"""
Detector 3 -- Binoculars.

Cross-perplexity ratio between an *observer* model (distilgpt2) and a
*performer* model (gpt2).

    score = observer_cross_entropy / performer_cross_entropy

Thresholds:  < 0.85 -> AI,  > 1.05 -> human.
"""

from __future__ import annotations

import logging

import torch

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

MAX_LENGTH = 512
THRESHOLD_AI = 0.85
THRESHOLD_HUMAN = 1.05


class BinocularsDetector(BaseDetector):

    @staticmethod
    @torch.no_grad()
    def _cross_entropy(text: str, model, tokenizer) -> float:
        device = next(model.parameters()).device
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"]
        if input_ids.size(1) < 2:
            return 0.0
        outputs = model(**enc, labels=input_ids)
        return outputs.loss.item()

    async def analyze(self, text: str) -> dict:
        signal = "binoculars"
        if len(text.split()) < 10:
            return self._empty_result(signal, "text too short (< 10 words)")

        obs_tok, obs_model = await ModelRegistry.get_model("distilgpt2")
        perf_tok, perf_model = await ModelRegistry.get_model("gpt2")

        observer_ce = self._cross_entropy(text, obs_model, obs_tok)
        performer_ce = self._cross_entropy(text, perf_model, perf_tok)

        ratio = observer_ce / performer_ce if performer_ce > 1e-8 else 1.0

        if ratio <= THRESHOLD_AI:
            ai_prob = self._clamp(0.7 + 0.3 * (THRESHOLD_AI - ratio) / THRESHOLD_AI)
        elif ratio >= THRESHOLD_HUMAN:
            ai_prob = self._clamp(0.3 - 0.3 * (ratio - THRESHOLD_HUMAN) / THRESHOLD_HUMAN)
        else:
            ai_prob = self._clamp(
                0.7 - 0.4 * (ratio - THRESHOLD_AI) / (THRESHOLD_HUMAN - THRESHOLD_AI)
            )

        dist = abs(ratio - 0.95)
        confidence = "high" if dist > 0.2 else "medium" if dist > 0.1 else "low"

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "observer_cross_entropy": round(observer_ce, 4),
                "performer_cross_entropy": round(performer_ce, 4),
                "binoculars_ratio": round(ratio, 4),
                "threshold_ai": THRESHOLD_AI,
                "threshold_human": THRESHOLD_HUMAN,
            },
        }
