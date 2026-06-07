"""
Exact / near-exact plagiarism detection using document fingerprinting
(Winnowing algorithm), Jaccard similarity, and longest common substring.
"""

import hashlib
import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Winnowing parameters
# ---------------------------------------------------------------------------
DEFAULT_K_GRAM_SIZE = 5  # number of words per k-gram
DEFAULT_WINDOW_SIZE = 4  # winnowing window size


def _normalize(text: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace."""
    import re

    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _kgrams(words: List[str], k: int) -> List[str]:
    """Generate k-gram strings from a word list."""
    return [" ".join(words[i : i + k]) for i in range(len(words) - k + 1)]


def _hash_kgram(kgram: str) -> int:
    """Deterministic integer hash of a k-gram string."""
    return int(hashlib.md5(kgram.encode("utf-8")).hexdigest()[:8], 16)


class ExactMatcher:
    """
    Provides exact and near-exact textual overlap detection between two
    documents using fingerprinting and string-matching algorithms.
    """

    def __init__(
        self,
        k: int = DEFAULT_K_GRAM_SIZE,
        window: int = DEFAULT_WINDOW_SIZE,
    ) -> None:
        self.k = k
        self.window = window

    # ------------------------------------------------------------------
    # Winnowing document fingerprinting
    # ------------------------------------------------------------------
    def fingerprint(self, text: str) -> Set[int]:
        """
        Compute the Winnowing fingerprint set for *text*.

        Returns a set of selected hash values that compactly represent the
        document's content.
        """
        norm = _normalize(text)
        words = norm.split()
        if len(words) < self.k:
            # Too short to fingerprint; return hash of entire text
            return {_hash_kgram(norm)} if norm else set()

        kgrams = _kgrams(words, self.k)
        hashes = [_hash_kgram(kg) for kg in kgrams]

        # Winnowing: select the minimum hash in each window; when there is
        # a tie, prefer the rightmost position.
        fingerprints: Set[int] = set()
        prev_min_idx = -1

        for i in range(len(hashes) - self.window + 1):
            window_hashes = hashes[i : i + self.window]
            # Find rightmost minimum
            min_val = min(window_hashes)
            # Rightmost occurrence of min_val in window
            min_idx = i + self.window - 1 - window_hashes[::-1].index(min_val)
            if min_idx != prev_min_idx:
                fingerprints.add(min_val)
                prev_min_idx = min_idx

        return fingerprints

    # ------------------------------------------------------------------
    # Jaccard similarity on fingerprints
    # ------------------------------------------------------------------
    def jaccard_similarity(self, fp_a: Set[int], fp_b: Set[int]) -> float:
        """Jaccard index between two fingerprint sets."""
        if not fp_a and not fp_b:
            return 0.0
        intersection = fp_a & fp_b
        union = fp_a | fp_b
        return len(intersection) / len(union) if union else 0.0

    # ------------------------------------------------------------------
    # Longest Common Substring
    # ------------------------------------------------------------------
    @staticmethod
    def longest_common_substring(text_a: str, text_b: str) -> Dict[str, Any]:
        """
        Find the longest common substring between two texts (word-level).

        Returns dict with ``substring``, ``length_words``, ``position_a``,
        ``position_b``.
        """
        words_a = _normalize(text_a).split()
        words_b = _normalize(text_b).split()

        if not words_a or not words_b:
            return {"substring": "", "length_words": 0, "position_a": -1, "position_b": -1}

        # Dynamic-programming table (space-optimised to two rows)
        m, n = len(words_a), len(words_b)
        prev = [0] * (n + 1)
        curr = [0] * (n + 1)
        max_len = 0
        end_a = 0

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if words_a[i - 1] == words_b[j - 1]:
                    curr[j] = prev[j - 1] + 1
                    if curr[j] > max_len:
                        max_len = curr[j]
                        end_a = i
                else:
                    curr[j] = 0
            prev, curr = curr, [0] * (n + 1)

        start_a = end_a - max_len
        substring = " ".join(words_a[start_a:end_a])

        # Find position in text_b
        pos_b = -1
        if max_len > 0:
            target = words_a[start_a:end_a]
            for j in range(len(words_b) - max_len + 1):
                if words_b[j : j + max_len] == target:
                    pos_b = j
                    break

        return {
            "substring": substring,
            "length_words": max_len,
            "position_a": start_a,
            "position_b": pos_b,
        }

    # ------------------------------------------------------------------
    # High-level comparison
    # ------------------------------------------------------------------
    def compare(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """
        Full exact-match comparison between two documents.

        Returns dict with jaccard_similarity, fingerprint counts,
        longest_common_substring info, and an overlap_score (0-1).
        """
        fp_a = self.fingerprint(text_a)
        fp_b = self.fingerprint(text_b)
        jaccard = self.jaccard_similarity(fp_a, fp_b)
        lcs = self.longest_common_substring(text_a, text_b)

        # Overlap score: weighted combo of Jaccard and LCS proportion
        words_a_count = len(_normalize(text_a).split())
        lcs_ratio = lcs["length_words"] / max(words_a_count, 1)
        overlap_score = 0.6 * jaccard + 0.4 * lcs_ratio

        return {
            "jaccard_similarity": round(jaccard, 4),
            "fingerprint_count_a": len(fp_a),
            "fingerprint_count_b": len(fp_b),
            "shared_fingerprints": len(fp_a & fp_b),
            "longest_common_substring": lcs,
            "lcs_word_ratio": round(lcs_ratio, 4),
            "overlap_score": round(min(overlap_score, 1.0), 4),
        }
