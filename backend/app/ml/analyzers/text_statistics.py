"""
Comprehensive text statistics engine for ClarityAI.

Computes word counts, distributions, POS ratios, and more.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopwords (English subset for word-cloud / frequency filtering)
# ---------------------------------------------------------------------------

_STOPWORDS: set[str] = {
    "a",
    "an",
    "the",
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
    "is",
    "it",
    "as",
    "was",
    "are",
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
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "its",
    "our",
    "their",
    "what",
    "which",
    "who",
    "whom",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "because",
    "if",
    "about",
    "up",
    "out",
    "then",
    "into",
    "also",
    "after",
    "before",
    "over",
    "between",
    "through",
    "during",
    "without",
    "again",
    "further",
    "once",
    "here",
    "there",
    "any",
    "am",
    "were",
    "while",
}

# ---------------------------------------------------------------------------
# Common word lists for simple language detection
# ---------------------------------------------------------------------------

_LANG_MARKERS: Dict[str, set[str]] = {
    "English": {"the", "is", "and", "of", "to", "in", "that", "it", "was", "for", "with", "are"},
    "Spanish": {"el", "la", "de", "en", "los", "las", "del", "que", "por", "con", "una", "es"},
    "French": {"le", "la", "de", "les", "des", "un", "une", "du", "est", "dans", "que", "pour"},
    "German": {"der", "die", "und", "das", "ist", "ein", "eine", "den", "von", "zu", "mit", "auf"},
}


def _load_spacy():
    try:
        import spacy

        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli import download

            download("en_core_web_sm")
            return spacy.load("en_core_web_sm")
    except ImportError:
        logger.warning("spaCy not installed — POS statistics will be unavailable")
        return None


class TextStatisticsAnalyzer:
    """Computes comprehensive text statistics."""

    def __init__(self) -> None:
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = _load_spacy()
        return self._nlp

    def analyze(self, text: str) -> Dict[str, Any]:
        """Run full text statistics analysis."""
        words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text)
        words_lower = [w.lower() for w in words]
        sentences = self._split_sentences(text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()] if text.strip() else []

        num_words = len(words)
        num_sentences = max(len(sentences), 1)
        num_paragraphs = len(paragraphs)
        num_chars_with_spaces = len(text)
        num_chars_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

        avg_word_length = (sum(len(w) for w in words) / num_words) if num_words else 0
        avg_sentence_length = num_words / num_sentences if num_sentences else 0

        # Unique words / vocabulary
        unique_words = set(words_lower)
        vocabulary_size = len(unique_words)

        # Most common words (excluding stopwords)
        filtered_words = [w for w in words_lower if w not in _STOPWORDS and len(w) > 2]
        word_freq = Counter(filtered_words)
        most_common_words = word_freq.most_common(20)

        # Most common bigrams
        bigrams = [
            (words_lower[i], words_lower[i + 1])
            for i in range(len(words_lower) - 1)
            if words_lower[i] not in _STOPWORDS and words_lower[i + 1] not in _STOPWORDS
        ]
        bigram_freq = Counter(bigrams)
        most_common_bigrams = [
            {"bigram": f"{b[0]} {b[1]}", "count": c} for b, c in bigram_freq.most_common(10)
        ]

        # Word length distribution
        word_lengths = [len(w) for w in words]
        wl_counter = Counter(word_lengths)
        word_length_distribution = [
            {"length": length, "count": count} for length, count in sorted(wl_counter.items())
        ]

        # Sentence length distribution
        sent_lengths = [len(s.split()) for s in sentences]
        sl_counter = Counter(sent_lengths)
        sentence_length_distribution = [
            {"length": length, "count": count} for length, count in sorted(sl_counter.items())
        ]

        # POS distribution
        pos_distribution = self._get_pos_distribution(text)

        # Word cloud data (top 100)
        word_cloud_data = [{"word": w, "frequency": c} for w, c in word_freq.most_common(100)]

        # Time estimates
        reading_time_minutes = round(num_words / 250, 2) if num_words else 0
        speaking_time_minutes = round(num_words / 150, 2) if num_words else 0

        # Language detection
        detected_language = self._detect_language(words_lower)

        return {
            "word_count": num_words,
            "character_count_with_spaces": num_chars_with_spaces,
            "character_count_without_spaces": num_chars_no_spaces,
            "sentence_count": len(sentences),
            "paragraph_count": num_paragraphs,
            "avg_word_length": round(avg_word_length, 2),
            "avg_sentence_length": round(avg_sentence_length, 2),
            "unique_words": vocabulary_size,
            "vocabulary_richness": round(vocabulary_size / num_words, 4) if num_words else 0,
            "most_common_words": [{"word": w, "count": c} for w, c in most_common_words],
            "most_common_bigrams": most_common_bigrams,
            "word_length_distribution": word_length_distribution,
            "sentence_length_distribution": sentence_length_distribution,
            "pos_distribution": pos_distribution,
            "word_cloud_data": word_cloud_data,
            "reading_time_minutes": reading_time_minutes,
            "speaking_time_minutes": speaking_time_minutes,
            "detected_language": detected_language,
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _get_pos_distribution(self, text: str) -> Dict[str, Any]:
        """Get part-of-speech distribution as percentages."""
        nlp = self.nlp
        if nlp is None:
            return {}

        doc = nlp(text)
        total = len(doc) or 1
        pos_counts: Dict[str, int] = {}
        for token in doc:
            label = token.pos_
            pos_counts[label] = pos_counts.get(label, 0) + 1

        pos_labels = {
            "NOUN": "nouns",
            "VERB": "verbs",
            "ADJ": "adjectives",
            "ADV": "adverbs",
            "PRON": "pronouns",
            "DET": "determiners",
            "ADP": "prepositions",
            "CONJ": "conjunctions",
            "CCONJ": "conjunctions",
            "NUM": "numerals",
            "PROPN": "proper_nouns",
            "AUX": "auxiliary_verbs",
            "PUNCT": "punctuation",
        }

        distribution = {}
        for pos, label in pos_labels.items():
            count = pos_counts.get(pos, 0)
            if label in distribution:
                distribution[label]["count"] += count
                distribution[label]["percentage"] = round(
                    distribution[label]["count"] / total * 100, 2
                )
            else:
                distribution[label] = {
                    "count": count,
                    "percentage": round(count / total * 100, 2),
                }

        return distribution

    @staticmethod
    def _detect_language(words: List[str]) -> Dict[str, Any]:
        """Basic language detection by matching common word frequencies."""
        if not words:
            return {"language": "unknown", "confidence": 0.0}

        word_set = set(words[:500])  # sample first 500 words
        scores: Dict[str, float] = {}

        for lang, markers in _LANG_MARKERS.items():
            match_count = len(word_set & markers)
            scores[lang] = match_count / len(markers)

        if not scores:
            return {"language": "unknown", "confidence": 0.0}

        best_lang = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_lang]

        if best_score < 0.1:
            return {"language": "unknown", "confidence": round(best_score, 4)}

        return {"language": best_lang, "confidence": round(min(1.0, best_score), 4)}
