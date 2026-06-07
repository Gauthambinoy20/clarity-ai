"""
Ensemble meta-learner that combines all 14 detection signals into a single
AI-probability score with classification and interpretability metadata.
"""

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default per-signal weights used by the fallback weighted-average estimator.
# Weights were hand-tuned against a held-out dev set; they intentionally
# over-weight the more discriminative signals.
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: Dict[str, float] = {
    "perplexity": 0.10,
    "burstiness": 0.08,
    "entropy": 0.07,
    "stylometric": 0.09,
    "pos_pattern": 0.05,
    "vocabulary_richness": 0.05,
    "repetition": 0.05,
    "coherence": 0.06,
    "detectgpt": 0.10,
    "binoculars": 0.10,
    "roberta_chatgpt": 0.08,
    "roberta_openai": 0.08,
    "ai_content_detector": 0.06,
    "watermark": 0.03,
}

SIGNAL_NAMES: List[str] = list(DEFAULT_WEIGHTS.keys())

# Interaction feature definitions: (signal_a, signal_b)
INTERACTION_PAIRS: List[Tuple[str, str]] = [
    ("detectgpt", "binoculars"),
    ("stylometric", "entropy"),
    ("perplexity", "burstiness"),
]


def _extract_feature_vector(signal_results: Dict[str, Dict[str, Any]]) -> np.ndarray:
    """
    Build a numeric feature vector from signal results.

    Returns a 1-D array of length len(SIGNAL_NAMES) + len(INTERACTION_PAIRS).
    Missing signals default to 0.5 (maximally uncertain).
    """
    base_features: List[float] = []
    for name in SIGNAL_NAMES:
        result = signal_results.get(name, {})
        prob = result.get("ai_probability", 0.5)
        prob = max(0.0, min(1.0, float(prob)))
        base_features.append(prob)

    # Interaction terms (product of the two base probabilities)
    interactions: List[float] = []
    for sig_a, sig_b in INTERACTION_PAIRS:
        idx_a = SIGNAL_NAMES.index(sig_a)
        idx_b = SIGNAL_NAMES.index(sig_b)
        interactions.append(base_features[idx_a] * base_features[idx_b])

    return np.array(base_features + interactions, dtype=np.float64)


