"""
Internal paraphrase / self-plagiarism detector for ClarityAI.

Splits a single document into sentences, compares every pair using cosine
similarity from sentence-transformers, flags repetitive and self-plagiarised
pairs, and clusters similar sentences together.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Similarity thresholds
REPETITION_THRESHOLD = 0.80
SELF_PLAGIARISM_THRESHOLD = 0.90
CLUSTER_THRESHOLD = 0.80  # minimum similarity to belong to same cluster


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences using punctuation heuristics."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def _split_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs by blank lines."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


class ParaphraseDetector:
    """
    Detects internal repetition and self-plagiarism within a single document
    by comparing all sentence pairs via cosine similarity.
    """

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        """Lazy-load the sentence-transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("ParaphraseDetector: sentence-transformer model loaded.")
            except ImportError:
                logger.error(
                    "sentence-transformers is not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as exc:
                logger.error("Failed to load sentence-transformer: %s", exc)
        return self._model

    # ------------------------------------------------------------------
    # Core similarity computation
    # ------------------------------------------------------------------

    def _compute_similarity_matrix(self, sentences: List[str]) -> Optional[np.ndarray]:
        """Encode all sentences and return an NxN cosine similarity matrix."""
        model = self._get_model()
        if model is None:
            return None

        embeddings = model.encode(sentences, convert_to_numpy=True, show_progress_bar=False)
        # Normalise for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10
        normed = embeddings / norms
        similarity_matrix = normed @ normed.T
        return similarity_matrix

    def _fallback_similarity(self, a: str, b: str) -> float:
        """Word-overlap Jaccard as a crude fallback."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    # ------------------------------------------------------------------
    # Flagging
    # ------------------------------------------------------------------

    def _flag_pairs(
        self,
        sentences: List[str],
        sim_matrix: np.ndarray,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Compare every unique sentence pair.

        Returns:
            repetition_pairs: similarity > REPETITION_THRESHOLD
            plagiarism_pairs: similarity > SELF_PLAGIARISM_THRESHOLD
        """
        n = len(sentences)
        repetition_pairs: List[Dict[str, Any]] = []
        plagiarism_pairs: List[Dict[str, Any]] = []

        for i in range(n):
            for j in range(i + 1, n):
                sim = float(sim_matrix[i, j])
                if sim >= SELF_PLAGIARISM_THRESHOLD:
                    entry = {
                        "sentence_a_index": i,
                        "sentence_b_index": j,
                        "sentence_a": sentences[i][:300],
                        "sentence_b": sentences[j][:300],
                        "similarity": round(sim, 4),
                        "flag": "self_plagiarism",
                    }
                    plagiarism_pairs.append(entry)
                    repetition_pairs.append(entry)
                elif sim >= REPETITION_THRESHOLD:
                    entry = {
                        "sentence_a_index": i,
                        "sentence_b_index": j,
                        "sentence_a": sentences[i][:300],
                        "sentence_b": sentences[j][:300],
                        "similarity": round(sim, 4),
                        "flag": "internal_repetition",
                    }
                    repetition_pairs.append(entry)

        return repetition_pairs, plagiarism_pairs

    # ------------------------------------------------------------------
    # Clustering
    # ------------------------------------------------------------------

    def _cluster_sentences(
        self,
        sentences: List[str],
        sim_matrix: np.ndarray,
    ) -> List[List[int]]:
        """
        Simple greedy clustering: assign each sentence to the first cluster
        whose representative it is similar enough to (>= CLUSTER_THRESHOLD).
        """
        n = len(sentences)
        clusters: List[List[int]] = []
        assigned = set()

        for i in range(n):
            if i in assigned:
                continue
            cluster = [i]
            assigned.add(i)
            for j in range(i + 1, n):
                if j in assigned:
                    continue
                if float(sim_matrix[i, j]) >= CLUSTER_THRESHOLD:
                    cluster.append(j)
                    assigned.add(j)
            clusters.append(cluster)

        return clusters

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze a document for internal paraphrasing and self-plagiarism.

        Returns
        -------
        dict with keys:
            repetition_score       : float 0-1 (fraction of sentences involved in repetition)
            flagged_pairs          : list of dicts (pairs above threshold)
            self_plagiarism_pairs  : list of dicts (pairs above 0.90)
            clusters               : list of list[int] (sentence-index clusters)
            unique_content_ratio   : float 0-1 (unique clusters / total sentences)
            total_sentences        : int
            paragraph_count        : int
        """
        paragraphs = _split_paragraphs(text)
        sentences = _split_sentences(text)

        if len(sentences) < 2:
            return {
                "repetition_score": 0.0,
                "flagged_pairs": [],
                "self_plagiarism_pairs": [],
                "clusters": [],
                "unique_content_ratio": 1.0,
                "total_sentences": len(sentences),
                "paragraph_count": len(paragraphs),
            }

        sim_matrix = self._compute_similarity_matrix(sentences)

        # Fallback: compute pairwise Jaccard if model unavailable
        if sim_matrix is None:
            n = len(sentences)
            sim_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(i, n):
                    if i == j:
                        sim_matrix[i, j] = 1.0
                    else:
                        s = self._fallback_similarity(sentences[i], sentences[j])
                        sim_matrix[i, j] = s
                        sim_matrix[j, i] = s

        repetition_pairs, plagiarism_pairs = self._flag_pairs(sentences, sim_matrix)
        clusters = self._cluster_sentences(sentences, sim_matrix)

        # Sentences involved in at least one repetition flag
        involved_indices: set[int] = set()
        for pair in repetition_pairs:
            involved_indices.add(pair["sentence_a_index"])
            involved_indices.add(pair["sentence_b_index"])

        total = len(sentences)
        repetition_score = len(involved_indices) / total if total > 0 else 0.0

        # Unique content ratio: number of unique clusters / total sentences
        # A cluster of size 1 = fully unique; larger clusters = repetition
        unique_content_ratio = len(clusters) / total if total > 0 else 1.0

        return {
            "repetition_score": round(repetition_score, 4),
            "flagged_pairs": repetition_pairs,
            "self_plagiarism_pairs": plagiarism_pairs,
            "clusters": [
                {
                    "cluster_id": idx,
                    "sentence_indices": cluster,
                    "size": len(cluster),
                    "representative": sentences[cluster[0]][:200],
                }
                for idx, cluster in enumerate(clusters)
            ],
            "unique_content_ratio": round(unique_content_ratio, 4),
            "total_sentences": total,
            "paragraph_count": len(paragraphs),
        }
