"""
Batch File Processing Engine -- Process multiple texts through fast detection
and aggregate the results with statistics and distribution data.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _new_id() -> str:
    return uuid.uuid4().hex


class BatchProcessor:
    """Process multiple texts through fast detection and aggregate results."""

    # ── Quick AI score (same lightweight heuristic used in version_tracker) ─

    @staticmethod
    def _quick_ai_score(text: str) -> float:
        """
        Lightweight AI score heuristic using 3 signals:
        sentence uniformity, vocabulary richness, and average word length.
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

        # Signal 2: Vocabulary richness (low unique ratio = more AI-like)
        unique_ratio = len(set(words)) / len(words)
        vocab_signal = max(0, min(1, 1.0 - unique_ratio))

        # Signal 3: Average word length (AI tends toward 5-6 char words)
        avg_wl = sum(len(w) for w in words) / len(words)
        wl_signal = max(0, min(1, 1.0 - abs(avg_wl - 5.5) / 3.0))

        score = 0.4 * uniformity_signal + 0.3 * vocab_signal + 0.3 * wl_signal
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _classify(score: float) -> str:
        if score >= 0.85:
            return "ai_generated"
        elif score >= 0.50:
            return "mixed"
        else:
            return "human_written"

    @staticmethod
    def _top_signal(text: str) -> str:
        """Determine which of the 3 quick signals contributed most."""
        words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())
        if len(words) < 10:
            return "insufficient_text"

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s for s in sentences if len(s.strip()) > 5]

        # Compute each signal
        sent_lengths = [len(s.split()) for s in sentences] if sentences else [0]
        mean_len = sum(sent_lengths) / max(len(sent_lengths), 1)
        if mean_len > 0:
            std_len = (
                sum((length - mean_len) ** 2 for length in sent_lengths) / len(sent_lengths)
            ) ** 0.5
            cov = std_len / mean_len
        else:
            cov = 0
        uniformity = max(0, min(1, 1.0 - cov))

        unique_ratio = len(set(words)) / len(words)
        vocab = max(0, min(1, 1.0 - unique_ratio))

        avg_wl = sum(len(w) for w in words) / len(words)
        wl = max(0, min(1, 1.0 - abs(avg_wl - 5.5) / 3.0))

        signals = {
            "sentence_uniformity": uniformity,
            "vocabulary_richness": vocab,
            "word_length_pattern": wl,
        }
        return max(signals, key=signals.get)  # type: ignore[arg-type]

    # ── Public API ───────────────────────────────────────────────────────

    def process_batch(
        self,
        texts: List[str],
        filenames: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process a batch of texts through fast detection.

        Args:
            texts: list of text contents to analyze
            filenames: optional list of filenames (same length as texts)

        Returns:
            batch_id, total_files, avg_score, score_distribution,
            flagged_count, results list sorted by AI score descending
        """
        start = time.perf_counter()
        batch_id = _new_id()

        if filenames is None:
            filenames = [f"text_{i + 1}" for i in range(len(texts))]
        elif len(filenames) != len(texts):
            # Pad filenames if mismatched
            filenames = filenames + [f"text_{i + 1}" for i in range(len(filenames), len(texts))]

        results: List[Dict[str, Any]] = []
        scores: List[float] = []

        for idx, (text, filename) in enumerate(zip(texts, filenames)):
            word_count = len(re.findall(r"\S+", text))
            ai_score = self._quick_ai_score(text)
            classification = self._classify(ai_score)
            top_sig = self._top_signal(text)

            scores.append(ai_score)
            results.append(
                {
                    "index": idx,
                    "filename": filename,
                    "word_count": word_count,
                    "ai_score": ai_score,
                    "classification": classification,
                    "top_signal": top_sig,
                }
            )

        # Sort by AI score descending (most suspicious first)
        results.sort(key=lambda r: r["ai_score"], reverse=True)

        # Aggregate statistics
        total_files = len(texts)
        avg_score = round(sum(scores) / max(len(scores), 1), 4)
        flagged_count = sum(1 for s in scores if s >= 0.70)

        # Score distribution: 10 bins from 0.0 to 1.0
        bins = [0] * 10
        for s in scores:
            bin_idx = min(int(s * 10), 9)
            bins[bin_idx] += 1

        score_distribution = [
            {
                "range": f"{i * 0.1:.1f}-{(i + 1) * 0.1:.1f}",
                "count": bins[i],
            }
            for i in range(10)
        ]

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return {
            "batch_id": batch_id,
            "total_files": total_files,
            "avg_score": avg_score,
            "score_distribution": score_distribution,
            "flagged_count": flagged_count,
            "results": results,
            "processing_time_ms": elapsed_ms,
        }
