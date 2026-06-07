"""
Semantic plagiarism detection -- uses sentence embeddings to find paraphrased
or semantically similar passages even when lexical overlap is low.
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    EXACT_COPY = "exact_copy"
    CLOSE_PARAPHRASE = "close_paraphrase"
    SEMANTIC_MATCH = "semantic_match"
    NO_MATCH = "no_match"


# Thresholds
SEMANTIC_SIM_HIGH = 0.85
LEXICAL_OVERLAP_LOW = 0.30
EXACT_COPY_LEXICAL = 0.80
CLOSE_PARAPHRASE_SIM = 0.80


def _load_model():
    """Lazy-load the sentence-transformer model."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded all-MiniLM-L6-v2 for semantic matching.")
        return model
    except Exception as exc:
        logger.error("Could not load sentence-transformers model: %s", exc)
        return None


def _split_sentences(text: str) -> List[str]:
    """Basic sentence splitter."""
    sents = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sents if s.strip() and len(s.split()) >= 3]


def _word_set(text: str) -> set:
    return set(re.sub(r"[^\w\s]", "", text.lower()).split())


def _lexical_overlap(text_a: str, text_b: str) -> float:
    """Word-level Jaccard overlap between two strings."""
    wa = _word_set(text_a)
    wb = _word_set(text_b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-10:
        return 0.0
    return float(np.dot(a, b) / denom)


def _classify_match(semantic_sim: float, lexical_sim: float) -> MatchType:
    """
    Classify the type of match between two text segments.

    - exact_copy:         high semantic sim AND high lexical overlap
    - close_paraphrase:   high semantic sim AND low lexical overlap
    - semantic_match:     moderate-high semantic sim
    - no_match:           low semantic sim
    """
    if semantic_sim >= SEMANTIC_SIM_HIGH and lexical_sim >= EXACT_COPY_LEXICAL:
        return MatchType.EXACT_COPY
    if semantic_sim >= SEMANTIC_SIM_HIGH and lexical_sim < LEXICAL_OVERLAP_LOW:
        return MatchType.CLOSE_PARAPHRASE
    if semantic_sim >= CLOSE_PARAPHRASE_SIM:
        return MatchType.SEMANTIC_MATCH
    return MatchType.NO_MATCH


class SemanticMatcher:
    """
    Compare two documents at the sentence level using dense embeddings from
    ``all-MiniLM-L6-v2`` to detect paraphrasing and semantic copying.
    """

    def __init__(self) -> None:
        self._model = None  # lazy-loaded

    @property
    def model(self):
        if self._model is None:
            self._model = _load_model()
        return self._model

    # ------------------------------------------------------------------
    # Core: pairwise sentence comparison
    # ------------------------------------------------------------------
    def compare_sentences(
        self,
        sentences_a: List[str],
        sentences_b: List[str],
    ) -> List[Dict[str, Any]]:
        """
        For every sentence in *sentences_a*, find the best-matching sentence
        in *sentences_b* and classify the match type.

        Returns a list of match records (one per sentence in A).
        """
        model = self.model
        if model is None:
            logger.warning("Model unavailable; falling back to lexical-only matching.")
            return self._lexical_only_compare(sentences_a, sentences_b)

        if not sentences_a or not sentences_b:
            return []

        # Batch-encode both sets
        emb_a = model.encode(sentences_a, convert_to_numpy=True, show_progress_bar=False)
        emb_b = model.encode(sentences_b, convert_to_numpy=True, show_progress_bar=False)

        matches: List[Dict[str, Any]] = []
        for i, (sent_a, vec_a) in enumerate(zip(sentences_a, emb_a)):
            best_sim = -1.0
            best_j = 0
            for j, vec_b in enumerate(emb_b):
                sim = _cosine_similarity(vec_a, vec_b)
                if sim > best_sim:
                    best_sim = sim
                    best_j = j

            lex_overlap = _lexical_overlap(sent_a, sentences_b[best_j])
            match_type = _classify_match(best_sim, lex_overlap)

            matches.append(
                {
                    "source_sentence": sent_a,
                    "matched_sentence": sentences_b[best_j],
                    "semantic_similarity": round(best_sim, 4),
                    "lexical_overlap": round(lex_overlap, 4),
                    "match_type": match_type.value,
                    "is_paraphrase": (
                        best_sim >= SEMANTIC_SIM_HIGH and lex_overlap < LEXICAL_OVERLAP_LOW
                    ),
                }
            )

        return matches

    def _lexical_only_compare(
        self, sentences_a: List[str], sentences_b: List[str]
    ) -> List[Dict[str, Any]]:
        """Fallback when the embedding model is unavailable."""
        matches: List[Dict[str, Any]] = []
        for sent_a in sentences_a:
            best_lex = -1.0
            best_j = 0
            for j, sent_b in enumerate(sentences_b):
                lex = _lexical_overlap(sent_a, sent_b)
                if lex > best_lex:
                    best_lex = lex
                    best_j = j

            match_type = (
                MatchType.EXACT_COPY if best_lex >= EXACT_COPY_LEXICAL else MatchType.NO_MATCH
            )
            matches.append(
                {
                    "source_sentence": sent_a,
                    "matched_sentence": sentences_b[best_j],
                    "semantic_similarity": best_lex,  # approximate
                    "lexical_overlap": round(best_lex, 4),
                    "match_type": match_type.value,
                    "is_paraphrase": False,
                }
            )
        return matches

    # ------------------------------------------------------------------
    # Document-level comparison
    # ------------------------------------------------------------------
    def compare(
        self,
        text_a: str,
        text_b: str,
    ) -> Dict[str, Any]:
        """
        Compare two full documents and return aggregate similarity metrics.
        """
        sents_a = _split_sentences(text_a)
        sents_b = _split_sentences(text_b)

        if not sents_a or not sents_b:
            return {
                "overall_semantic_similarity": 0.0,
                "matches": [],
                "exact_copies": 0,
                "close_paraphrases": 0,
                "semantic_matches": 0,
                "flagged_sentence_ratio": 0.0,
            }

        matches = self.compare_sentences(sents_a, sents_b)

        exact_count = sum(1 for m in matches if m["match_type"] == MatchType.EXACT_COPY.value)
        para_count = sum(1 for m in matches if m["match_type"] == MatchType.CLOSE_PARAPHRASE.value)
        sem_count = sum(1 for m in matches if m["match_type"] == MatchType.SEMANTIC_MATCH.value)
        flagged = exact_count + para_count + sem_count

        avg_sim = sum(m["semantic_similarity"] for m in matches) / len(matches) if matches else 0.0

        return {
            "overall_semantic_similarity": round(avg_sim, 4),
            "matches": matches,
            "exact_copies": exact_count,
            "close_paraphrases": para_count,
            "semantic_matches": sem_count,
            "flagged_sentence_ratio": round(flagged / len(matches), 4) if matches else 0.0,
        }
