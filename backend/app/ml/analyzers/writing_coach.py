"""
AI Writing Coach -- Analyzes text and provides real-time improvement
suggestions to make content sound more human and less AI-generated.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Pattern databases ────────────────────────────────────────────────────

_FORMAL_REPLACEMENTS: List[Tuple[str, str, str]] = [
    # (pattern_to_find, suggestion, category)
    ("furthermore", "also", "transition"),
    ("moreover", "also", "transition"),
    ("additionally", "also", "transition"),
    ("consequently", "so", "transition"),
    ("nevertheless", "still", "transition"),
    ("nonetheless", "even so", "transition"),
    ("subsequently", "then", "transition"),
    ("henceforth", "from now on", "transition"),
    ("in conclusion", "to wrap up", "transition"),
    ("in summary", "overall", "transition"),
    ("it is worth noting", "note that", "wordiness"),
    ("it should be noted", "note that", "wordiness"),
    ("it is important to note", "importantly", "wordiness"),
    ("in light of", "given", "wordiness"),
    ("with respect to", "about", "wordiness"),
    ("in terms of", "for", "wordiness"),
    ("in order to", "to", "wordiness"),
    ("due to the fact that", "because", "wordiness"),
    ("for the purpose of", "to", "wordiness"),
    ("in the event that", "if", "wordiness"),
    ("at this point in time", "now", "wordiness"),
    ("utilize", "use", "vocabulary"),
    ("commence", "start", "vocabulary"),
    ("terminate", "end", "vocabulary"),
    ("facilitate", "help", "vocabulary"),
    ("endeavor", "try", "vocabulary"),
    ("ascertain", "find out", "vocabulary"),
    ("elucidate", "explain", "vocabulary"),
    ("ameliorate", "improve", "vocabulary"),
    ("paradigm", "model", "vocabulary"),
    ("leverage", "use", "vocabulary"),
    ("optimize", "improve", "vocabulary"),
    ("implement", "set up", "vocabulary"),
    ("methodology", "method", "vocabulary"),
    ("plethora", "many", "vocabulary"),
    ("myriad", "many", "vocabulary"),
]

_CONTRACTION_MAP: Dict[str, str] = {
    "it is": "it's",
    "do not": "don't",
    "does not": "doesn't",
    "will not": "won't",
    "can not": "can't",
    "cannot": "can't",
    "could not": "couldn't",
    "would not": "wouldn't",
    "should not": "shouldn't",
    "is not": "isn't",
    "are not": "aren't",
    "was not": "wasn't",
    "were not": "weren't",
    "has not": "hasn't",
    "have not": "haven't",
    "had not": "hadn't",
    "did not": "didn't",
    "they are": "they're",
    "we are": "we're",
    "you are": "you're",
    "I am": "I'm",
    "he is": "he's",
    "she is": "she's",
    "that is": "that's",
    "there is": "there's",
    "here is": "here's",
    "who is": "who's",
    "what is": "what's",
    "let us": "let's",
    "I will": "I'll",
    "you will": "you'll",
    "we will": "we'll",
    "they will": "they'll",
    "I would": "I'd",
    "you would": "you'd",
    "we would": "we'd",
    "they would": "they'd",
    "I have": "I've",
    "you have": "you've",
    "we have": "we've",
    "they have": "they've",
}

_AI_SIGNATURE_PHRASES = [
    "it is important to",
    "it is worth noting",
    "it should be noted",
    "in today's world",
    "in today's society",
    "in the modern era",
    "plays a crucial role",
    "plays a vital role",
    "plays an important role",
    "a wide range of",
    "a variety of",
    "a significant amount of",
    "on the other hand",
    "in this day and age",
    "the fact that",
    "there are many",
    "there are several",
    "there are numerous",
    "delve into",
    "dive into",
    "shed light on",
    "pave the way",
    "at the end of the day",
    "last but not least",
    "all in all",
    "to sum up",
    "in a nutshell",
]


class WritingCoach:
    """Analyze text and provide suggestions to make it sound more human."""

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 3]

    @staticmethod
    def _find_position(text: str, substring: str) -> Optional[int]:
        """Find character position of substring in text (case-insensitive)."""
        idx = text.lower().find(substring.lower())
        return idx if idx >= 0 else None

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text and return writing coach suggestions.

        Returns:
            human_score: 0-100 (higher = more human-sounding)
            suggestions: list of suggestion dicts
            quick_fixes: list of easy fixes
        """
        suggestions: List[Dict[str, Any]] = []
        quick_fixes: List[Dict[str, Any]] = []
        penalty_points = 0.0
        text_lower = text.lower()
        sentences = self._sentence_split(text)
        words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text_lower)
        total_words = len(words) or 1

        # ── Check 1: Formal word replacements ────────────────────────────
        for pattern, replacement, category in _FORMAL_REPLACEMENTS:
            pos = self._find_position(text, pattern)
            if pos is not None:
                impact = "high" if category == "transition" else "medium"
                suggestion = {
                    "category": category,
                    "message": f"Replace '{pattern}' with '{replacement}' for a more natural tone",
                    "original": pattern,
                    "fix": replacement,
                    "impact": impact,
                    "position": pos,
                }
                suggestions.append(suggestion)
                quick_fixes.append(
                    {
                        "original": pattern,
                        "fix": replacement,
                        "position": pos,
                    }
                )
                penalty_points += 2.0 if impact == "high" else 1.0

        # ── Check 2: Contraction suggestions ─────────────────────────────
        for expanded, contracted in _CONTRACTION_MAP.items():
            pos = self._find_position(text, expanded)
            if pos is not None:
                # Make sure it's not already contracted in the actual text
                actual_segment = text[pos : pos + len(expanded)]
                if actual_segment.lower() == expanded.lower():
                    suggestion = {
                        "category": "contraction",
                        "message": f"Consider using a contraction: '{expanded}' -> '{contracted}'",
                        "original": expanded,
                        "fix": contracted,
                        "impact": "low",
                        "position": pos,
                    }
                    suggestions.append(suggestion)
                    quick_fixes.append(
                        {
                            "original": expanded,
                            "fix": contracted,
                            "position": pos,
                        }
                    )
                    penalty_points += 0.5

        # ── Check 3: Sentence length uniformity ──────────────────────────
        if len(sentences) >= 4:
            sent_lengths = [len(s.split()) for s in sentences]
            mean_len = sum(sent_lengths) / len(sent_lengths)
            std_len = (
                sum((length - mean_len) ** 2 for length in sent_lengths) / len(sent_lengths)
            ) ** 0.5
            cov = std_len / mean_len if mean_len > 0 else 0

            if cov < 0.3:
                # Find a long sentence to suggest breaking up
                for i, (s, length) in enumerate(zip(sentences, sent_lengths)):
                    if length > mean_len * 1.2:
                        pos = self._find_position(text, s[:40])
                        suggestions.append(
                            {
                                "category": "sentence_structure",
                                "message": "This paragraph has too uniform sentence lengths. Try varying: break this long sentence or combine short ones.",
                                "original": s[:80] + ("..." if len(s) > 80 else ""),
                                "fix": "Try splitting into shorter sentences or combining nearby short sentences",
                                "impact": "high",
                                "position": pos,
                            }
                        )
                        penalty_points += 3.0
                        break
                else:
                    suggestions.append(
                        {
                            "category": "sentence_structure",
                            "message": "Sentences are very uniform in length. Try varying sentence length for natural flow.",
                            "original": None,
                            "fix": "Mix short punchy sentences with longer descriptive ones",
                            "impact": "high",
                            "position": 0,
                        }
                    )
                    penalty_points += 3.0

        # ── Check 4: Transition word density ─────────────────────────────
        transition_words = [
            "furthermore",
            "moreover",
            "additionally",
            "consequently",
            "nevertheless",
            "nonetheless",
            "subsequently",
            "however",
            "therefore",
            "thus",
            "hence",
            "accordingly",
            "meanwhile",
            "similarly",
            "likewise",
            "conversely",
            "alternatively",
        ]
        transition_count = sum(1 for w in words if w in transition_words)
        transition_density = transition_count / (total_words / 100)
        if transition_density > 2.0:
            suggestions.append(
                {
                    "category": "transition",
                    "message": f"Too many transition words ({transition_count} found). Remove some for natural flow.",
                    "original": None,
                    "fix": "Remove unnecessary transitions. Let ideas flow naturally without signposting every connection.",
                    "impact": "high",
                    "position": 0,
                }
            )
            penalty_points += 3.0

        # ── Check 5: AI signature phrases ────────────────────────────────
        for phrase in _AI_SIGNATURE_PHRASES:
            pos = self._find_position(text, phrase)
            if pos is not None:
                suggestions.append(
                    {
                        "category": "ai_signature",
                        "message": f"'{phrase}' is a common AI-generated phrase. Rephrase or remove it.",
                        "original": phrase,
                        "fix": "Rephrase in your own words or remove entirely",
                        "impact": "high",
                        "position": pos,
                    }
                )
                penalty_points += 2.5

        # ── Check 6: Personal voice ──────────────────────────────────────
        first_person = sum(1 for w in words if w in {"i", "me", "my", "mine", "myself"})
        if first_person == 0 and total_words > 50:
            suggestions.append(
                {
                    "category": "personal_voice",
                    "message": "Add a personal anecdote or opinion to make this sound more authentic.",
                    "original": None,
                    "fix": "Include first-person perspective: share an experience, opinion, or reaction",
                    "impact": "medium",
                    "position": 0,
                }
            )
            penalty_points += 2.0

        # ── Check 7: Paragraph starting words ────────────────────────────
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paragraphs) >= 3:
            starts = []
            for p in paragraphs:
                first_word = p.split()[0].lower().rstrip(".,;:") if p.split() else ""
                starts.append(first_word)
            if len(set(starts)) < len(starts) * 0.6:
                suggestions.append(
                    {
                        "category": "paragraph_structure",
                        "message": "Paragraphs start with repetitive words. Vary your opening words.",
                        "original": None,
                        "fix": "Start paragraphs differently -- use questions, quotes, or jump straight to the point",
                        "impact": "medium",
                        "position": 0,
                    }
                )
                penalty_points += 1.5

        # ── Check 8: Passive voice ───────────────────────────────────────
        passive_patterns = [
            r"\b(?:is|are|was|were|been|being)\s+\w+ed\b",
            r"\b(?:is|are|was|were|been|being)\s+\w+en\b",
        ]
        passive_count = 0
        for pattern in passive_patterns:
            passive_count += len(re.findall(pattern, text_lower))
        passive_ratio = passive_count / max(len(sentences), 1)
        if passive_ratio > 0.3:
            suggestions.append(
                {
                    "category": "voice",
                    "message": f"High passive voice usage ({passive_count} instances). Use active voice more.",
                    "original": None,
                    "fix": "Rewrite passive constructions: 'was done by X' -> 'X did'",
                    "impact": "medium",
                    "position": 0,
                }
            )
            penalty_points += 2.0

        # ── Compute human score ──────────────────────────────────────────
        # Start at 100, deduct penalty points, floor at 0
        raw_score = 100.0 - penalty_points
        human_score = max(0, min(100, round(raw_score)))

        # Sort suggestions by impact (high > medium > low)
        impact_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: impact_order.get(s.get("impact", "low"), 3))

        return {
            "human_score": human_score,
            "suggestions": suggestions,
            "quick_fixes": quick_fixes,
            "total_suggestions": len(suggestions),
            "high_impact_count": sum(1 for s in suggestions if s.get("impact") == "high"),
            "medium_impact_count": sum(1 for s in suggestions if s.get("impact") == "medium"),
            "low_impact_count": sum(1 for s in suggestions if s.get("impact") == "low"),
        }
