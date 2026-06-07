"""
Detector 9 -- Zero-Shot Ensemble.

Runs three HuggingFace text-classification pipelines, averages their
scores, and reports consensus.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# Registry keys that map to text-classification pipelines
_PIPELINE_KEYS = (
    "roberta-detector-1",  # Hello-SimpleAI/chatgpt-detector-roberta
    "roberta-detector-2",  # openai-community/roberta-large-openai-detector
    "ai-detector-3",  # PirateXX/AI-Content-Detector
)

# Label normalisation:  every pipeline may use different label strings
_AI_LABELS = {"fake", "ai", "ai-generated", "machine", "chatgpt", "generated", "LABEL_0"}
_HUMAN_LABELS = {"real", "human", "human-written", "LABEL_1"}


class ZeroShotEnsembleDetector(BaseDetector):

    @staticmethod
    def _normalise_score(result: Dict) -> float:
        """Return a 0-1 score where 1 = AI."""
        label = result.get("label", "").lower().strip()
        score = float(result.get("score", 0.5))

        if label in _AI_LABELS:
            return score
        if label in _HUMAN_LABELS:
            return 1.0 - score

        # Fallback heuristic: if the label contains "ai" or "fake"
        if any(k in label for k in ("ai", "fake", "machine", "generated")):
            return score
        # Otherwise assume the top label is human
        return 1.0 - score

    async def analyze(self, text: str) -> dict:
        signal = "zero_shot_ensemble"
        if len(text.split()) < 10:
            return self._empty_result(signal, "text too short (< 10 words)")

        individual: List[Dict] = []
        scores: List[float] = []

        for key in _PIPELINE_KEYS:
            try:
                pipe = await ModelRegistry.get_model(key)
                # pipeline returns a list of dicts; take top result
                result = pipe(text, truncation=True, max_length=512)
                if isinstance(result, list):
                    result = result[0]
                ai_score = self._normalise_score(result)
                scores.append(ai_score)
                individual.append(
                    {
                        "model": key,
                        "raw_label": result.get("label", ""),
                        "raw_score": round(float(result.get("score", 0.0)), 4),
                        "ai_score": round(ai_score, 4),
                    }
                )
            except Exception as exc:
                logger.warning("Pipeline %s failed: %s", key, exc)
                individual.append(
                    {
                        "model": key,
                        "error": str(exc),
                        "ai_score": 0.5,
                    }
                )
                scores.append(0.5)

        avg_score = float(sum(scores) / len(scores)) if scores else 0.5

        # Consensus: all agree within 0.2 of the average
        agree_count = sum(1 for s in scores if abs(s - avg_score) < 0.2)
        consensus = agree_count == len(scores) and len(scores) > 0

        ai_prob = self._clamp(avg_score)
        confidence = (
            "high"
            if consensus and abs(ai_prob - 0.5) > 0.3
            else "medium" if abs(ai_prob - 0.5) > 0.15 else "low"
        )

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "individual_results": individual,
                "average_score": round(avg_score, 4),
                "consensus": consensus,
                "num_models": len(scores),
            },
        }
