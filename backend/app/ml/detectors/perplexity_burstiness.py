"""
Detector 1 -- Perplexity & Burstiness Analysis.

Computes per-sentence perplexity via GPT-2 and burstiness metrics
(coefficient of variation, Goh-Barabasi index, sequential memory,
bimodality coefficient).
"""

from __future__ import annotations

import math
import re
import logging
from typing import List

import torch
import numpy as np
from scipy import stats as sp_stats

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class PerplexityBurstinessDetector(BaseDetector):

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    @staticmethod
    @torch.no_grad()
    def _sentence_perplexity(sentence: str, model, tokenizer) -> float:
        device = next(model.parameters()).device
        enc = tokenizer(
            sentence,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(device)
        input_ids = enc["input_ids"]
        if input_ids.size(1) < 2:
            return 0.0
        outputs = model(**enc, labels=input_ids)
        return math.exp(outputs.loss.item())

    @staticmethod
    def _coefficient_of_variation(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mu = float(np.mean(values))
        if mu == 0:
            return 0.0
        return float(np.std(values, ddof=1) / mu)

    @staticmethod
    def _goh_barabasi_index(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mu = float(np.mean(values))
        sigma = float(np.std(values, ddof=1))
        denom = sigma + mu
        return float((sigma - mu) / denom) if denom != 0 else 0.0

    @staticmethod
    def _sequential_memory(values: List[float]) -> float:
        if len(values) < 3:
            return 0.0
        arr = np.array(values)
        mean = arr.mean()
        var = float(np.var(arr))
        if var == 0:
            return 0.0
        return float(np.mean((arr[:-1] - mean) * (arr[1:] - mean)) / var)

    @staticmethod
    def _bimodality_coefficient(values: List[float]) -> float:
        if len(values) < 4:
            return 0.0
        skew = float(sp_stats.skew(values))
        kurt = float(sp_stats.kurtosis(values, fisher=False))
        if kurt == 0:
            return 0.0
        return (skew**2 + 1) / kurt

    # ── main ─────────────────────────────────────────────────────────────

    async def analyze(self, text: str) -> dict:
        signal = "perplexity_burstiness"
        sentences = self._sentence_split(text)
        if len(sentences) < 3:
            return self._empty_result(signal, "need >= 3 sentences")

        tokenizer, model = await ModelRegistry.get_model("gpt2")

        perplexities: List[float] = [
            self._sentence_perplexity(s, model, tokenizer) for s in sentences
        ]

        mean_ppl = float(np.mean(perplexities))
        cv = self._coefficient_of_variation(perplexities)
        goh = self._goh_barabasi_index(perplexities)
        mem = self._sequential_memory(perplexities)
        bimod = self._bimodality_coefficient(perplexities)

        ppl_score = self._sigmoid(-(mean_ppl - 60) / 30)
        cv_score = self._sigmoid(-(cv - 0.8) / 0.3)
        goh_score = self._sigmoid(-(goh - 0.0) / 0.3)
        mem_score = self._sigmoid((mem - 0.2) / 0.3)
        bimod_score = self._sigmoid(-(bimod - 0.555) / 0.2)

        ai_prob = self._clamp(
            0.30 * ppl_score
            + 0.25 * cv_score
            + 0.15 * goh_score
            + 0.15 * mem_score
            + 0.15 * bimod_score
        )
        confidence = self._compute_confidence(
            [ppl_score, cv_score, goh_score, mem_score, bimod_score]
        )

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "mean_perplexity": round(mean_ppl, 2),
                "coefficient_of_variation": round(cv, 4),
                "goh_barabasi_index": round(goh, 4),
                "sequential_memory": round(mem, 4),
                "bimodality_coefficient": round(bimod, 4),
                "num_sentences": len(sentences),
                "per_sentence_perplexity": [round(p, 2) for p in perplexities],
            },
            "sub_scores": {
                "ppl_score": round(ppl_score, 4),
                "cv_score": round(cv_score, 4),
                "goh_score": round(goh_score, 4),
                "mem_score": round(mem_score, 4),
                "bimod_score": round(bimod_score, 4),
            },
        }
