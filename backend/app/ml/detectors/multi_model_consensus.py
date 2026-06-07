"""
Multi-Model Consensus Detector for ClarityAI.

Runs all available zero-shot text-classification pipelines simultaneously,
computes agreement scores, applies weighted voting based on per-model
reliability, and provides disagreement analysis.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configuration: registry key -> (display name, reliability weight)
# Weights reflect empirical reliability; higher = more trusted.
# ---------------------------------------------------------------------------
_MODEL_CONFIGS: List[Tuple[str, str, float]] = [
    ("roberta-detector-1", "Hello-SimpleAI/chatgpt-detector-roberta", 0.35),
    ("roberta-detector-2", "openai-community/roberta-large-openai-detector", 0.40),
    ("ai-detector-3", "PirateXX/AI-Content-Detector", 0.25),
]

# Label normalisation sets
_AI_LABELS = {"fake", "ai", "ai-generated", "machine", "chatgpt", "generated", "LABEL_0"}
_HUMAN_LABELS = {"real", "human", "human-written", "LABEL_1"}

# Agreement threshold: two scores are "in agreement" if within this delta
_AGREEMENT_DELTA = 0.20

# Classification threshold
_AI_THRESHOLD = 0.55
_HUMAN_THRESHOLD = 0.45


class MultiModelConsensusDetector(BaseDetector):
    """
    Runs all available zero-shot classifiers, computes weighted consensus,
    and reports agreement / disagreement analysis.
    """

    @staticmethod
    def _normalise_score(result: Dict) -> float:
        """Normalise pipeline output to 0-1 where 1 = AI."""
        label = result.get("label", "").lower().strip()
        score = float(result.get("score", 0.5))

        if label in _AI_LABELS:
            return score
        if label in _HUMAN_LABELS:
            return 1.0 - score
        if any(k in label for k in ("ai", "fake", "machine", "generated")):
            return score
        return 1.0 - score

    async def _run_single_model(self, key: str, display_name: str, text: str) -> Dict[str, Any]:
        """Run a single classification pipeline and return its result."""
        try:
            pipe = await ModelRegistry.get_model(key)
            result = pipe(text, truncation=True, max_length=512)
            if isinstance(result, list):
                result = result[0]
            ai_score = self._normalise_score(result)

            # Classify vote
            if ai_score >= _AI_THRESHOLD:
                vote = "ai"
            elif ai_score <= _HUMAN_THRESHOLD:
                vote = "human"
            else:
                vote = "uncertain"

            return {
                "model_key": key,
                "model_name": display_name,
                "raw_label": result.get("label", ""),
                "raw_score": round(float(result.get("score", 0.0)), 4),
                "ai_score": round(ai_score, 4),
                "vote": vote,
                "error": None,
            }
        except Exception as exc:
            logger.warning("Model %s failed: %s", key, exc)
            return {
                "model_key": key,
                "model_name": display_name,
                "raw_label": "",
                "raw_score": 0.0,
                "ai_score": 0.5,
                "vote": "uncertain",
                "error": str(exc),
            }

    def _compute_weighted_score(self, individual_results: List[Dict[str, Any]]) -> float:
        """Compute weighted average AI score based on reliability weights."""
        total_weight = 0.0
        weighted_sum = 0.0

        for result in individual_results:
            key = result["model_key"]
            # Find weight for this model
            weight = 1.0 / len(individual_results)  # default uniform
            for cfg_key, _, cfg_weight in _MODEL_CONFIGS:
                if cfg_key == key:
                    weight = cfg_weight
                    break

            # Reduce weight if the model errored
            if result["error"] is not None:
                weight *= 0.1

            weighted_sum += result["ai_score"] * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5
        return weighted_sum / total_weight

    @staticmethod
    def _compute_agreement(
        individual_results: List[Dict[str, Any]],
    ) -> Tuple[float, int, int]:
        """
        Compute agreement metrics.

        Returns: (agreement_ratio, agree_count, total_count)
        """
        valid_results = [r for r in individual_results if r["error"] is None]
        if len(valid_results) < 2:
            return 1.0, len(valid_results), len(valid_results)

        scores = [r["ai_score"] for r in valid_results]
        mean_score = sum(scores) / len(scores)

        agree_count = sum(1 for s in scores if abs(s - mean_score) < _AGREEMENT_DELTA)
        return (
            round(agree_count / len(valid_results), 4),
            agree_count,
            len(valid_results),
        )

    @staticmethod
    def _analyze_disagreements(
        individual_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify and explain model disagreements."""
        valid_results = [r for r in individual_results if r["error"] is None]
        if len(valid_results) < 2:
            return []

        scores = [r["ai_score"] for r in valid_results]
        mean_score = sum(scores) / len(scores)

        disagreements: List[Dict[str, Any]] = []

        # Find models that deviate from the consensus
        for result in valid_results:
            deviation = result["ai_score"] - mean_score
            if abs(deviation) >= _AGREEMENT_DELTA:
                direction = "more AI" if deviation > 0 else "more human"
                disagreements.append(
                    {
                        "model": result["model_name"],
                        "model_key": result["model_key"],
                        "ai_score": result["ai_score"],
                        "deviation_from_mean": round(deviation, 4),
                        "direction": direction,
                        "explanation": (
                            f"{result['model_name']} scored {result['ai_score']:.2f} "
                            f"({direction} than consensus {mean_score:.2f}). "
                            f"This model may weight different textual features."
                        ),
                    }
                )

        # Check for split votes (some say AI, some say human)
        votes = [r["vote"] for r in valid_results]
        ai_votes = votes.count("ai")
        human_votes = votes.count("human")
        if ai_votes > 0 and human_votes > 0:
            disagreements.append(
                {
                    "type": "split_vote",
                    "ai_vote_count": ai_votes,
                    "human_vote_count": human_votes,
                    "uncertain_vote_count": votes.count("uncertain"),
                    "explanation": (
                        f"Models are split: {ai_votes} vote AI, {human_votes} vote human, "
                        f"{votes.count('uncertain')} uncertain. "
                        "The text may contain mixed human/AI content."
                    ),
                }
            )

        return disagreements

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    async def analyze(self, text: str) -> dict:
        signal = "multi_model_consensus"

        if len(text.split()) < 10:
            return self._empty_result(signal, "text too short (< 10 words)")

        # Run all models concurrently
        tasks = [self._run_single_model(key, name, text) for key, name, _ in _MODEL_CONFIGS]
        individual_results = await asyncio.gather(*tasks)

        # Weighted consensus score
        consensus_score = self._compute_weighted_score(individual_results)

        # Agreement analysis
        agreement_ratio, agree_count, total_models = self._compute_agreement(individual_results)

        # Disagreement analysis
        disagreement_details = self._analyze_disagreements(individual_results)

        # Final AI probability (clamped)
        ai_probability = self._clamp(consensus_score)

        # Confidence based on agreement and score extremity
        score_extremity = abs(ai_probability - 0.5)
        if agreement_ratio >= 0.9 and score_extremity > 0.3:
            confidence = "high"
        elif agreement_ratio >= 0.6 and score_extremity > 0.15:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "signal": signal,
            "ai_probability": round(ai_probability, 4),
            "confidence": confidence,
            "consensus_score": round(consensus_score, 4),
            "agreement_ratio": agreement_ratio,
            "individual_votes": individual_results,
            "disagreement_details": disagreement_details,
            "details": {
                "num_models": total_models,
                "models_agreeing": agree_count,
                "weighted_score": round(consensus_score, 4),
                "unweighted_score": (
                    round(
                        sum(r["ai_score"] for r in individual_results) / len(individual_results), 4
                    )
                    if individual_results
                    else 0.5
                ),
            },
        }
