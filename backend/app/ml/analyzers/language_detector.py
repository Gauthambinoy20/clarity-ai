"""
Multi-Language Detector.

Detects the language of input text using character n-gram frequency
analysis.  Supports 13 languages with confidence scores, mixed-language
detection, and per-language probability breakdown.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Character-range based detectors (for non-Latin scripts)
# ---------------------------------------------------------------------------

SCRIPT_RANGES: Dict[str, List[Tuple[int, int]]] = {
    "chinese": [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x2F00, 0x2FDF)],
    "japanese": [(0x3040, 0x309F), (0x30A0, 0x30FF), (0x31F0, 0x31FF)],
    "korean": [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
    "hindi": [(0x0900, 0x097F), (0xA8E0, 0xA8FF)],
    "russian": [(0x0400, 0x04FF), (0x0500, 0x052F)],
}


# ---------------------------------------------------------------------------
# Top character trigram profiles per Latin-script language
# (Derived from frequency analysis of large corpora)
# ---------------------------------------------------------------------------

TRIGRAM_PROFILES: Dict[str, Dict[str, float]] = {
    "english": {
        "the": 0.035,
        "and": 0.016,
        "ing": 0.015,
        "tion": 0.012,
        "ent": 0.010,
        "ion": 0.010,
        "her": 0.009,
        "for": 0.009,
        "tha": 0.008,
        "nth": 0.008,
        "ere": 0.008,
        "hat": 0.007,
        "his": 0.007,
        "ith": 0.007,
        "ter": 0.007,
        "was": 0.006,
        "all": 0.006,
        "ati": 0.006,
        "eth": 0.006,
        "ver": 0.006,
        "ous": 0.005,
        "est": 0.005,
        "rea": 0.005,
        "com": 0.005,
        "not": 0.005,
        "igh": 0.005,
        "ght": 0.005,
        "oul": 0.005,
        "men": 0.005,
        "pro": 0.004,
    },
    "spanish": {
        "del": 0.012,
        "ent": 0.011,
        "que": 0.011,
        "cion": 0.010,
        "ado": 0.009,
        "las": 0.009,
        "los": 0.009,
        "nte": 0.008,
        "con": 0.008,
        "est": 0.008,
        "ien": 0.007,
        "por": 0.007,
        "ara": 0.007,
        "ero": 0.007,
        "sta": 0.007,
        "mos": 0.006,
        "tos": 0.006,
        "una": 0.006,
        "res": 0.006,
        "ados": 0.006,
        "aci": 0.006,
        "tra": 0.005,
        "com": 0.005,
        "pre": 0.005,
        "rec": 0.005,
        "par": 0.005,
        "men": 0.005,
        "aba": 0.005,
        "ues": 0.005,
        "ter": 0.005,
    },
    "french": {
        "les": 0.013,
        "ent": 0.012,
        "des": 0.011,
        "que": 0.010,
        "tion": 0.009,
        "ion": 0.009,
        "est": 0.008,
        "ait": 0.008,
        "par": 0.007,
        "ous": 0.007,
        "our": 0.007,
        "sur": 0.007,
        "pas": 0.006,
        "con": 0.006,
        "qui": 0.006,
        "dan": 0.006,
        "ans": 0.006,
        "men": 0.006,
        "com": 0.005,
        "tre": 0.005,
        "eur": 0.005,
        "ais": 0.005,
        "aux": 0.005,
        "ont": 0.005,
        "ell": 0.005,
        "pou": 0.005,
        "aits": 0.005,
        "oir": 0.005,
        "sse": 0.004,
        "eme": 0.004,
    },
    "german": {
        "ein": 0.014,
        "ich": 0.013,
        "sch": 0.012,
        "che": 0.011,
        "der": 0.011,
        "die": 0.010,
        "und": 0.010,
        "den": 0.009,
        "ung": 0.009,
        "ber": 0.008,
        "eit": 0.008,
        "ver": 0.008,
        "ent": 0.007,
        "gen": 0.007,
        "ter": 0.007,
        "ten": 0.007,
        "nen": 0.006,
        "ges": 0.006,
        "ste": 0.006,
        "auf": 0.006,
        "cht": 0.006,
        "nic": 0.006,
        "aus": 0.005,
        "nde": 0.005,
        "ine": 0.005,
        "ier": 0.005,
        "ach": 0.005,
        "war": 0.005,
        "mit": 0.005,
        "das": 0.005,
    },
    "portuguese": {
        "que": 0.012,
        "ent": 0.011,
        "ado": 0.010,
        "dos": 0.009,
        "aco": 0.009,
        "par": 0.008,
        "est": 0.008,
        "com": 0.008,
        "nte": 0.008,
        "mos": 0.007,
        "men": 0.007,
        "uma": 0.007,
        "oes": 0.007,
        "res": 0.006,
        "tra": 0.006,
        "con": 0.006,
        "das": 0.006,
        "pre": 0.006,
        "pro": 0.006,
        "sta": 0.006,
        "cia": 0.005,
        "ter": 0.005,
        "vel": 0.005,
        "ara": 0.005,
        "ais": 0.005,
        "ida": 0.005,
        "ados": 0.005,
        "cao": 0.005,
        "rio": 0.005,
        "ica": 0.005,
    },
    "italian": {
        "che": 0.013,
        "ell": 0.011,
        "ent": 0.010,
        "per": 0.010,
        "del": 0.009,
        "con": 0.009,
        "ato": 0.008,
        "ion": 0.008,
        "azi": 0.008,
        "non": 0.007,
        "tta": 0.007,
        "una": 0.007,
        "lla": 0.007,
        "eri": 0.007,
        "sta": 0.006,
        "nte": 0.006,
        "men": 0.006,
        "gli": 0.006,
        "ono": 0.006,
        "tto": 0.006,
        "ual": 0.005,
        "com": 0.005,
        "pre": 0.005,
        "ter": 0.005,
        "anc": 0.005,
        "ess": 0.005,
        "att": 0.005,
        "ver": 0.005,
        "ire": 0.005,
        "are": 0.005,
    },
    "dutch": {
        "een": 0.014,
        "van": 0.013,
        "het": 0.012,
        "den": 0.011,
        "oor": 0.010,
        "aar": 0.009,
        "ver": 0.009,
        "der": 0.009,
        "ijk": 0.008,
        "ede": 0.008,
        "sch": 0.008,
        "and": 0.007,
        "ing": 0.007,
        "ent": 0.007,
        "gen": 0.007,
        "ter": 0.006,
        "aat": 0.006,
        "die": 0.006,
        "voor": 0.006,
        "erd": 0.006,
        "ond": 0.005,
        "ste": 0.005,
        "ren": 0.005,
        "ach": 0.005,
        "ige": 0.005,
        "eli": 0.005,
        "aan": 0.005,
        "nde": 0.005,
        "als": 0.005,
        "cht": 0.005,
    },
}

# Unique word markers for quick identification
WORD_MARKERS: Dict[str, List[str]] = {
    "english": [
        "the",
        "is",
        "are",
        "was",
        "were",
        "have",
        "has",
        "been",
        "this",
        "that",
        "with",
        "from",
        "they",
        "which",
        "would",
        "could",
        "should",
    ],
    "spanish": [
        "el",
        "la",
        "los",
        "las",
        "del",
        "es",
        "una",
        "por",
        "como",
        "pero",
        "esta",
        "esto",
        "cuando",
        "porque",
        "para",
        "sobre",
        "entre",
    ],
    "french": [
        "le",
        "la",
        "les",
        "des",
        "est",
        "une",
        "que",
        "dans",
        "pour",
        "avec",
        "sur",
        "pas",
        "qui",
        "mais",
        "sont",
        "cette",
        "nous",
    ],
    "german": [
        "der",
        "die",
        "das",
        "und",
        "ist",
        "ein",
        "eine",
        "nicht",
        "mit",
        "auf",
        "sich",
        "auch",
        "ich",
        "wird",
        "aus",
        "aber",
        "wenn",
    ],
    "portuguese": [
        "o",
        "os",
        "uma",
        "que",
        "nao",
        "para",
        "com",
        "por",
        "mais",
        "como",
        "esta",
        "dos",
        "das",
        "foi",
        "pode",
        "entre",
        "sobre",
    ],
    "italian": [
        "il",
        "gli",
        "una",
        "che",
        "non",
        "con",
        "per",
        "sono",
        "della",
        "questo",
        "anche",
        "come",
        "quando",
        "stato",
        "essere",
        "fatto",
    ],
    "dutch": [
        "het",
        "een",
        "van",
        "dat",
        "niet",
        "zijn",
        "voor",
        "ook",
        "maar",
        "naar",
        "deze",
        "werd",
        "door",
        "heeft",
        "worden",
        "veel",
    ],
    "russian": [],
    "chinese": [],
    "japanese": [],
    "korean": [],
    "arabic": [],
    "hindi": [],
}


def _extract_trigrams(text: str) -> Counter:
    """Extract character trigrams from text, lowercased and stripped of punctuation."""
    clean = re.sub(r"[^\w\s]", "", text.lower())
    clean = re.sub(r"\s+", " ", clean).strip()
    trigrams: Counter = Counter()
    for i in range(len(clean) - 2):
        tri = clean[i : i + 3]
        if " " not in tri:
            trigrams[tri] += 1
    return trigrams


def _cosine_similarity(profile: Dict[str, float], text_trigrams: Counter) -> float:
    """Compute cosine similarity between a language profile and text trigrams."""
    total = sum(text_trigrams.values())
    if total == 0:
        return 0.0

    text_freq = {k: v / total for k, v in text_trigrams.items()}

    # Dot product
    dot = sum(
        profile.get(tri, 0.0) * text_freq.get(tri, 0.0) for tri in set(profile) | set(text_freq)
    )

    # Magnitudes
    mag_profile = sum(v**2 for v in profile.values()) ** 0.5
    mag_text = sum(v**2 for v in text_freq.values()) ** 0.5

    if mag_profile == 0 or mag_text == 0:
        return 0.0

    return dot / (mag_profile * mag_text)


def _detect_script(text: str) -> Dict[str, float]:
    """Detect character script distribution in text."""
    char_counts: Dict[str, int] = {}
    total_chars = 0

    for ch in text:
        if ch.isspace() or ch in ".,!?;:'\"-()[]{}":
            continue
        total_chars += 1
        code = ord(ch)
        found = False
        for script_name, ranges in SCRIPT_RANGES.items():
            for lo, hi in ranges:
                if lo <= code <= hi:
                    char_counts[script_name] = char_counts.get(script_name, 0) + 1
                    found = True
                    break
            if found:
                break
        if not found:
            char_counts["latin"] = char_counts.get("latin", 0) + 1

    if total_chars == 0:
        return {}

    return {k: v / total_chars for k, v in char_counts.items()}


def _word_marker_score(text: str, language: str) -> float:
    """Score based on presence of language-specific function words."""
    markers = WORD_MARKERS.get(language, [])
    if not markers:
        return 0.0

    words = set(re.findall(r"\b\w+\b", text.lower()))
    if not words:
        return 0.0

    hits = sum(1 for m in markers if m in words)
    return hits / len(markers)


class LanguageDetector:
    """
    Multi-language detector using character n-gram frequency analysis.

    Supports: English, Spanish, French, German, Portuguese, Italian,
    Dutch, Russian, Chinese, Japanese, Korean, Arabic, Hindi.
    """

    SUPPORTED_LANGUAGES = [
        "english",
        "spanish",
        "french",
        "german",
        "portuguese",
        "italian",
        "dutch",
        "russian",
        "chinese",
        "japanese",
        "korean",
        "arabic",
        "hindi",
    ]

    LANGUAGE_NAMES = {
        "english": "English",
        "spanish": "Spanish",
        "french": "French",
        "german": "German",
        "portuguese": "Portuguese",
        "italian": "Italian",
        "dutch": "Dutch",
        "russian": "Russian",
        "chinese": "Chinese",
        "japanese": "Japanese",
        "korean": "Korean",
        "arabic": "Arabic",
        "hindi": "Hindi",
    }

    def analyze(self, text: str) -> dict:
        """
        Detect the language(s) of the input text.

        Returns:
            primary_language: Most likely language.
            confidence: Confidence score for primary language (0-1).
            all_languages_scores: Dict of all language scores.
            is_mixed: Whether multiple languages are detected.
        """
        if not text or len(text.strip()) < 3:
            return {
                "primary_language": "unknown",
                "confidence": 0.0,
                "all_languages_scores": {},
                "is_mixed": False,
                "error": "text too short for detection",
            }

        # Step 1: Detect character scripts
        script_dist = _detect_script(text)

        scores: Dict[str, float] = {}

        # Step 2: Non-Latin script detection
        for script_lang in ["chinese", "japanese", "korean", "arabic", "hindi", "russian"]:
            script_key = script_lang
            if script_key in script_dist:
                scores[script_lang] = script_dist[script_key]

        # Step 3: Trigram analysis for Latin-script languages
        latin_fraction = script_dist.get("latin", 0.0)
        if latin_fraction > 0.3:
            trigrams = _extract_trigrams(text)
            for lang, profile in TRIGRAM_PROFILES.items():
                tri_score = _cosine_similarity(profile, trigrams)
                word_score = _word_marker_score(text, lang)
                # Combine trigram and word marker signals
                combined = tri_score * 0.6 + word_score * 0.4
                scores[lang] = combined * latin_fraction

        # Step 4: Ensure all supported languages have a score
        for lang in self.SUPPORTED_LANGUAGES:
            if lang not in scores:
                scores[lang] = 0.0

        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        else:
            scores = {k: 1.0 / len(self.SUPPORTED_LANGUAGES) for k in self.SUPPORTED_LANGUAGES}

        # Sort by score
        sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

        # Determine primary language
        primary = next(iter(sorted_scores))
        primary_score = sorted_scores[primary]

        # Determine confidence
        confidence = min(primary_score, 1.0)

        # Mixed language detection
        significant_langs = [lang for lang, score in sorted_scores.items() if score > 0.15]
        is_mixed = len(significant_langs) > 1

        # Format all language scores with human-readable names
        all_scores = {
            self.LANGUAGE_NAMES.get(lang, lang): round(score, 4)
            for lang, score in sorted_scores.items()
            if score > 0.001
        }

        return {
            "primary_language": self.LANGUAGE_NAMES.get(primary, primary),
            "primary_language_code": primary,
            "confidence": round(confidence, 4),
            "all_languages_scores": all_scores,
            "is_mixed": is_mixed,
            "detected_languages": [
                {
                    "language": self.LANGUAGE_NAMES.get(lang, lang),
                    "code": lang,
                    "score": round(score, 4),
                }
                for lang, score in sorted_scores.items()
                if score > 0.05
            ],
            "script_distribution": {k: round(v, 4) for k, v in script_dist.items()},
        }
