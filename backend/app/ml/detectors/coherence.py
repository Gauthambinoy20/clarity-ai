"""
Detector 10 -- Coherence Analysis.

Sentence embedding similarity using sentence-transformers.
Adjacent and skip-1 similarities, coherence-drop detection.
Abnormally high coherence suggests AI authorship.
"""

from __future__ import annotations

import re
import logging
from typing import List

import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class CoherenceDetector(BaseDetector):

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return float(dot / norm) if norm > 0 else 0.0

    async def analyze(self, text: str) -> dict:
        signal = "coherence"
        sentences = self._sentence_split(text)
        if len(sentences) < 3:
            return self._empty_result(signal, "need >= 3 sentences")

        st_model = await ModelRegistry.get_model("sentence-transformers")
        embeddings = st_model.encode(sentences, show_progress_bar=False)

        # Adjacent similarities
        adj_sims: List[float] = []
        for i in range(len(embeddings) - 1):
            adj_sims.append(self._cosine_sim(embeddings[i], embeddings[i + 1]))

        # Skip-1 similarities
        skip_sims: List[float] = []
        for i in range(len(embeddings) - 2):
            skip_sims.append(self._cosine_sim(embeddings[i], embeddings[i + 2]))

        mean_adj = float(np.mean(adj_sims))
        std_adj = float(np.std(adj_sims))
        mean_skip = float(np.mean(skip_sims)) if skip_sims else 0.0

        # Coherence drops (similarity < mean - 2*std)
        threshold = mean_adj - 2 * std_adj
        drops = [
            {"position": i, "similarity": round(adj_sims[i], 4)}
            for i in range(len(adj_sims))
            if adj_sims[i] < threshold
        ]

        # High coherence + low variance -> AI
        coh_score = self._sigmoid((mean_adj - 0.45) / 0.15)
        var_score = self._sigmoid(-(std_adj - 0.1) / 0.05)
        skip_score = self._sigmoid((mean_skip - 0.35) / 0.15)

        ai_prob = self._clamp(0.40 * coh_score + 0.30 * var_score + 0.30 * skip_score)
        confidence = self._compute_confidence([coh_score, var_score, skip_score])

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "mean_adjacent_similarity": round(mean_adj, 4),
                "std_adjacent_similarity": round(std_adj, 4),
                "mean_skip1_similarity": round(mean_skip, 4),
                "num_sentences": len(sentences),
                "coherence_drops": drops,
                "adjacent_similarities": [round(s, 4) for s in adj_sims],
            },
            "sub_scores": {
                "coherence_score": round(coh_score, 4),
                "variance_score": round(var_score, 4),
                "skip_score": round(skip_score, 4),
            },
        }
