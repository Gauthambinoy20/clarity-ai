"""
Detector 5 -- KGW Watermark Detection.

Green-list z-test with gamma=0.25.
z > 4.0  ->  watermark detected (override flag set).
"""

from __future__ import annotations

import hashlib
import logging

import torch
import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

GAMMA = 0.25
Z_THRESHOLD = 4.0
MAX_LENGTH = 512


class WatermarkDetector(BaseDetector):

    @staticmethod
    def _green_list_for_token(prev_token_id: int, vocab_size: int) -> set:
        seed = hashlib.sha256(str(prev_token_id).encode()).digest()
        rng = np.random.RandomState(int.from_bytes(seed[:4], byteorder="big"))
        green_size = int(GAMMA * vocab_size)
        return set(rng.choice(vocab_size, size=green_size, replace=False).tolist())

    @staticmethod
    @torch.no_grad()
    def _compute_z_score(text: str, model, tokenizer) -> dict:
        device = next(model.parameters()).device
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"][0]
        seq_len = len(input_ids)
        vocab_size = model.config.vocab_size

        if seq_len < 3:
            return {"z_score": 0.0, "green_fraction": 0.0, "num_tokens": 0}

        green_count = 0
        total = seq_len - 1
        for i in range(1, seq_len):
            prev_id = input_ids[i - 1].item()
            cur_id = input_ids[i].item()
            green_set = WatermarkDetector._green_list_for_token(prev_id, vocab_size)
            if cur_id in green_set:
                green_count += 1

        green_frac = green_count / total
        std = (GAMMA * (1 - GAMMA) / total) ** 0.5 if total > 0 else 1.0
        z = (green_frac - GAMMA) / std if std > 0 else 0.0

        return {
            "z_score": float(z),
            "green_fraction": float(green_frac),
            "green_count": green_count,
            "num_tokens": total,
        }

    async def analyze(self, text: str) -> dict:
        signal = "watermark"
        if len(text.split()) < 10:
            return self._empty_result(signal, "text too short (< 10 words)")

        tokenizer, model = await ModelRegistry.get_model("gpt2")
        result = self._compute_z_score(text, model, tokenizer)
        z = result["z_score"]

        watermark_detected = z > Z_THRESHOLD
        possible_watermark = z > 2.0

        if watermark_detected:
            ai_prob = self._clamp(0.85 + 0.15 * self._sigmoid((z - Z_THRESHOLD) * 2))
        elif possible_watermark:
            ai_prob = self._clamp(0.5 + 0.35 * (z - 2.0) / (Z_THRESHOLD - 2.0))
        else:
            ai_prob = self._clamp(0.3 * self._sigmoid(z))

        confidence = "high" if watermark_detected else "medium" if possible_watermark else "low"

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "watermark_detected": watermark_detected,
            "override": watermark_detected,
            "details": {
                "z_score": round(z, 4),
                "z_threshold": Z_THRESHOLD,
                "green_fraction": round(result["green_fraction"], 4),
                "expected_green_fraction": GAMMA,
                "num_tokens_analyzed": result["num_tokens"],
            },
        }
