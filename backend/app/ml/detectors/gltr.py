"""
Detector 6 -- GLTR (Giant Language model Test Room).

Per-token rank, probability, entropy, bucket/color for visualization.
Aggregate top-10 ratio drives the AI probability score.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import torch
import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

MAX_LENGTH = 512


class GLTRDetector(BaseDetector):

    @staticmethod
    @torch.no_grad()
    def _analyze_tokens(text: str, model, tokenizer) -> List[Dict]:
        device = next(model.parameters()).device
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"]
        seq_len = input_ids.size(1)
        if seq_len < 2:
            return []

        logits = model(**enc).logits
        probs = torch.softmax(logits[0, :-1], dim=-1)
        target_ids = input_ids[0, 1:]

        sorted_indices = probs.argsort(dim=-1, descending=True)

        token_data: List[Dict] = []
        for i in range(len(target_ids)):
            tid = target_ids[i].item()
            token_str = tokenizer.decode([tid])
            token_prob = probs[i, tid].item()

            rank_t = (sorted_indices[i] == tid).nonzero(as_tuple=True)[0]
            rank = rank_t.item() if len(rank_t) > 0 else probs.size(-1)

            log_p = torch.log(probs[i] + 1e-10)
            entropy = -(probs[i] * log_p).sum().item()

            if rank < 10:
                bucket, color = "top10", "green"
            elif rank < 100:
                bucket, color = "top100", "yellow"
            elif rank < 1000:
                bucket, color = "top1000", "red"
            else:
                bucket, color = "rare", "purple"

            token_data.append(
                {
                    "token": token_str,
                    "token_id": tid,
                    "rank": rank,
                    "probability": round(token_prob, 6),
                    "entropy": round(entropy, 4),
                    "bucket": bucket,
                    "color": color,
                }
            )
        return token_data

    async def analyze(self, text: str) -> dict:
        signal = "gltr"
        if len(text.split()) < 5:
            return self._empty_result(signal, "text too short (< 5 words)")

        tokenizer, model = await ModelRegistry.get_model("gpt2")
        token_data = self._analyze_tokens(text, model, tokenizer)
        if not token_data:
            return self._empty_result(signal, "could not tokenize text")

        total = len(token_data)
        counts = {"top10": 0, "top100": 0, "top1000": 0, "rare": 0}
        for t in token_data:
            counts[t["bucket"]] += 1

        top10_ratio = counts["top10"] / total
        ai_prob = self._clamp(self._sigmoid((top10_ratio - 0.45) / 0.15))

        mean_rank = float(np.mean([t["rank"] for t in token_data]))
        mean_entropy = float(np.mean([t["entropy"] for t in token_data]))

        confidence = (
            "high" if abs(ai_prob - 0.5) > 0.3 else "medium" if abs(ai_prob - 0.5) > 0.15 else "low"
        )

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "token_data": token_data,
            "details": {
                "total_tokens": total,
                "top10_ratio": round(top10_ratio, 4),
                "top100_ratio": round(counts["top100"] / total, 4),
                "top1000_ratio": round(counts["top1000"] / total, 4),
                "rare_ratio": round(counts["rare"] / total, 4),
                "mean_rank": round(mean_rank, 2),
                "mean_entropy": round(mean_entropy, 4),
                "bucket_counts": counts,
            },
        }
