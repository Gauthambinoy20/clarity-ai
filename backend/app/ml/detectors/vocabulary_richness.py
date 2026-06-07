"""
Detector 11 -- Vocabulary Richness.

Computes Yule's K, Hapax ratio, Brunet's W, Honore's H, Sichel's S,
and frequency-distribution entropy.
"""

from __future__ import annotations

import math
import logging
from collections import Counter
from typing import List

from app.ml.detectors.base import BaseDetector

logger = logging.getLogger(__name__)


class VocabularyRichnessDetector(BaseDetector):

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        import re

        return [w.lower() for w in re.findall(r"[a-zA-Z']+", text)]

    @staticmethod
    def _yules_k(tokens: List[str]) -> float:
        n = len(tokens)
        if n == 0:
            return 0.0
        freq = Counter(tokens)
        fof = Counter(freq.values())
        m2 = sum(i * i * v for i, v in fof.items())
        return 10000.0 * (m2 - n) / (n * n) if n > 1 else 0.0

    @staticmethod
    def _hapax_ratio(tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        freq = Counter(tokens)
        return sum(1 for v in freq.values() if v == 1) / len(tokens)

    @staticmethod
    def _brunets_w(tokens: List[str]) -> float:
        """W = N^(V^-0.172).  Lower W -> richer vocabulary."""
        n = len(tokens)
        v = len(set(tokens))
        if n == 0 or v == 0:
            return 0.0
        return n ** (v**-0.172)

    @staticmethod
    def _honores_h(tokens: List[str]) -> float:
        """H = 100 * log(N) / (1 - hapax_count / V)."""
        n = len(tokens)
        freq = Counter(tokens)
        v = len(freq)
        hapax = sum(1 for c in freq.values() if c == 1)
        if v == 0 or v == hapax:
            return 0.0
        return 100.0 * math.log(n) / (1.0 - hapax / v)

    @staticmethod
    def _sichels_s(tokens: List[str]) -> float:
        """S = dis / V (proportion of words appearing exactly twice)."""
        freq = Counter(tokens)
        v = len(freq)
        if v == 0:
            return 0.0
        dis = sum(1 for c in freq.values() if c == 2)
        return dis / v

    @staticmethod
    def _freq_dist_entropy(tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        freq = Counter(tokens)
        n = len(tokens)
        return -sum((c / n) * math.log2(c / n) for c in freq.values() if c > 0)

    async def analyze(self, text: str) -> dict:
        signal = "vocabulary_richness"
        tokens = self._tokenize(text)
        if len(tokens) < 20:
            return self._empty_result(signal, "text too short (< 20 words)")

        yk = self._yules_k(tokens)
        hapax = self._hapax_ratio(tokens)
        bw = self._brunets_w(tokens)
        hh = self._honores_h(tokens)
        ss = self._sichels_s(tokens)
        fde = self._freq_dist_entropy(tokens)

        # AI text tends to have lower Yule's K (less repetition), lower hapax
        # ratio (fewer rare words), and moderate entropy
        yk_score = self._sigmoid(-(yk - 100) / 40)
        hapax_score = self._sigmoid(-(hapax - 0.5) / 0.15)
        ent_score = self._sigmoid(-(fde - 9.0) / 1.5)

        ai_prob = self._clamp(0.35 * yk_score + 0.30 * hapax_score + 0.35 * ent_score)
        confidence = self._compute_confidence([yk_score, hapax_score, ent_score])

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "yules_k": round(yk, 4),
                "hapax_ratio": round(hapax, 4),
                "brunets_w": round(bw, 4),
                "honores_h": round(hh, 4),
                "sichels_s": round(ss, 4),
                "freq_dist_entropy": round(fde, 4),
                "unique_words": len(set(tokens)),
                "total_words": len(tokens),
            },
            "sub_scores": {
                "yules_k_score": round(yk_score, 4),
                "hapax_score": round(hapax_score, 4),
                "entropy_score": round(ent_score, 4),
            },
        }
