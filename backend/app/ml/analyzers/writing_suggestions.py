"""
AI writing improvement engine for ClarityAI.

Analyzes text and generates actionable suggestions across multiple categories.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transition words
# ---------------------------------------------------------------------------

_TRANSITION_WORDS: set[str] = {
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "additionally",
    "consequently",
    "nevertheless",
    "meanwhile",
    "similarly",
    "likewise",
    "conversely",
    "alternatively",
    "accordingly",
    "specifically",
    "subsequently",
    "finally",
    "initially",
    "first",
    "second",
    "third",
    "next",
    "then",
    "also",
    "besides",
    "hence",
    "thus",
    "nonetheless",
    "in addition",
    "on the other hand",
    "in contrast",
    "for example",
    "for instance",
    "in conclusion",
    "as a result",
    "in other words",
    "in particular",
    "in summary",
    "to summarize",
    "to illustrate",
    "that is",
    "in fact",
    "above all",
    "after all",
}

# ---------------------------------------------------------------------------
# Redundant phrases
# ---------------------------------------------------------------------------

_REDUNDANT_PHRASES: List[tuple[str, str]] = [
    ("absolutely essential", "essential"),
    ("actual fact", "fact"),
    ("added bonus", "bonus"),
    ("advance planning", "planning"),
    ("basic fundamentals", "fundamentals"),
    ("brief summary", "summary"),
    ("close proximity", "proximity"),
    ("collaborate together", "collaborate"),
    ("completely finished", "finished"),
    ("consensus of opinion", "consensus"),
    ("continue on", "continue"),
    ("each and every", "each"),
    ("end result", "result"),
    ("exactly the same", "the same"),
    ("final outcome", "outcome"),
    ("first and foremost", "first"),
    ("foreign imports", "imports"),
    ("free gift", "gift"),
    ("future plans", "plans"),
    ("general public", "public"),
    ("joint collaboration", "collaboration"),
    ("new innovation", "innovation"),
    ("past history", "history"),
    ("past experience", "experience"),
    ("personal opinion", "opinion"),
    ("plan ahead", "plan"),
    ("positive improvement", "improvement"),
    ("reason why", "reason"),
    ("revert back", "revert"),
    ("still remains", "remains"),
    ("sum total", "total"),
    ("true fact", "fact"),
    ("unexpected surprise", "surprise"),
    ("usual custom", "custom"),
    ("whether or not", "whether"),
]

# ---------------------------------------------------------------------------
# Jargon / buzzwords
# ---------------------------------------------------------------------------

_JARGON_WORDS: set[str] = {
    "synergy",
    "leverage",
    "paradigm",
    "holistic",
    "ecosystem",
    "scalable",
    "disruptive",
    "innovative",
    "best-in-class",
    "world-class",
    "cutting-edge",
    "bleeding-edge",
    "mission-critical",
    "value-added",
    "core-competency",
    "stakeholder",
    "bandwidth",
    "granular",
    "deliverables",
    "actionable",
    "incentivize",
    "ideate",
    "operationalize",
    "monetize",
    "optimize",
    "streamline",
    "empower",
    "facilitate",
    "utilize",
    "robust",
    "thought-leader",
    "game-changer",
    "move-the-needle",
    "low-hanging-fruit",
    "circle-back",
    "deep-dive",
    "blue-sky",
    "boil-the-ocean",
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
        logger.warning("spaCy not installed — writing suggestions will use regex-only mode")
        return None


class WritingSuggestionEngine:
    """Generates actionable writing improvement suggestions."""

    def __init__(self) -> None:
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = _load_spacy()
        return self._nlp

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text and return categorized suggestions with an overall score."""
        suggestions: List[Dict[str, Any]] = []
        sentences = self._split_sentences(text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        suggestions.extend(self._check_long_paragraphs(paragraphs, text))
        suggestions.extend(self._check_monotonous_sentence_starts(sentences, text))
        suggestions.extend(self._check_transition_words(sentences, text))
        suggestions.extend(self._check_passive_voice_clusters(sentences, text))
        suggestions.extend(self._check_jargon(text))
        suggestions.extend(self._check_redundant_phrases(text))
        suggestions.extend(self._check_sentence_variety(sentences))
        suggestions.extend(self._check_paragraph_structure(paragraphs, text))
        suggestions.extend(self._check_vague_language(text))

        # Compute overall writing score
        critical_count = sum(1 for s in suggestions if s["severity"] == "critical")
        warning_count = sum(1 for s in suggestions if s["severity"] == "warning")
        info_count = sum(1 for s in suggestions if s["severity"] == "info")

        score = max(0, 100 - critical_count * 10 - warning_count * 5 - info_count * 2)

        # Category breakdown
        categories: Dict[str, int] = {}
        for s in suggestions:
            cat = s["category"]
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "overall_writing_score": score,
            "suggestion_count": len(suggestions),
            "suggestions": suggestions,
            "category_breakdown": categories,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _check_long_paragraphs(self, paragraphs: List[str], full_text: str) -> List[Dict[str, Any]]:
        """Flag paragraphs longer than 150 words."""
        suggestions = []
        for para in paragraphs:
            word_count = len(para.split())
            if word_count > 150:
                pos = full_text.find(para[:50])
                suggestions.append(
                    {
                        "category": "structure",
                        "severity": "warning",
                        "message": f"Long paragraph ({word_count} words). Consider breaking it into smaller paragraphs for better readability.",
                        "original_text": para[:100] + "..." if len(para) > 100 else para,
                        "suggested_fix": "Split this paragraph at natural topic boundaries.",
                        "position": (
                            {"start": max(0, pos), "end": max(0, pos) + len(para)}
                            if pos >= 0
                            else None
                        ),
                    }
                )
        return suggestions

    def _check_monotonous_sentence_starts(
        self, sentences: List[str], full_text: str
    ) -> List[Dict[str, Any]]:
        """Flag consecutive sentences starting with the same word."""
        suggestions = []
        if len(sentences) < 3:
            return suggestions

        for i in range(len(sentences) - 2):
            starts = []
            for j in range(i, min(i + 3, len(sentences))):
                first_word = sentences[j].split()[0].lower() if sentences[j].split() else ""
                starts.append(first_word)

            if len(starts) == 3 and starts[0] == starts[1] == starts[2] and starts[0]:
                pos = full_text.find(sentences[i][:30])
                suggestions.append(
                    {
                        "category": "engagement",
                        "severity": "warning",
                        "message": f"Three consecutive sentences start with '{starts[0].capitalize()}'. Vary your sentence openings for better flow.",
                        "original_text": f"{sentences[i][:50]}... | {sentences[i+1][:50]}... | {sentences[i+2][:50]}...",
                        "suggested_fix": "Start one or more sentences with a different word, transition phrase, or restructure the sentence.",
                        "position": {"start": max(0, pos)} if pos >= 0 else None,
                    }
                )
        return suggestions

    def _check_transition_words(self, sentences: List[str], full_text: str) -> List[Dict[str, Any]]:
        """Flag lack of transition words between paragraphs/sentences."""
        suggestions = []
        if len(sentences) < 5:
            return suggestions

        text_lower = full_text.lower()
        transition_count = sum(
            1 for tw in _TRANSITION_WORDS if f" {tw}" in text_lower or text_lower.startswith(tw)
        )
        ratio = transition_count / len(sentences)

        if ratio < 0.1 and len(sentences) > 5:
            suggestions.append(
                {
                    "category": "structure",
                    "severity": "info",
                    "message": f"Low use of transition words ({transition_count} found in {len(sentences)} sentences). Transitions improve flow and coherence.",
                    "original_text": None,
                    "suggested_fix": "Add transitions like 'However', 'Moreover', 'In addition', 'For example' between ideas.",
                    "position": None,
                }
            )
        return suggestions

    def _check_passive_voice_clusters(
        self, sentences: List[str], full_text: str
    ) -> List[Dict[str, Any]]:
        """Flag clusters of consecutive passive voice sentences."""
        suggestions = []
        nlp = self.nlp
        if nlp is None:
            return suggestions

        passive_flags = []
        for sent in sentences:
            doc = nlp(sent)
            is_passive = any(token.dep_ in ("nsubjpass", "auxpass") for token in doc)
            passive_flags.append(is_passive)

        # Find clusters of 3+ consecutive passive sentences
        streak = 0
        streak_start = 0
        for i, is_passive in enumerate(passive_flags):
            if is_passive:
                if streak == 0:
                    streak_start = i
                streak += 1
            else:
                if streak >= 3:
                    pos = full_text.find(sentences[streak_start][:30])
                    suggestions.append(
                        {
                            "category": "clarity",
                            "severity": "warning",
                            "message": f"Cluster of {streak} consecutive passive voice sentences starting at sentence {streak_start + 1}.",
                            "original_text": sentences[streak_start][:80] + "...",
                            "suggested_fix": "Rewrite some sentences in active voice for more direct, engaging writing.",
                            "position": {"start": max(0, pos)} if pos >= 0 else None,
                        }
                    )
                streak = 0

        # Check trailing streak
        if streak >= 3:
            pos = full_text.find(sentences[streak_start][:30])
            suggestions.append(
                {
                    "category": "clarity",
                    "severity": "warning",
                    "message": f"Cluster of {streak} consecutive passive voice sentences near the end.",
                    "original_text": sentences[streak_start][:80] + "...",
                    "suggested_fix": "Rewrite some sentences in active voice.",
                    "position": {"start": max(0, pos)} if pos >= 0 else None,
                }
            )

        return suggestions

    def _check_jargon(self, text: str) -> List[Dict[str, Any]]:
        """Flag jargon and buzzword overuse."""
        suggestions = []
        text_lower = text.lower()
        words = re.findall(r"[a-z]+(?:-[a-z]+)*", text_lower)
        jargon_found = [w for w in words if w in _JARGON_WORDS]

        if len(jargon_found) > 3:
            unique_jargon = list(set(jargon_found))[:8]
            suggestions.append(
                {
                    "category": "vocabulary",
                    "severity": "warning",
                    "message": f"Jargon overuse: {len(jargon_found)} buzzwords detected ({', '.join(unique_jargon)}).",
                    "original_text": None,
                    "suggested_fix": "Replace jargon with plain, specific language your audience will understand.",
                    "position": None,
                }
            )
        elif jargon_found:
            for jw in set(jargon_found):
                idx = text_lower.find(jw)
                suggestions.append(
                    {
                        "category": "vocabulary",
                        "severity": "info",
                        "message": f"Buzzword detected: '{jw}'",
                        "original_text": jw,
                        "suggested_fix": "Consider using a more specific, plain-language alternative.",
                        "position": {"start": idx, "end": idx + len(jw)} if idx >= 0 else None,
                    }
                )
        return suggestions

    def _check_redundant_phrases(self, text: str) -> List[Dict[str, Any]]:
        """Flag redundant phrases."""
        suggestions = []
        text_lower = text.lower()
        for redundant, concise in _REDUNDANT_PHRASES:
            idx = text_lower.find(redundant)
            if idx >= 0:
                suggestions.append(
                    {
                        "category": "conciseness",
                        "severity": "info",
                        "message": f"Redundant phrase: '{redundant}'",
                        "original_text": redundant,
                        "suggested_fix": f"Replace with '{concise}'.",
                        "position": {"start": idx, "end": idx + len(redundant)},
                    }
                )
        return suggestions

    def _check_sentence_variety(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """Flag lack of sentence length variety."""
        suggestions = []
        if len(sentences) < 5:
            return suggestions

        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        # Standard deviation
        variance = sum((length - avg_len) ** 2 for length in lengths) / len(lengths)
        std_dev = variance**0.5

        if std_dev < 3 and avg_len > 5:
            suggestions.append(
                {
                    "category": "engagement",
                    "severity": "info",
                    "message": f"Sentences have similar lengths (avg {avg_len:.0f} words, std dev {std_dev:.1f}). Varying sentence length improves rhythm.",
                    "original_text": None,
                    "suggested_fix": "Mix short punchy sentences with longer descriptive ones.",
                    "position": None,
                }
            )
        return suggestions

    def _check_paragraph_structure(
        self, paragraphs: List[str], full_text: str
    ) -> List[Dict[str, Any]]:
        """Flag single-sentence paragraphs in sequence or no paragraph breaks."""
        suggestions = []

        if len(paragraphs) == 1 and len(full_text.split()) > 200:
            suggestions.append(
                {
                    "category": "structure",
                    "severity": "warning",
                    "message": "No paragraph breaks detected in a long text. Break the text into paragraphs.",
                    "original_text": None,
                    "suggested_fix": "Add paragraph breaks every 3-5 sentences or when the topic shifts.",
                    "position": None,
                }
            )

        # Consecutive single-sentence paragraphs
        single_streak = 0
        for para in paragraphs:
            sent_count = len(re.split(r"(?<=[.!?])\s+", para.strip()))
            if sent_count <= 1:
                single_streak += 1
            else:
                if single_streak >= 4:
                    suggestions.append(
                        {
                            "category": "structure",
                            "severity": "info",
                            "message": f"{single_streak} consecutive single-sentence paragraphs detected. Consider combining related ideas.",
                            "original_text": None,
                            "suggested_fix": "Group related single sentences into cohesive paragraphs.",
                            "position": None,
                        }
                    )
                single_streak = 0

        return suggestions

    def _check_vague_language(self, text: str) -> List[Dict[str, Any]]:
        """Flag vague or imprecise language."""
        suggestions = []
        vague_words = {
            "things": "Specify what 'things' refers to.",
            "stuff": "Replace 'stuff' with a specific noun.",
            "very": "Use a stronger adjective instead of 'very + adjective'.",
            "really": "Consider removing 'really' or using a stronger word.",
            "quite": "Be more precise than 'quite'.",
            "basically": "Consider removing 'basically' — it weakens your statement.",
            "actually": "Consider removing 'actually' unless correcting a misconception.",
            "literally": "Use 'literally' only for literal truth, not emphasis.",
            "a lot": "Quantify instead of saying 'a lot'.",
        }

        text_lower = text.lower()
        words = re.findall(r"[a-z]+", text_lower)
        word_freq = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1

        for vague, fix in vague_words.items():
            vague_parts = vague.split()
            if len(vague_parts) == 1:
                count = word_freq.get(vague, 0)
            else:
                count = text_lower.count(vague)

            if count >= 3:
                suggestions.append(
                    {
                        "category": "clarity",
                        "severity": "info",
                        "message": f"Vague word '{vague}' used {count} times.",
                        "original_text": vague,
                        "suggested_fix": fix,
                        "position": None,
                    }
                )
        return suggestions
