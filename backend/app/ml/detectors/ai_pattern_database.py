"""
AI Pattern Database Detector.

A comprehensive database of 100+ AI-generated text patterns categorised by
model family (GPT-4, Claude, Gemini, Llama).  Includes regex patterns for
common AI structures, transition phrases, opening/closing sentence patterns,
and hedging patterns.  Returns pattern density and AI probability.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

from app.ml.detectors.base import BaseDetector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pattern Categories
# ---------------------------------------------------------------------------


@dataclass
class PatternEntry:
    """A single pattern with its regex and metadata."""

    pattern: str
    category: str
    model: str = "generic"
    weight: float = 1.0


# ── AI Signature Phrases by Model ──────────────────────────────────────────

GPT4_PHRASES: List[str] = [
    "delve",
    "tapestry",
    "multifaceted",
    "nuanced",
    "comprehensive",
    "landscape",
    "paradigm",
    "intricate",
    "pivotal",
    "holistic",
    "robust",
    "streamline",
    "leverage",
    "underscores",
    "realm",
    "encompasses",
    "facilitates",
    "navigating",
    "fostering",
    "underpinning",
    "meticulous",
    "commendable",
    "noteworthy",
    "paramount",
    "indispensable",
    "groundbreaking",
    "cutting-edge",
    "game-changer",
    "synergy",
    "ecosystem",
]

CLAUDE_PHRASES: List[str] = [
    "straightforward",
    "certainly",
    "absolutely",
    "happy to help",
    "great question",
    "fascinating",
    "thoughtful",
    "I appreciate",
    "nuance",
    "context",
    "perspective",
    "I'd be glad",
    "I want to be transparent",
    "I should note",
    "it's worth mentioning",
    "that said",
    "with that in mind",
    "to be fair",
    "I think it's important",
    "let me think about",
    "that's a really",
    "I'd push back",
    "I'm not sure I agree",
    "there's a tension",
    "helpfully",
]

GEMINI_PHRASES: List[str] = [
    "comprehensive overview",
    "explore",
    "aspects",
    "key takeaways",
    "in-depth",
    "insights",
    "strategies",
    "optimize",
    "enhance",
    "benefits",
    "considerations",
    "implementation",
    "deep dive",
    "actionable",
    "breakdown",
    "best practices",
    "use cases",
    "step-by-step",
    "pros and cons",
    "quick summary",
    "bottom line",
    "here's the deal",
    "main points",
    "worth highlighting",
    "crucial to understand",
]

LLAMA_PHRASES: List[str] = [
    "sure thing",
    "let's get started",
    "no problem",
    "gotcha",
    "awesome",
    "cool",
    "stuff",
    "basically",
    "pretty much",
    "kind of",
    "gonna",
    "wanna",
    "lemme",
    "tbh",
    "let me break it down",
    "here's the thing",
    "real quick",
    "super important",
    "big deal",
    "that being said",
    "at the end of the day",
    "long story short",
    "just to be clear",
    "I'd say",
    "for what it's worth",
]


# ── Structural Regex Patterns ──────────────────────────────────────────────

STRUCTURAL_PATTERNS: List[PatternEntry] = [
    # Numbered list patterns
    PatternEntry(r"^\s*\d+\.\s+\*\*[^*]+\*\*", "numbered_list", "generic", 1.5),
    PatternEntry(r"^\s*\d+\.\s+[A-Z]", "numbered_list", "generic", 0.8),
    PatternEntry(r"^\s*-\s+\*\*[^*]+\*\*:", "bullet_bold", "generic", 1.2),
    PatternEntry(r"^\s*[-*]\s+[A-Z][a-z]+:", "bullet_pattern", "generic", 1.0),
    # "Let me..." / "Here's..." openers
    PatternEntry(
        r"\blet me\b(?:\s+\w+){1,3}\b(?:explain|clarify|break|walk|help|show|elaborate|outline)\b",
        "ai_opener",
        "generic",
        1.5,
    ),
    PatternEntry(r"\bhere(?:'s| is| are)\b", "ai_opener", "generic", 0.7),
    PatternEntry(
        r"\bhere(?:'s| is) (?:a |an )?(?:quick|brief|comprehensive|detailed)",
        "ai_opener",
        "generic",
        1.3,
    ),
    # Markdown-style formatting in plain text
    PatternEntry(r"\*\*[^*]{3,50}\*\*", "markdown_bold", "generic", 1.0),
    PatternEntry(r"#{1,3}\s+\w+", "markdown_header", "generic", 1.2),
    # Emoji bullet patterns
    PatternEntry(r"^\s*[\U0001F300-\U0001FAFF]\s+", "emoji_bullet", "generic", 1.5),
    # Code block indicators in non-code text
    PatternEntry(r"```\w*\n", "code_block", "generic", 0.8),
]


# ── Transition Phrases (AI overuses these) ─────────────────────────────────

TRANSITION_PATTERNS: List[PatternEntry] = [
    PatternEntry(r"\bfurthermore\b", "transition", "generic", 1.2),
    PatternEntry(r"\bmoreover\b", "transition", "generic", 1.2),
    PatternEntry(r"\bin addition\b", "transition", "generic", 1.0),
    PatternEntry(r"\bit(?:'s| is) worth noting\b", "transition", "generic", 1.5),
    PatternEntry(r"\badditionally\b", "transition", "generic", 1.1),
    PatternEntry(r"\bconsequently\b", "transition", "generic", 1.0),
    PatternEntry(r"\bnevertheless\b", "transition", "generic", 1.1),
    PatternEntry(r"\bnonetheless\b", "transition", "generic", 1.1),
    PatternEntry(r"\bon the other hand\b", "transition", "generic", 0.9),
    PatternEntry(r"\bthat being said\b", "transition", "generic", 1.3),
    PatternEntry(r"\bwith that (?:being )?said\b", "transition", "generic", 1.3),
    PatternEntry(r"\bhaving said that\b", "transition", "generic", 1.2),
    PatternEntry(r"\bit should be noted\b", "transition", "generic", 1.4),
    PatternEntry(r"\bspecifically\b", "transition", "generic", 0.7),
    PatternEntry(r"\bultimately\b", "transition", "generic", 0.8),
    PatternEntry(r"\bby the same token\b", "transition", "generic", 1.3),
    PatternEntry(r"\bin light of (?:this|that|the above)\b", "transition", "generic", 1.4),
    PatternEntry(r"\bequally important\b", "transition", "generic", 1.2),
    PatternEntry(r"\bwith this in mind\b", "transition", "generic", 1.3),
    PatternEntry(r"\bthat said\b", "transition", "generic", 1.0),
]


# ── Opening Sentence Patterns ─────────────────────────────────────────────

OPENING_PATTERNS: List[PatternEntry] = [
    PatternEntry(
        r"^in today(?:'s| s) (?:rapidly )?(?:evolving|changing|digital|modern|fast-paced|interconnected)",
        "opening",
        "generic",
        2.0,
    ),
    PatternEntry(r"^when it comes to\b", "opening", "generic", 1.5),
    PatternEntry(
        r"^one of the most (?:important|significant|common|popular|effective|powerful|challenging)",
        "opening",
        "generic",
        1.8,
    ),
    PatternEntry(r"^in (?:the |an )?(?:era|age|world) of\b", "opening", "generic", 1.8),
    PatternEntry(
        r"^as (?:we|you) (?:navigate|explore|delve|dive|embark)", "opening", "generic", 1.7
    ),
    PatternEntry(
        r"^(?:the|a) (?:concept|idea|notion|question|topic|subject) of\b", "opening", "generic", 1.3
    ),
    PatternEntry(
        r"^have you ever (?:wondered|thought|considered|asked)", "opening", "generic", 1.5
    ),
    PatternEntry(
        r"^in (?:the )?(?:realm|domain|field|world|sphere) of\b", "opening", "generic", 1.8
    ),
    PatternEntry(
        r"^throughout (?:history|the ages|the years|human history)\b", "opening", "generic", 1.5
    ),
    PatternEntry(r"^it(?:'s| is) no (?:secret|surprise|exaggeration)\b", "opening", "generic", 1.6),
    PatternEntry(
        r"^(?:understanding|exploring|examining|navigating) (?:the )?\w+\b",
        "opening",
        "generic",
        1.2,
    ),
    PatternEntry(
        r"^the (?:rise|emergence|evolution|importance|significance|impact) of\b",
        "opening",
        "generic",
        1.6,
    ),
]


# ── Closing Sentence Patterns ─────────────────────────────────────────────

CLOSING_PATTERNS: List[PatternEntry] = [
    PatternEntry(r"\bin conclusion\b", "closing", "generic", 1.8),
    PatternEntry(r"\bto summarize\b", "closing", "generic", 1.5),
    PatternEntry(r"\boverall\b,?\s", "closing", "generic", 0.8),
    PatternEntry(r"\bin summary\b", "closing", "generic", 1.5),
    PatternEntry(r"\bto (?:sum|wrap) (?:it )?up\b", "closing", "generic", 1.5),
    PatternEntry(r"\bin (?:a )?nutshell\b", "closing", "generic", 1.3),
    PatternEntry(r"\ball (?:things|in all)\b", "closing", "generic", 0.9),
    PatternEntry(
        r"\bby (?:embracing|adopting|leveraging|understanding|implementing)\b",
        "closing",
        "generic",
        1.4,
    ),
    PatternEntry(r"\bthe (?:key|bottom) line (?:is|here)\b", "closing", "generic", 1.3),
    PatternEntry(r"\bmoving forward\b", "closing", "generic", 1.2),
    PatternEntry(r"\bas we (?:move|look|go) forward\b", "closing", "generic", 1.5),
    PatternEntry(r"\bit(?:'s| is) clear that\b", "closing", "generic", 1.2),
]


# ── Hedging Patterns ──────────────────────────────────────────────────────

HEDGING_PATTERNS: List[PatternEntry] = [
    PatternEntry(r"\bit(?:'s| is) important to note that\b", "hedging", "generic", 1.8),
    PatternEntry(r"\bit should be noted (?:that )?\b", "hedging", "generic", 1.6),
    PatternEntry(
        r"\bit(?:'s| is) worth (?:noting|mentioning|pointing out)\b", "hedging", "generic", 1.7
    ),
    PatternEntry(
        r"\bwhile (?:it(?:'s| is) )?(?:true|possible|likely) that\b", "hedging", "generic", 1.3
    ),
    PatternEntry(r"\bgenerally speaking\b", "hedging", "generic", 1.2),
    PatternEntry(r"\bthat (?:being )?said\b", "hedging", "generic", 1.0),
    PatternEntry(
        r"\bhowever,? it(?:'s| is) (?:important|crucial|essential|worth)\b",
        "hedging",
        "generic",
        1.5,
    ),
    PatternEntry(
        r"\bthere(?:'s| is) no (?:one-size-fits-all|simple|easy|single)\b",
        "hedging",
        "generic",
        1.6,
    ),
    PatternEntry(
        r"\bit(?:'s| is) (?:also )?important to (?:consider|remember|keep in mind)\b",
        "hedging",
        "generic",
        1.5,
    ),
    PatternEntry(r"\bon (?:the )?(?:one|the other) hand\b", "hedging", "generic", 1.0),
    PatternEntry(r"\bit depends on\b", "hedging", "generic", 0.8),
    PatternEntry(r"\bwith that (?:being )?said\b", "hedging", "generic", 1.2),
    PatternEntry(
        r"\bit(?:'s| is) (?:a )?common (?:misconception|mistake|belief)\b",
        "hedging",
        "generic",
        1.4,
    ),
    PatternEntry(r"\bas (?:always|with (?:anything|everything))\b", "hedging", "generic", 1.0),
]


# ── Compile all patterns into a master list ────────────────────────────────

ALL_PATTERNS: List[PatternEntry] = (
    STRUCTURAL_PATTERNS
    + TRANSITION_PATTERNS
    + OPENING_PATTERNS
    + CLOSING_PATTERNS
    + HEDGING_PATTERNS
)

ALL_PHRASE_DATABASES: Dict[str, List[str]] = {
    "gpt4": GPT4_PHRASES,
    "claude": CLAUDE_PHRASES,
    "gemini": GEMINI_PHRASES,
    "llama": LLAMA_PHRASES,
}

# Pre-compile regexes for performance
_COMPILED_PATTERNS: List[Tuple[re.Pattern, PatternEntry]] = [
    (re.compile(p.pattern, re.IGNORECASE | re.MULTILINE), p) for p in ALL_PATTERNS
]


class AIPatternDatabaseDetector(BaseDetector):
    """
    Scans text against 100+ known AI-generated text patterns.

    Returns pattern density, matched patterns by category, and an
    AI probability score derived from pattern saturation.
    """

    async def analyze(self, text: str) -> dict:
        signal = "ai_pattern_database"
        words = text.split()
        word_count = len(words)

        if word_count < 15:
            return self._empty_result(signal, "text too short (< 15 words)")

        lower = text.lower()
        # ── Phase 1: Phrase matching (per-model) ──────────────────────
        phrase_hits: Dict[str, List[str]] = {m: [] for m in ALL_PHRASE_DATABASES}
        for model_name, phrases in ALL_PHRASE_DATABASES.items():
            for phrase in phrases:
                if phrase.lower() in lower:
                    phrase_hits[model_name].append(phrase)

        total_phrase_hits = sum(len(v) for v in phrase_hits.values())

        # ── Phase 2: Regex pattern matching ───────────────────────────
        pattern_matches: Dict[str, List[Dict]] = {
            "numbered_list": [],
            "bullet_bold": [],
            "bullet_pattern": [],
            "ai_opener": [],
            "markdown_bold": [],
            "markdown_header": [],
            "emoji_bullet": [],
            "code_block": [],
            "transition": [],
            "opening": [],
            "closing": [],
            "hedging": [],
        }

        weighted_hit_count = 0.0

        for compiled, entry in _COMPILED_PATTERNS:
            matches = compiled.findall(text)
            if matches:
                cat = entry.category
                if cat not in pattern_matches:
                    pattern_matches[cat] = []
                for m in matches:
                    match_text = m if isinstance(m, str) else m[0] if m else ""
                    pattern_matches[cat].append(
                        {
                            "matched": match_text.strip()[:80],
                            "pattern": entry.pattern,
                            "model": entry.model,
                        }
                    )
                weighted_hit_count += len(matches) * entry.weight

        # ── Phase 3: Compute density metrics ──────────────────────────
        total_regex_hits = sum(len(v) for v in pattern_matches.values())
        total_hits = total_phrase_hits + total_regex_hits
        pattern_density = total_hits / max(word_count, 1)

        # Sentence count (rough)
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = max(len(sentences), 1)

        # Per-category density
        category_counts: Dict[str, int] = {}
        for cat, entries in pattern_matches.items():
            if entries:
                category_counts[cat] = len(entries)

        # ── Phase 4: Score computation ────────────────────────────────
        # Normalize weighted hits by text length
        density_score = self._clamp(weighted_hit_count / max(word_count / 50, 1))

        # Phrase density score
        phrase_density_score = self._clamp(total_phrase_hits / max(sentence_count, 1) * 2.0)

        # Category spread bonus: more categories hit = more AI-like
        unique_categories = len([c for c, v in pattern_matches.items() if v])
        spread_score = self._clamp(unique_categories / 8.0)

        # Opening/closing pattern bonus
        has_opening = len(pattern_matches.get("opening", [])) > 0
        has_closing = len(pattern_matches.get("closing", [])) > 0
        structural_bonus = 0.0
        if has_opening:
            structural_bonus += 0.1
        if has_closing:
            structural_bonus += 0.1
        if has_opening and has_closing:
            structural_bonus += 0.05

        # Combine scores
        raw_score = (
            density_score * 0.35
            + phrase_density_score * 0.25
            + spread_score * 0.20
            + structural_bonus
            + min(total_regex_hits * 0.01, 0.10)
        )

        ai_probability = self._clamp(self._sigmoid((raw_score - 0.25) / 0.15))

        # ── Phase 5: Determine most likely model ──────────────────────
        model_scores: Dict[str, float] = {}
        for model_name, hits in phrase_hits.items():
            model_scores[model_name] = len(hits)

        total_model = sum(model_scores.values())
        if total_model > 0:
            model_probs = {k: v / total_model for k, v in model_scores.items()}
        else:
            model_probs = {k: 0.25 for k in model_scores}

        most_likely_model = max(model_probs, key=model_probs.get)  # type: ignore[arg-type]

        # Confidence
        confidence = self._compute_confidence([density_score, phrase_density_score, spread_score])

        # Build category summary for response
        pattern_categories: Dict[str, Dict] = {}
        for cat, entries in pattern_matches.items():
            if entries:
                pattern_categories[cat] = {
                    "count": len(entries),
                    "examples": [e["matched"] for e in entries[:5]],
                }

        return {
            "signal": signal,
            "ai_probability": round(ai_probability, 4),
            "confidence": confidence,
            "patterns_found": total_hits,
            "pattern_density": round(pattern_density, 6),
            "pattern_categories": pattern_categories,
            "phrase_matches": {model: hits for model, hits in phrase_hits.items() if hits},
            "most_likely_model": most_likely_model,
            "model_probabilities": {k: round(v, 4) for k, v in model_probs.items()},
            "details": {
                "total_phrase_hits": total_phrase_hits,
                "total_regex_hits": total_regex_hits,
                "density_score": round(density_score, 4),
                "phrase_density_score": round(phrase_density_score, 4),
                "spread_score": round(spread_score, 4),
                "structural_bonus": round(structural_bonus, 4),
                "unique_categories_hit": unique_categories,
                "word_count": word_count,
                "sentence_count": sentence_count,
            },
        }
