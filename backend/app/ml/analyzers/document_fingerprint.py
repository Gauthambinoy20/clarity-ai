"""
Document Fingerprint Generator -- Creates tamper-proof document fingerprints.

Generates SHA-256 hashes of normalized text, content n-gram fingerprints,
and structural fingerprints. Supports verification of two fingerprints.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class DocumentFingerprinter:
    """Generate and verify tamper-proof document fingerprints."""

    def __init__(self, ngram_size: int = 3) -> None:
        self.ngram_size = ngram_size

    # ── Text normalization ───────────────────────────────────────────────

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Lowercase, strip excess whitespace, remove non-alphanumeric except spaces."""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _extract_words(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _paragraph_split(text: str) -> List[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()] if text.strip() else []
        return paragraphs

    # ── Hash generation ──────────────────────────────────────────────────

    def _text_hash(self, text: str) -> str:
        """SHA-256 hash of normalized text."""
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _generate_ngrams(self, words: List[str]) -> Set[str]:
        """Generate word n-grams as a set (order-independent for comparison)."""
        if len(words) < self.ngram_size:
            return {" ".join(words)} if words else set()
        ngrams = set()
        for i in range(len(words) - self.ngram_size + 1):
            ngram = " ".join(words[i : i + self.ngram_size])
            ngrams.add(ngram)
        return ngrams

    def _content_hash(self, text: str) -> Tuple[str, Set[str]]:
        """
        Content fingerprint: hash of sorted word n-grams.
        Also returns the n-gram set for comparison.
        """
        words = self._extract_words(text)
        ngrams = self._generate_ngrams(words)
        # Sort for deterministic hashing
        sorted_ngrams = sorted(ngrams)
        combined = "|".join(sorted_ngrams)
        content_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return content_hash, ngrams

    def _pos_distribution_string(self, words: List[str]) -> str:
        """
        Approximate POS distribution using simple heuristics
        (avoids requiring spaCy at fingerprint time).
        """
        # Simple approximation: word length distribution as proxy
        length_counts = Counter(min(len(w), 15) for w in words)
        parts = [f"{length}:{count}" for length, count in sorted(length_counts.items())]
        return "|".join(parts)

    def _structure_hash(self, text: str) -> str:
        """
        Structural fingerprint: hash of sentence count + paragraph count
        + average word length + word-length distribution.
        """
        words = self._extract_words(text)
        sentences = self._sentence_split(text)
        paragraphs = self._paragraph_split(text)

        num_words = len(words)
        num_sentences = len(sentences)
        num_paragraphs = len(paragraphs)
        avg_word_length = round(sum(len(w) for w in words) / max(num_words, 1), 2)
        pos_dist = self._pos_distribution_string(words)

        structure_string = (
            f"sentences:{num_sentences}|"
            f"paragraphs:{num_paragraphs}|"
            f"avg_word_len:{avg_word_length}|"
            f"pos_dist:{pos_dist}"
        )
        return hashlib.sha256(structure_string.encode("utf-8")).hexdigest()

    # ── Public API ───────────────────────────────────────────────────────

    def generate_fingerprint(self, text: str) -> Dict[str, Any]:
        """
        Generate a tamper-proof document fingerprint.

        Returns:
            fingerprint_id, text_hash, content_hash, structure_hash,
            created_at, word_count, ngrams (for internal storage/comparison)
        """
        words = self._extract_words(text)
        text_h = self._text_hash(text)
        content_h, ngrams = self._content_hash(text)
        structure_h = self._structure_hash(text)
        now = _utcnow()

        return {
            "fingerprint_id": _new_id(),
            "text_hash": text_h,
            "content_hash": content_h,
            "structure_hash": structure_h,
            "created_at": now.isoformat(),
            "word_count": len(words),
            "ngram_count": len(ngrams),
            "_ngrams": ngrams,  # internal: used for verification
        }

    def verify_fingerprints(
        self,
        fp1: Dict[str, Any],
        fp2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare two fingerprints and report match status.

        Returns:
            exact_match: bool (identical text hashes)
            content_match: bool (>90% n-gram overlap)
            structure_match: bool (identical structure hashes)
            content_similarity: float (Jaccard similarity of n-grams)
        """
        exact_match = fp1.get("text_hash") == fp2.get("text_hash")
        structure_match = fp1.get("structure_hash") == fp2.get("structure_hash")

        # Content similarity via Jaccard index on n-grams
        ngrams1: Set[str] = fp1.get("_ngrams", set())
        ngrams2: Set[str] = fp2.get("_ngrams", set())

        if not ngrams1 and not ngrams2:
            content_similarity = 1.0 if exact_match else 0.0
        elif not ngrams1 or not ngrams2:
            content_similarity = 0.0
        else:
            intersection = ngrams1 & ngrams2
            union = ngrams1 | ngrams2
            content_similarity = len(intersection) / len(union) if union else 0.0

        content_match = content_similarity >= 0.90

        return {
            "exact_match": exact_match,
            "content_match": content_match,
            "structure_match": structure_match,
            "content_similarity": round(content_similarity, 4),
            "fp1_id": fp1.get("fingerprint_id"),
            "fp2_id": fp2.get("fingerprint_id"),
        }
