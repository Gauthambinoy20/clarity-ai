"""
Version Tracker -- Track text versions and score changes over time.

Stores each version with version number, text, AI score, and timestamp.
Computes diffs between consecutive versions and tracks score trajectory.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class VersionTracker:
    """
    Track document versions and score changes.

    Uses an in-memory store keyed by document_id. In production this
    would be backed by a database table; here we store in a class-level
    dict so the data persists for the lifetime of the process.
    """

    # Class-level store: document_id -> list of version dicts
    _store: Dict[str, List[Dict[str, Any]]] = {}

    # ── Diff helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\S+", text)

    @classmethod
    def _compute_diff(cls, old_text: str, new_text: str) -> Dict[str, int]:
        """
        Compute a simple word-level diff between two texts.

        Returns counts of words added, removed, and changed.
        """
        old_words = cls._tokenize(old_text)
        new_words = cls._tokenize(new_text)

        # Use a simple LCS-inspired approach via Counter for speed
        from collections import Counter

        old_counts = Counter(old_words)
        new_counts = Counter(new_words)

        all_words = set(old_counts.keys()) | set(new_counts.keys())

        words_added = 0
        words_removed = 0
        words_changed = 0

        for word in all_words:
            old_c = old_counts.get(word, 0)
            new_c = new_counts.get(word, 0)
            if old_c == 0 and new_c > 0:
                words_added += new_c
            elif old_c > 0 and new_c == 0:
                words_removed += old_c
            elif old_c != new_c:
                diff = abs(new_c - old_c)
                if new_c > old_c:
                    words_added += diff
                else:
                    words_removed += diff

        # Approximate "changed" words: words present in both but in different positions
        # We estimate by looking at positional differences
        min_len = min(len(old_words), len(new_words))
        positional_changes = 0
        for i in range(min_len):
            if old_words[i] != new_words[i]:
                positional_changes += 1

        # Words changed = positional changes minus additions/removals already counted
        words_changed = max(0, positional_changes - words_added - words_removed)

        return {
            "words_added": words_added,
            "words_removed": words_removed,
            "words_changed": words_changed,
        }

    # ── Fake score computation (lightweight) ─────────────────────────────

    @staticmethod
    def _quick_ai_score(text: str) -> float:
        """
        Quick heuristic AI score for version tracking.
        Uses simple statistical signals rather than full ML pipeline.
        """
        words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())
        if len(words) < 10:
            return 0.5

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s for s in sentences if len(s.strip()) > 5]
        if not sentences:
            return 0.5

        # Signal 1: Sentence length uniformity
        sent_lengths = [len(s.split()) for s in sentences]
        mean_len = sum(sent_lengths) / len(sent_lengths)
        if mean_len > 0:
            std_len = (
                sum((length - mean_len) ** 2 for length in sent_lengths) / len(sent_lengths)
            ) ** 0.5
            cov = std_len / mean_len
        else:
            cov = 0
        uniformity_signal = max(0, min(1, 1.0 - cov))

        # Signal 2: Vocabulary richness
        unique_ratio = len(set(words)) / len(words)
        # AI text tends to have lower unique ratio
        vocab_signal = max(0, min(1, 1.0 - unique_ratio))

        # Signal 3: Average word length (AI tends toward medium-length words)
        avg_wl = sum(len(w) for w in words) / len(words)
        # AI average tends to be 5-6 chars
        wl_signal = max(0, min(1, 1.0 - abs(avg_wl - 5.5) / 3.0))

        score = 0.4 * uniformity_signal + 0.3 * vocab_signal + 0.3 * wl_signal
        return round(max(0.0, min(1.0, score)), 4)

    # ── Public API ───────────────────────────────────────────────────────

    def add_version(
        self,
        document_id: str,
        text: str,
        ai_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Add a new version of a document.

        If ai_score is not provided, a quick heuristic score is computed.

        Returns:
            version_number, previous_score, current_score, score_change,
            diff_summary, versions list
        """
        if document_id not in self._store:
            self._store[document_id] = []

        versions = self._store[document_id]
        version_number = len(versions) + 1
        current_score = ai_score if ai_score is not None else self._quick_ai_score(text)
        now = _utcnow()

        # Compute diff against previous version
        previous_score: Optional[float] = None
        diff_summary: Optional[Dict[str, int]] = None
        if versions:
            prev = versions[-1]
            previous_score = prev["ai_score"]
            diff_summary = self._compute_diff(prev["text"], text)
        else:
            diff_summary = {
                "words_added": len(self._tokenize(text)),
                "words_removed": 0,
                "words_changed": 0,
            }

        version_entry = {
            "version_number": version_number,
            "text": text,
            "ai_score": current_score,
            "timestamp": now.isoformat(),
            "word_count": len(self._tokenize(text)),
            "diff_summary": diff_summary,
        }
        versions.append(version_entry)

        score_change = (
            round(current_score - previous_score, 4) if previous_score is not None else 0.0
        )

        # Build score trajectory
        score_trajectory = [
            {"version": v["version_number"], "score": v["ai_score"], "timestamp": v["timestamp"]}
            for v in versions
        ]

        return {
            "document_id": document_id,
            "version_number": version_number,
            "previous_score": previous_score,
            "current_score": current_score,
            "score_change": score_change,
            "diff_summary": diff_summary,
            "score_trajectory": score_trajectory,
            "total_versions": len(versions),
        }

    def get_history(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full version history for a document.

        Returns None if document_id is not found.
        """
        if document_id not in self._store:
            return None

        versions = self._store[document_id]
        version_summaries = []
        for v in versions:
            summary = {
                "version_number": v["version_number"],
                "ai_score": v["ai_score"],
                "timestamp": v["timestamp"],
                "word_count": v["word_count"],
                "diff_summary": v["diff_summary"],
            }
            version_summaries.append(summary)

        score_trajectory = [
            {"version": v["version_number"], "score": v["ai_score"], "timestamp": v["timestamp"]}
            for v in versions
        ]

        latest = versions[-1] if versions else None

        return {
            "document_id": document_id,
            "total_versions": len(versions),
            "latest_version": latest["version_number"] if latest else 0,
            "latest_score": latest["ai_score"] if latest else None,
            "score_trajectory": score_trajectory,
            "versions": version_summaries,
        }
