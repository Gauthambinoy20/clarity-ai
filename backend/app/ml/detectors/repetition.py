"""
Detector 13 -- Repetition Analysis.

N-gram repetition rates (3,4,5-gram), sentence opener diversity,
over-variation detection, POS-pattern structure diversity.
"""

from __future__ import annotations

import re
import logging
from collections import Counter
from typing import List

import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class RepetitionDetector(BaseDetector):

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"[a-zA-Z']+", text)]

    @staticmethod
    def _ngram_repetition_rate(tokens: List[str], n: int) -> float:
        if len(tokens) < n:
            return 0.0
        ngrams = [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
        freq = Counter(ngrams)
        repeated = sum(c for c in freq.values() if c > 1)
        return repeated / max(len(ngrams), 1)

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 3]

    @staticmethod
    def _sentence_opener_diversity(sentences: List[str]) -> float:
        if not sentences:
            return 0.0
        openers = []
        for s in sentences:
            words = s.split()
            if words:
                openers.append(words[0].lower())
        unique = len(set(openers))
        return unique / max(len(openers), 1)

    @staticmethod
    def _over_variation_score(sentences: List[str]) -> float:
        """Detect if sentence lengths are *too* evenly distributed (AI pattern)."""
        if len(sentences) < 3:
            return 0.0
        lengths = [len(s.split()) for s in sentences]
        cv = float(np.std(lengths) / (np.mean(lengths) + 1e-8))
        # Very low CV -> suspiciously uniform -> AI
        # Very high CV -> natural variation -> human
        if cv < 0.15:
            return 0.9
        elif cv < 0.3:
            return 0.5
        else:
            return 0.1

    async def _pos_structure_diversity(self, sentences: List[str]) -> float:
        """Diversity of POS-tag patterns across sentences."""
        if not sentences:
            return 0.0
        nlp = await ModelRegistry.get_model("spacy")
        patterns = []
        for s in sentences:
            doc = nlp(s)
            pattern = tuple(t.pos_ for t in doc if t.pos_ != "SPACE")
            patterns.append(pattern)
        unique = len(set(patterns))
        return unique / max(len(patterns), 1)

    async def analyze(self, text: str) -> dict:
        signal = "repetition"
        tokens = self._tokenize(text)
        sentences = self._sentence_split(text)
        if len(tokens) < 20:
            return self._empty_result(signal, "text too short (< 20 words)")

        rep3 = self._ngram_repetition_rate(tokens, 3)
        rep4 = self._ngram_repetition_rate(tokens, 4)
        rep5 = self._ngram_repetition_rate(tokens, 5)

        opener_div = self._sentence_opener_diversity(sentences)
        over_var = self._over_variation_score(sentences)
        pos_div = await self._pos_structure_diversity(sentences)

        # AI text: low n-gram repetition, high opener diversity, low over-variation CV
        rep_avg = (rep3 + rep4 + rep5) / 3
        rep_score = self._sigmoid(-(rep_avg - 0.05) / 0.02)
        opener_score = self._sigmoid((opener_div - 0.7) / 0.1)
        var_score = over_var
        pos_score = self._sigmoid((pos_div - 0.8) / 0.1)

        ai_prob = self._clamp(
            0.25 * rep_score + 0.25 * opener_score + 0.25 * var_score + 0.25 * pos_score
        )
        confidence = self._compute_confidence([rep_score, opener_score, var_score, pos_score])

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "trigram_repetition_rate": round(rep3, 4),
                "fourgram_repetition_rate": round(rep4, 4),
                "fivegram_repetition_rate": round(rep5, 4),
                "sentence_opener_diversity": round(opener_div, 4),
                "over_variation_score": round(over_var, 4),
                "pos_structure_diversity": round(pos_div, 4),
                "num_sentences": len(sentences),
                "num_tokens": len(tokens),
            },
            "sub_scores": {
                "repetition_score": round(rep_score, 4),
                "opener_score": round(opener_score, 4),
                "variation_score": round(var_score, 4),
                "pos_score": round(pos_score, 4),
            },
        }
