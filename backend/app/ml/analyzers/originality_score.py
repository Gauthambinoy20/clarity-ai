"""
Advanced Originality Scoring.

Combines AI detection score, plagiarism score, vocabulary uniqueness,
and structural originality into a single 0-100 "Originality Score"
with categorical labels and detailed breakdown.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEIGHTS = {
    "ai_detection": 0.40,
    "plagiarism": 0.30,
    "vocabulary_uniqueness": 0.15,
    "structural_originality": 0.15,
}

CATEGORY_THRESHOLDS: List[Tuple[float, str]] = [
    (85.0, "Highly Original"),
    (70.0, "Mostly Original"),
    (50.0, "Partially Original"),
    (30.0, "Low Originality"),
    (0.0, "Not Original"),
]


def _categorize(score: float) -> str:
    """Map a 0-100 score to a category label."""
    for threshold, label in CATEGORY_THRESHOLDS:
        if score >= threshold:
            return label
    return "Not Original"


# ---------------------------------------------------------------------------
# Sub-scorers
# ---------------------------------------------------------------------------


def _vocabulary_uniqueness(text: str) -> Dict[str, Any]:
    """
    Compute vocabulary uniqueness metrics.

    - Type-Token Ratio (TTR)
    - Hapax legomena ratio (words appearing exactly once)
    - Average word length deviation from mean
    - Rare word percentage
    """
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if not words:
        return {"score": 50.0, "details": {}}

    word_count = len(words)
    unique_words = set(words)
    unique_count = len(unique_words)

    # Type-Token Ratio (adjusted for text length using root TTR)
    root_ttr = unique_count / math.sqrt(word_count) if word_count > 0 else 0

    # Hapax legomena (words appearing exactly once)
    freq = Counter(words)
    hapax = sum(1 for w, c in freq.items() if c == 1)
    hapax_ratio = hapax / max(word_count, 1)

    # Average word length (longer/more diverse = more original)
    avg_length = sum(len(w) for w in words) / max(word_count, 1)
    length_variety = sum(abs(len(w) - avg_length) for w in words) / max(word_count, 1)

    # Common words ratio (lower = more original)
    COMMON_WORDS = {
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "it",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        "not",
        "no",
        "so",
        "if",
        "as",
        "very",
        "just",
        "about",
        "up",
        "out",
        "then",
        "than",
    }
    common_count = sum(1 for w in words if w in COMMON_WORDS)
    common_ratio = common_count / max(word_count, 1)
    non_common_ratio = 1.0 - common_ratio

    # Combine into a 0-100 score
    # root_ttr typically ranges 3-12 for normal text
    ttr_score = min(root_ttr / 10.0, 1.0) * 100
    hapax_score = min(hapax_ratio / 0.6, 1.0) * 100
    variety_score = min(length_variety / 3.0, 1.0) * 100
    richness_score = min(non_common_ratio / 0.7, 1.0) * 100

    final = ttr_score * 0.35 + hapax_score * 0.25 + variety_score * 0.15 + richness_score * 0.25

    return {
        "score": round(max(0, min(100, final)), 2),
        "details": {
            "type_token_ratio": round(root_ttr, 4),
            "hapax_ratio": round(hapax_ratio, 4),
            "avg_word_length": round(avg_length, 2),
            "length_variety": round(length_variety, 4),
            "unique_word_count": unique_count,
            "total_word_count": word_count,
            "common_word_ratio": round(common_ratio, 4),
        },
    }


def _structural_originality(text: str) -> Dict[str, Any]:
    """
    Assess structural originality.

    Detects formulaic structures commonly used by AI:
    - Uniform paragraph lengths (AI tends to be more uniform)
    - Predictable sentence length patterns
    - Formulaic transitions
    - Repetitive sentence starters
    """
    # Split into paragraphs and sentences
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    sentences = re.split(r"[.!?]+\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if len(sentences) < 3:
        return {"score": 50.0, "details": {}}

    # Paragraph length variance (higher variance = more human-like)
    if len(paragraphs) > 1:
        para_lengths = [len(p.split()) for p in paragraphs]
        para_mean = sum(para_lengths) / len(para_lengths)
        para_var = sum((length - para_mean) ** 2 for length in para_lengths) / len(para_lengths)
        para_cv = (para_var**0.5) / max(para_mean, 1)  # coefficient of variation
    else:
        para_cv = 0.3  # neutral

    # Sentence length variance
    sent_lengths = [len(s.split()) for s in sentences]
    sent_mean = sum(sent_lengths) / len(sent_lengths)
    sent_var = sum((length - sent_mean) ** 2 for length in sent_lengths) / len(sent_lengths)
    sent_cv = (sent_var**0.5) / max(sent_mean, 1)

    # Sentence starter diversity
    starters = [s.split()[0].lower() if s.split() else "" for s in sentences]
    starter_unique = len(set(starters))
    starter_diversity = starter_unique / max(len(starters), 1)

    # Formulaic transition check
    FORMULAIC_TRANSITIONS = [
        r"\bfurthermore\b",
        r"\bmoreover\b",
        r"\badditionally\b",
        r"\bin conclusion\b",
        r"\bin summary\b",
        r"\bto summarize\b",
        r"\bfirstly\b",
        r"\bsecondly\b",
        r"\bthirdly\b",
        r"\bin addition\b",
        r"\bconsequently\b",
        r"\btherefore\b",
    ]
    lower = text.lower()
    transition_hits = sum(len(re.findall(pat, lower)) for pat in FORMULAIC_TRANSITIONS)
    transition_density = transition_hits / max(len(sentences), 1)

    # Numbered/bullet list detection
    list_lines = len(re.findall(r"^\s*(?:\d+\.|\-|\*)\s+", text, re.MULTILINE))
    list_ratio = list_lines / max(len(sentences), 1)

    # Compute score (higher = more original)
    # Higher CV = more varied = more original
    para_score = min(para_cv / 0.6, 1.0) * 100
    sent_score = min(sent_cv / 0.5, 1.0) * 100
    starter_score = starter_diversity * 100
    # Lower transition density = more original
    transition_score = max(0, (1.0 - transition_density * 3)) * 100
    # Lower list ratio = more original
    list_score = max(0, (1.0 - list_ratio * 2)) * 100

    final = (
        para_score * 0.15
        + sent_score * 0.25
        + starter_score * 0.25
        + transition_score * 0.20
        + list_score * 0.15
    )

    return {
        "score": round(max(0, min(100, final)), 2),
        "details": {
            "paragraph_length_cv": round(para_cv, 4),
            "sentence_length_cv": round(sent_cv, 4),
            "sentence_starter_diversity": round(starter_diversity, 4),
            "transition_density": round(transition_density, 4),
            "list_ratio": round(list_ratio, 4),
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
        },
    }


class OriginalityScorer:
    """
    Produces a single 0-100 Originality Score by combining:
      - AI detection score (40%)
      - Plagiarism score (30%)
      - Vocabulary uniqueness (15%)
      - Structural originality (15%)
    """

    def analyze(
        self,
        text: str,
        ai_score: float = 0.5,
        plagiarism_score: float = 0.0,
    ) -> dict:
        """
        Compute the originality score.

        Args:
            text: The input text to analyse.
            ai_score: AI detection probability (0-1, where 1 = AI-generated).
            plagiarism_score: Plagiarism probability (0-1, where 1 = plagiarised).

        Returns:
            Dictionary with overall score, category, and detailed breakdown.
        """
        if not text or len(text.split()) < 10:
            return {
                "originality_score": 50.0,
                "category": "Partially Original",
                "breakdown": {},
                "error": "text too short for meaningful analysis",
            }

        # Compute internal metrics
        vocab_result = _vocabulary_uniqueness(text)
        struct_result = _structural_originality(text)

        # Convert AI score to originality component (invert: low AI = high originality)
        ai_originality = (1.0 - ai_score) * 100.0

        # Convert plagiarism score to originality component
        plag_originality = (1.0 - plagiarism_score) * 100.0

        vocab_score = vocab_result["score"]
        struct_score = struct_result["score"]

        # Weighted combination
        overall = (
            ai_originality * WEIGHTS["ai_detection"]
            + plag_originality * WEIGHTS["plagiarism"]
            + vocab_score * WEIGHTS["vocabulary_uniqueness"]
            + struct_score * WEIGHTS["structural_originality"]
        )

        overall = max(0.0, min(100.0, overall))
        category = _categorize(overall)

        return {
            "originality_score": round(overall, 2),
            "category": category,
            "breakdown": {
                "ai_detection": {
                    "score": round(ai_originality, 2),
                    "weight": WEIGHTS["ai_detection"],
                    "weighted_contribution": round(ai_originality * WEIGHTS["ai_detection"], 2),
                    "description": "Inverse of AI detection probability",
                    "raw_ai_score": round(ai_score, 4),
                },
                "plagiarism": {
                    "score": round(plag_originality, 2),
                    "weight": WEIGHTS["plagiarism"],
                    "weighted_contribution": round(plag_originality * WEIGHTS["plagiarism"], 2),
                    "description": "Inverse of plagiarism probability",
                    "raw_plagiarism_score": round(plagiarism_score, 4),
                },
                "vocabulary_uniqueness": {
                    "score": round(vocab_score, 2),
                    "weight": WEIGHTS["vocabulary_uniqueness"],
                    "weighted_contribution": round(
                        vocab_score * WEIGHTS["vocabulary_uniqueness"], 2
                    ),
                    "description": "Vocabulary diversity and richness",
                    "details": vocab_result["details"],
                },
                "structural_originality": {
                    "score": round(struct_score, 2),
                    "weight": WEIGHTS["structural_originality"],
                    "weighted_contribution": round(
                        struct_score * WEIGHTS["structural_originality"], 2
                    ),
                    "description": "Writing structure diversity and non-formulaic patterns",
                    "details": struct_result["details"],
                },
            },
        }