class EnsembleMetaLearner:
    """
    Combines predictions from all 14 detection signals via either a trained
    logistic-regression meta-model or a hand-tuned weighted average fallback.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self._model = None
        self._model_path = model_path

        if model_path is None:
            candidate = (
                Path(__file__).resolve().parent.parent.parent.parent / "models" / "meta_learner.pkl"
            )
            if candidate.exists():
                self._model_path = str(candidate)

        if self._model_path and Path(self._model_path).exists():
            try:
                with open(self._model_path, "rb") as fh:
                    self._model = pickle.load(fh)
                logger.info("Meta-learner model loaded from %s", self._model_path)
            except Exception as exc:
                logger.warning("Failed to load meta-learner model: %s", exc)
                self._model = None

    # ------------------------------------------------------------------
    # Training helper (offline usage)
    # ------------------------------------------------------------------
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        save_path: Optional[str] = None,
    ) -> None:
        """
        Train the meta-learner on stacked signal features.

        Parameters
        ----------
        X : array of shape (n_samples, n_features)
            Each row is the output of ``_extract_feature_vector``.
        y : array of shape (n_samples,)
            Binary labels: 1 = AI, 0 = human.
        save_path : optional filesystem path to persist the model.
        """
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.linear_model import LogisticRegression

        base_lr = LogisticRegression(
            C=1.0,
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
        )
        calibrated = CalibratedClassifierCV(base_lr, cv=5, method="isotonic")
        calibrated.fit(X, y)
        self._model = calibrated
        logger.info("Meta-learner trained on %d samples.", len(y))

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as fh:
                pickle.dump(self._model, fh)
            logger.info("Meta-learner saved to %s", save_path)

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def predict(self, signal_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Produce the final ensemble prediction.

        Parameters
        ----------
        signal_results : dict
            Maps signal name -> detector result dict (must contain
            ``ai_probability`` at minimum).

        Returns
        -------
        dict with keys:
            overall_score, classification, confidence, signal_agreement,
            top_contributing_signals, interpretation
        """
        # ----- watermark override -----------------------------------
        watermark_result = signal_results.get("watermark", {})
        watermark_detected = watermark_result.get("watermark_detected", False)

        features = _extract_feature_vector(signal_results)
        base_probs = features[: len(SIGNAL_NAMES)]

        if self._model is not None:
            try:
                overall_score = float(self._model.predict_proba(features.reshape(1, -1))[0, 1])
            except Exception as exc:
                logger.warning("Model prediction failed, falling back to weighted avg: %s", exc)
                overall_score = self._weighted_average(base_probs)
        else:
            overall_score = self._weighted_average(base_probs)

        # Apply watermark override
        if watermark_detected:
            overall_score = 0.95

        overall_score = max(0.0, min(1.0, overall_score))

        # ----- classification ----------------------------------------
        classification = self._classify(overall_score)

        # ----- confidence --------------------------------------------
        confidence = self._compute_confidence(base_probs)

        # ----- signal agreement --------------------------------------
        signal_agreement = self._signal_agreement(base_probs)

        # ----- top contributing signals ------------------------------
        top_signals = self._top_contributing_signals(signal_results, top_n=5)

        # ----- human-readable interpretation -------------------------
        interpretation = self._build_interpretation(
            overall_score,
            classification,
            confidence,
            signal_agreement,
            top_signals,
            watermark_detected,
        )

        return {
            "overall_score": round(overall_score, 4),
            "classification": classification,
            "confidence": confidence,
            "signal_agreement": round(signal_agreement, 4),
            "top_contributing_signals": top_signals,
            "interpretation": interpretation,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _weighted_average(base_probs: np.ndarray) -> float:
        weights = np.array([DEFAULT_WEIGHTS[s] for s in SIGNAL_NAMES], dtype=np.float64)
        total_weight = weights.sum()
        if total_weight == 0:
            return 0.5
        return float(np.dot(weights, base_probs) / total_weight)

    @staticmethod
    def _classify(score: float) -> str:
        if score >= 0.75:
            return "ai"
        elif score <= 0.30:
            return "human"
        else:
            return "mixed_or_uncertain"

    @staticmethod
    def _compute_confidence(probs: np.ndarray) -> str:
        std = float(np.std(probs))
        mean = float(np.mean(probs))
        # High confidence when signals agree strongly
        if std < 0.12 and (mean > 0.80 or mean < 0.20):
            return "high"
        elif std < 0.20 and (mean > 0.65 or mean < 0.35):
            return "medium"
        else:
            return "low"

    @staticmethod
    def _signal_agreement(probs: np.ndarray) -> float:
        """Return 0-1 measure of how much the signals agree (1 = perfect)."""
        if len(probs) == 0:
            return 0.0
        std = float(np.std(probs))
        # Map std=0 -> agreement=1, std=0.5 -> agreement=0
        return max(0.0, 1.0 - 2.0 * std)

    @staticmethod
    def _top_contributing_signals(
        signal_results: Dict[str, Dict[str, Any]], top_n: int = 5
    ) -> List[Dict[str, Any]]:
        scored: List[Tuple[str, float, str]] = []
        for name in SIGNAL_NAMES:
            result = signal_results.get(name, {})
            prob = float(result.get("ai_probability", 0.5))
            conf = result.get("confidence", "low")
            # Contribution = distance from 0.5 (undecided) weighted by signal weight
            weight = DEFAULT_WEIGHTS.get(name, 0.05)
            contribution = abs(prob - 0.5) * weight
            scored.append((name, prob, conf, contribution))

        scored.sort(key=lambda t: t[3], reverse=True)

        return [
            {
                "signal": name,
                "ai_probability": round(prob, 4),
                "confidence": conf,
                "contribution": round(contribution, 4),
            }
            for name, prob, conf, contribution in scored[:top_n]
        ]

    @staticmethod
    def _build_interpretation(
        score: float,
        classification: str,
        confidence: str,
        agreement: float,
        top_signals: List[Dict[str, Any]],
        watermark_detected: bool,
    ) -> str:
        parts: List[str] = []

        # Lead sentence
        pct = int(round(score * 100))
        if classification == "ai":
            parts.append(f"This text is very likely AI-generated (score: {pct}%).")
        elif classification == "human":
            parts.append(f"This text appears to be human-written (score: {pct}%).")
        else:
            parts.append(
                f"The origin of this text is uncertain (score: {pct}%). "
                "It may contain a mix of AI-generated and human-written content."
            )

        # Confidence / agreement
        if confidence == "high" and agreement > 0.75:
            parts.append(
                "Multiple independent detection signals strongly agree on this assessment."
            )
        elif confidence == "low" or agreement < 0.40:
            parts.append(
                "Detection signals show significant disagreement; treat this result with caution."
            )

        # Top signals
        if top_signals:
            names = ", ".join(s["signal"] for s in top_signals[:3])
            parts.append(f"The most influential signals were: {names}.")

        # Watermark
        if watermark_detected:
            parts.append(
                "An AI watermark was detected in this text, which is a strong indicator of AI generation."
            )

        return " ".join(parts)
