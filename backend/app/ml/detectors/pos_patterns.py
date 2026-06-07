"""
Detector 12 -- POS Pattern Analysis.

POS tag distribution via spaCy: noun/verb ratio, informality score,
POS entropy, unique POS bigrams.
"""

from __future__ import annotations

import math
import logging
from collections import Counter
from typing import List, Tuple

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class POSPatternsDetector(BaseDetector):

    async def analyze(self, text: str) -> dict:
        signal = "pos_patterns"
        if len(text.split()) < 15:
            return self._empty_result(signal, "text too short (< 15 words)")

        nlp = await ModelRegistry.get_model("spacy")
        doc = nlp(text)

        pos_tags: List[str] = [t.pos_ for t in doc if t.pos_ != "SPACE"]
        if not pos_tags:
            return self._empty_result(signal, "no POS tags extracted")

        pos_counts = Counter(pos_tags)
        total = len(pos_tags)

        # Noun / verb ratio
        nouns = pos_counts.get("NOUN", 0) + pos_counts.get("PROPN", 0)
        verbs = pos_counts.get("VERB", 0) + pos_counts.get("AUX", 0)
        nv_ratio = nouns / max(verbs, 1)

        # Informality score: interjections + particles
        informal = pos_counts.get("INTJ", 0) + pos_counts.get("PART", 0)
        informality = informal / total

        # POS entropy
        probs = [c / total for c in pos_counts.values()]
        pos_entropy = -sum(p * math.log2(p) for p in probs if p > 0)

        # Unique POS bigrams
        bigrams: List[Tuple[str, str]] = [
            (pos_tags[i], pos_tags[i + 1]) for i in range(len(pos_tags) - 1)
        ]
        unique_bigrams = len(set(bigrams))
        total_bigrams = max(len(bigrams), 1)
        bigram_diversity = unique_bigrams / total_bigrams

        # POS distribution (top tags)
        top_pos = dict(pos_counts.most_common(10))

        # Scoring:  AI text -> higher noun/verb ratio, lower informality,
        #           moderate POS entropy, lower bigram diversity
        nv_score = self._sigmoid((nv_ratio - 1.5) / 0.5)
        inf_score = self._sigmoid(-(informality - 0.01) / 0.005)
        ent_score = self._sigmoid(-(pos_entropy - 3.5) / 0.3)
        div_score = self._sigmoid(-(bigram_diversity - 0.6) / 0.1)

        ai_prob = self._clamp(
            0.25 * nv_score + 0.25 * inf_score + 0.25 * ent_score + 0.25 * div_score
        )
        confidence = self._compute_confidence([nv_score, inf_score, ent_score, div_score])

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "noun_verb_ratio": round(nv_ratio, 4),
                "informality_score": round(informality, 4),
                "pos_entropy": round(pos_entropy, 4),
                "unique_pos_bigrams": unique_bigrams,
                "total_pos_bigrams": len(bigrams),
                "bigram_diversity": round(bigram_diversity, 4),
                "pos_distribution": {k: v for k, v in sorted(top_pos.items(), key=lambda x: -x[1])},
                "total_tokens": total,
            },
            "sub_scores": {
                "noun_verb_score": round(nv_score, 4),
                "informality_score_sub": round(inf_score, 4),
                "entropy_score": round(ent_score, 4),
                "diversity_score": round(div_score, 4),
            },
        }
