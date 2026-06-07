"""
Text comparison engine for ClarityAI.

Compares two texts with similarity metrics, diff generation, and structural analysis.
"""

from __future__ import annotations

import difflib
import math
import re
from collections import Counter
from typing import Any, Dict, List, Set


class TextComparisonEngine:
    """Compares two texts and computes similarity metrics."""

    def analyze(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """Compare two texts and return detailed comparison data."""
        words_a = self._tokenize(text_a)
        words_b = self._tokenize(text_b)

        cosine_sim = self._cosine_similarity(words_a, words_b)
        jaccard_sim = self._jaccard_similarity(words_a, words_b)
        edit_ratio = self._edit_distance_ratio(text_a, text_b)
        common_phrases = self._find_common_phrases(words_a, words_b)
        diff_data = self._generate_diff(text_a, text_b)
        structural = self._structural_comparison(text_a, text_b, words_a, words_b)

        # Overall similarity: weighted combination
        similarity_score = round(cosine_sim * 0.4 + jaccard_sim * 0.3 + edit_ratio * 0.3, 4)

        return {
            "similarity_score": similarity_score,
            "cosine_similarity": round(cosine_sim, 4),
            "jaccard_similarity": round(jaccard_sim, 4),
            "edit_distance_ratio": round(edit_ratio, 4),
            "common_phrases": common_phrases,
            "diff_data": diff_data,
            "structural_comparison": structural,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())

    # ------------------------------------------------------------------
    def _cosine_similarity(self, words_a: List[str], words_b: List[str]) -> float:
        """Compute cosine similarity between two word-frequency vectors."""
        counter_a = Counter(words_a)
        counter_b = Counter(words_b)

        all_words = set(counter_a.keys()) | set(counter_b.keys())
        if not all_words:
            return 0.0

        dot_product = sum(counter_a.get(w, 0) * counter_b.get(w, 0) for w in all_words)
        mag_a = math.sqrt(sum(v**2 for v in counter_a.values()))
        mag_b = math.sqrt(sum(v**2 for v in counter_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)

    def _jaccard_similarity(self, words_a: List[str], words_b: List[str]) -> float:
        """Compute Jaccard similarity of word sets."""
        set_a = set(words_a)
        set_b = set(words_b)

        if not set_a and not set_b:
            return 0.0

        intersection = set_a & set_b
        union = set_a | set_b

        return len(intersection) / len(union) if union else 0.0

    def _edit_distance_ratio(self, text_a: str, text_b: str) -> float:
        """Compute similarity ratio based on edit distance (SequenceMatcher)."""
        return difflib.SequenceMatcher(None, text_a, text_b).ratio()

    # ------------------------------------------------------------------
    def _find_common_phrases(
        self, words_a: List[str], words_b: List[str], min_n: int = 3, max_n: int = 6
    ) -> List[Dict[str, Any]]:
        """Find shared n-grams between the two texts."""
        common: List[Dict[str, Any]] = []
        seen_phrases: Set[str] = set()

        for n in range(max_n, min_n - 1, -1):
            ngrams_a = set(tuple(words_a[i : i + n]) for i in range(len(words_a) - n + 1))
            ngrams_b = set(tuple(words_b[i : i + n]) for i in range(len(words_b) - n + 1))
            shared = ngrams_a & ngrams_b
            for ng in shared:
                phrase = " ".join(ng)
                # Skip if a longer phrase already covers this one
                if any(phrase in longer for longer in seen_phrases):
                    continue
                seen_phrases.add(phrase)
                common.append(
                    {
                        "phrase": phrase,
                        "word_count": n,
                    }
                )

        # Sort by phrase length descending and limit
        common.sort(key=lambda x: x["word_count"], reverse=True)
        return common[:30]

    # ------------------------------------------------------------------
    def _generate_diff(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """Generate a line-by-line diff between two texts."""
        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)

        differ = difflib.unified_diff(lines_a, lines_b, lineterm="", n=3)
        diff_lines = list(differ)

        additions = sum(
            1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
        )
        modifications = min(additions, deletions)

        return {
            "diff_text": "".join(diff_lines),
            "additions": additions,
            "deletions": deletions,
            "estimated_modifications": modifications,
            "total_changes": additions + deletions,
        }

    # ------------------------------------------------------------------
    def _structural_comparison(
        self,
        text_a: str,
        text_b: str,
        words_a: List[str],
        words_b: List[str],
    ) -> Dict[str, Any]:
        """Compare structural characteristics of both texts."""
        sentences_a = self._split_sentences(text_a)
        sentences_b = self._split_sentences(text_b)

        paras_a = [p.strip() for p in text_a.split("\n\n") if p.strip()]
        paras_b = [p.strip() for p in text_b.split("\n\n") if p.strip()]
        if not paras_a:
            paras_a = [text_a.strip()] if text_a.strip() else []
        if not paras_b:
            paras_b = [text_b.strip()] if text_b.strip() else []

        vocab_a = set(words_a)
        vocab_b = set(words_b)
        vocab_overlap = (
            len(vocab_a & vocab_b) / len(vocab_a | vocab_b) if (vocab_a | vocab_b) else 0
        )

        avg_sent_len_a = (len(words_a) / len(sentences_a)) if sentences_a else 0
        avg_sent_len_b = (len(words_b) / len(sentences_b)) if sentences_b else 0

        return {
            "text_a": {
                "word_count": len(words_a),
                "sentence_count": len(sentences_a),
                "paragraph_count": len(paras_a),
                "avg_sentence_length": round(avg_sent_len_a, 2),
                "vocabulary_size": len(vocab_a),
            },
            "text_b": {
                "word_count": len(words_b),
                "sentence_count": len(sentences_b),
                "paragraph_count": len(paras_b),
                "avg_sentence_length": round(avg_sent_len_b, 2),
                "vocabulary_size": len(vocab_b),
            },
            "vocabulary_overlap": round(vocab_overlap, 4),
            "word_count_difference": abs(len(words_a) - len(words_b)),
            "sentence_count_difference": abs(len(sentences_a) - len(sentences_b)),
        }

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]
