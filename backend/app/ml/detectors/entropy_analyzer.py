"""
Detector 8 -- Entropy Analyzer.

Multi-level Shannon entropy (character, word, bigram) plus AI buzzword
and AI phrase-pattern detection.
"""

from __future__ import annotations

import math
import re
import logging
from collections import Counter
from typing import List, Tuple

from app.ml.detectors.base import BaseDetector

logger = logging.getLogger(__name__)

AI_BUZZWORDS: List[str] = [
    "delve",
    "tapestry",
    "holistic",
    "synergy",
    "leverage",
    "paradigm",
    "nuanced",
    "multifaceted",
    "comprehensive",
    "robust",
    "innovative",
    "cutting-edge",
    "groundbreaking",
    "transformative",
    "pivotal",
    "crucial",
    "paramount",
    "fundamental",
    "intricate",
    "seamless",
    "streamline",
    "optimize",
    "utilize",
    "facilitate",
    "implement",
    "navigate",
    "landscape",
    "ecosystem",
    "framework",
    "methodology",
    "trajectory",
    "juxtaposition",
    "dichotomy",
    "underscore",
    "underpin",
    "elucidate",
    "articulate",
    "enumerate",
    "delineate",
    "synthesize",
    "extrapolate",
    "interpolate",
    "contextualize",
    "conceptualize",
    "operationalize",
    "spearhead",
    "bolster",
    "augment",
    "mitigate",
    "alleviate",
    "exacerbate",
    "culminate",
    "epitomize",
    "exemplify",
]

AI_PHRASE_PATTERNS: List[str] = [
    r"it\s+is\s+(important|worth|crucial|essential)\s+to\s+note",
    r"in\s+(today's|the\s+modern)\s+(world|age|era|landscape)",
    r"plays\s+a\s+(crucial|vital|pivotal|key|important)\s+role",
    r"(one|it)\s+cannot\s+(be\s+)?overstat(ed|e)",
    r"the\s+importance\s+of\s+\w+\s+cannot",
    r"in\s+conclusion",
    r"to\s+sum(marize|\s+up)",
    r"it\s+is\s+evident\s+that",
    r"this\s+essay\s+(will\s+)?(explore|examine|discuss|delve)",
    r"there\s+are\s+(several|many|numerous|various)\s+(key\s+)?(factors|reasons|aspects)",
    r"(first|second|third)(ly)?,?\s",
    r"on\s+the\s+other\s+hand",
    r"in\s+light\s+of",
    r"it\s+goes\s+without\s+saying",
    r"at\s+the\s+end\s+of\s+the\s+day",
    r"when\s+it\s+comes\s+to",
]


class EntropyAnalyzerDetector(BaseDetector):

    @staticmethod
    def _char_entropy(text: str) -> float:
        if not text:
            return 0.0
        freq = Counter(text)
        n = len(text)
        return -sum((c / n) * math.log2(c / n) for c in freq.values() if c > 0)

    @staticmethod
    def _word_entropy(words: List[str]) -> float:
        if not words:
            return 0.0
        freq = Counter(words)
        n = len(words)
        return -sum((c / n) * math.log2(c / n) for c in freq.values() if c > 0)

    @staticmethod
    def _bigram_entropy(words: List[str]) -> float:
        if len(words) < 2:
            return 0.0
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        freq = Counter(bigrams)
        n = len(bigrams)
        return -sum((c / n) * math.log2(c / n) for c in freq.values() if c > 0)

    @staticmethod
    def _buzzword_analysis(text: str) -> Tuple[float, List[str]]:
        lower = text.lower()
        words = lower.split()
        total = max(len(words), 1)
        hits: List[str] = []
        for bw in AI_BUZZWORDS:
            count = lower.count(bw)
            if count > 0:
                hits.extend([bw] * count)
        density = len(hits) / total
        return density, hits

    @staticmethod
    def _phrase_pattern_analysis(text: str) -> Tuple[float, List[str]]:
        lower = text.lower()
        words = lower.split()
        total = max(len(words), 1)
        hits: List[str] = []
        for pat in AI_PHRASE_PATTERNS:
            matches = re.findall(pat, lower)
            if matches:
                hits.extend([pat] * len(matches))
        density = len(hits) / total
        return density, hits

    async def analyze(self, text: str) -> dict:
        signal = "entropy_analyzer"
        words = text.lower().split()
        if len(words) < 10:
            return self._empty_result(signal, "text too short (< 10 words)")

        char_ent = self._char_entropy(text)
        word_ent = self._word_entropy(words)
        bigram_ent = self._bigram_entropy(words)

        bw_density, bw_hits = self._buzzword_analysis(text)
        ph_density, ph_hits = self._phrase_pattern_analysis(text)

        # Scoring:  lower entropy + more buzzwords/patterns -> more AI
        ent_score = self._sigmoid(-(word_ent - 8.0) / 2.0)
        bw_score = self._sigmoid((bw_density - 0.02) / 0.01)
        ph_score = self._sigmoid((ph_density - 0.005) / 0.003)

        ai_prob = self._clamp(0.35 * ent_score + 0.35 * bw_score + 0.30 * ph_score)
        confidence = self._compute_confidence([ent_score, bw_score, ph_score])

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "char_entropy": round(char_ent, 4),
                "word_entropy": round(word_ent, 4),
                "bigram_entropy": round(bigram_ent, 4),
                "buzzword_density": round(bw_density, 4),
                "phrase_density": round(ph_density, 4),
                "buzzword_hits": list(set(bw_hits)),
                "phrase_hits": list(set(ph_hits)),
                "num_buzzwords_found": len(bw_hits),
                "num_phrases_found": len(ph_hits),
            },
            "sub_scores": {
                "entropy_score": round(ent_score, 4),
                "buzzword_score": round(bw_score, 4),
                "phrase_score": round(ph_score, 4),
            },
        }
