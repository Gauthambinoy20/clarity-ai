"""
Rewrite Detector -- Detects AI text that has been paraphrased/humanized to evade detection.

Identifies "over-humanization" signals, residual AI patterns that survive
paraphrasing, and measures a naturalness score to catch the uncanny valley
of rewritten AI content.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from app.ml.detectors.base import BaseDetector

logger = logging.getLogger(__name__)

# ── Wordlists for heuristic checks ──────────────────────────────────────

_FORCED_CONTRACTIONS = {
    "it's",
    "don't",
    "doesn't",
    "won't",
    "can't",
    "couldn't",
    "wouldn't",
    "shouldn't",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "hadn't",
    "hasn't",
    "haven't",
    "didn't",
    "they're",
    "we're",
    "you're",
    "i'm",
    "he's",
    "she's",
    "that's",
    "there's",
    "here's",
    "who's",
    "what's",
    "let's",
}

_AI_TRANSITION_WORDS = {
    "furthermore",
    "moreover",
    "additionally",
    "consequently",
    "nevertheless",
    "nonetheless",
    "henceforth",
    "subsequently",
    "in conclusion",
    "in summary",
    "to summarize",
    "it is worth noting",
    "it should be noted",
    "it is important to note",
    "in this regard",
    "in light of",
    "with respect to",
    "in terms of",
    "on the other hand",
    "as a result",
    "in addition",
    "for instance",
    "for example",
    "in particular",
    "specifically",
    "notably",
    "significantly",
    "ultimately",
    "fundamentally",
    "essentially",
    "interestingly",
}

_AWKWARD_SYNONYMS = {
    "utilize": "use",
    "commence": "start",
    "terminate": "end",
    "facilitate": "help",
    "endeavor": "try",
    "ascertain": "find out",
    "elucidate": "explain",
    "ameliorate": "improve",
    "paradigm": "model",
    "synergy": "teamwork",
    "leverage": "use",
    "optimize": "improve",
    "implement": "do",
    "conceptualize": "think of",
    "incentivize": "encourage",
    "problematic": "bad",
    "methodology": "method",
    "aforementioned": "mentioned",
    "heretofore": "before",
    "notwithstanding": "despite",
    "pertaining": "about",
    "vis-a-vis": "about",
    "plethora": "many",
    "myriad": "many",
}

_TOPIC_STARTERS = {
    "one",
    "another",
    "first",
    "second",
    "third",
    "finally",
    "the",
    "this",
    "these",
    "in",
    "additionally",
    "moreover",
    "furthermore",
    "however",
    "while",
    "although",
    "when",
    "it",
}


class RewriteDetector(BaseDetector):
    """Detect AI text that has been paraphrased or humanized to evade detection."""

    # ── Sentence helpers ─────────────────────────────────────────────────

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    @staticmethod
    def _paragraph_split(text: str) -> List[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()] if text.strip() else []
        return paragraphs

    @staticmethod
    def _word_tokenize(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())

    # ── Signal 1: Over-humanization detection ────────────────────────────

    def _detect_over_humanization(self, text: str, sentences: List[str]) -> Dict[str, Any]:
        """
        Detect signs that text was deliberately altered to appear human:
        - Unnaturally perfect sentence length variation
        - Forced/excessive contractions
        - Awkward synonym substitutions
        """
        scores: List[float] = []

        # (a) Sentence length variation: too-perfect variation is suspicious
        sent_lengths = [len(s.split()) for s in sentences]
        if len(sent_lengths) >= 4:
            # Perfectly alternating lengths (short-long-short) is suspicious
            # Natural text has clustered lengths with occasional outliers
            # CoV of diffs near 0.3-0.5 is suspicious (too controlled)
            mean_len = sum(sent_lengths) / len(sent_lengths) if sent_lengths else 1
            cov = (
                (sum((length - mean_len) ** 2 for length in sent_lengths) / len(sent_lengths))
                ** 0.5
                / mean_len
                if mean_len > 0
                else 0
            )
            # Natural CoV is usually > 0.5 or < 0.2. The 0.25-0.45 range is "engineered"
            if 0.2 <= cov <= 0.5:
                variation_score = 1.0 - abs(cov - 0.35) / 0.15
            else:
                variation_score = 0.2
            variation_score = self._clamp(variation_score)
            scores.append(variation_score)
        else:
            variation_score = 0.3
            scores.append(variation_score)

        # (b) Forced contractions: high contraction density is suspicious
        words = self._word_tokenize(text)
        total_words = len(words) or 1
        text_lower = text.lower()
        contraction_count = sum(1 for c in _FORCED_CONTRACTIONS if c in text_lower)
        contraction_density = contraction_count / (total_words / 100)
        # Natural English has ~2-5 contractions per 100 words
        # Over-humanized text tends to have > 6
        if contraction_density > 6:
            contraction_score = min(1.0, (contraction_density - 6) / 4)
        elif contraction_density > 4:
            contraction_score = 0.3
        else:
            contraction_score = 0.1
        scores.append(contraction_score)

        # (c) Awkward synonym usage
        awkward_count = 0
        for word in words:
            if word in _AWKWARD_SYNONYMS:
                awkward_count += 1
        synonym_density = awkward_count / (total_words / 100)
        synonym_score = self._clamp(synonym_density / 3.0)
        scores.append(synonym_score)

        combined = variation_score * 0.4 + contraction_score * 0.3 + synonym_score * 0.3

        return {
            "over_humanization_score": round(combined, 4),
            "sentence_variation_score": round(variation_score, 4),
            "forced_contraction_score": round(contraction_score, 4),
            "awkward_synonym_score": round(synonym_score, 4),
            "contraction_density": round(contraction_density, 2),
            "awkward_synonyms_found": awkward_count,
            "_scores": scores,
        }

    # ── Signal 2: Residual AI patterns ───────────────────────────────────

    def _detect_residual_ai_patterns(
        self, text: str, sentences: List[str], paragraphs: List[str]
    ) -> Dict[str, Any]:
        """
        Detect AI patterns that survive paraphrasing:
        - Consistent paragraph structure
        - Topic sentence pattern (each paragraph starts with a topic sentence)
        - Lack of genuine tangents
        """
        scores: List[float] = []

        # (a) Paragraph structure consistency
        para_sent_counts = [len(self._sentence_split(p)) for p in paragraphs]
        if len(para_sent_counts) >= 3:
            mean_count = sum(para_sent_counts) / len(para_sent_counts)
            std_count = (
                sum((c - mean_count) ** 2 for c in para_sent_counts) / len(para_sent_counts)
            ) ** 0.5
            cov_para = std_count / mean_count if mean_count > 0 else 0
            # Very uniform paragraph sizes = AI pattern
            structure_score = self._clamp(1.0 - cov_para * 2)
            scores.append(structure_score)
        else:
            structure_score = 0.3
            scores.append(structure_score)

        # (b) Topic sentence pattern: check if first sentence of each paragraph
        # starts with a common topic-introducing word
        topic_pattern_count = 0
        if paragraphs:
            for p in paragraphs:
                first_sent = self._sentence_split(p)
                if first_sent:
                    first_word = (
                        first_sent[0].split()[0].lower().rstrip(".,;:")
                        if first_sent[0].split()
                        else ""
                    )
                    if first_word in _TOPIC_STARTERS:
                        topic_pattern_count += 1
            topic_ratio = topic_pattern_count / len(paragraphs)
            # Natural text: ~40-60% start with common starters
            # AI text: >75%
            topic_score = self._clamp((topic_ratio - 0.5) / 0.4) if topic_ratio > 0.5 else 0.1
            scores.append(topic_score)
        else:
            topic_score = 0.3
            scores.append(topic_score)

        # (c) Lack of tangents: AI text stays rigidly on-topic
        # Proxy: count unique semantic domains via simple vocabulary clustering
        text_lower = text.lower()
        transition_count = sum(1 for t in _AI_TRANSITION_WORDS if t in text_lower)
        transition_density = transition_count / (len(sentences) or 1)
        # > 0.5 transitions per sentence is a strong AI signal
        tangent_score = self._clamp(transition_density / 0.8)
        scores.append(tangent_score)

        combined = structure_score * 0.35 + topic_score * 0.35 + tangent_score * 0.3

        return {
            "residual_pattern_score": round(combined, 4),
            "structure_consistency_score": round(structure_score, 4),
            "topic_sentence_score": round(topic_score, 4),
            "transition_density_score": round(tangent_score, 4),
            "transition_count": transition_count,
            "topic_sentence_ratio": round(topic_pattern_count / max(len(paragraphs), 1), 2),
            "_scores": scores,
        }

    # ── Signal 3: Naturalness score (uncanny valley) ─────────────────────

    def _compute_naturalness_score(self, text: str, sentences: List[str]) -> Dict[str, Any]:
        """
        Measure how natural the text sounds. Rewritten AI text has an
        uncanny-valley effect -- it sounds slightly off.

        Checks:
        - Sentence rhythm irregularity
        - Punctuation variety
        - Personal pronoun usage
        - Filler words / hedging language
        """
        scores: List[float] = []
        words = self._word_tokenize(text)
        total_words = len(words) or 1

        # (a) Punctuation variety
        punct_types = set(re.findall(r"[^\w\s]", text))
        # Natural text uses 5+ punctuation types (. , ! ? ; : - " ' ...)
        punct_variety_score = self._clamp(len(punct_types) / 8.0)
        # Low variety = less natural (rewritten text often strips punctuation variety)
        naturalness_from_punct = punct_variety_score
        scores.append(naturalness_from_punct)

        # (b) Personal pronouns (natural text uses more first-person)
        first_person = sum(
            1 for w in words if w in {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours"}
        )
        pronoun_ratio = first_person / total_words
        # Natural human writing: > 2% first-person pronouns
        pronoun_naturalness = self._clamp(pronoun_ratio / 0.03)
        scores.append(pronoun_naturalness)

        # (c) Filler/hedging words (natural text has some hedging)
        fillers = {
            "actually",
            "basically",
            "honestly",
            "literally",
            "probably",
            "maybe",
            "perhaps",
            "sort of",
            "kind of",
            "like",
            "well",
            "anyway",
            "really",
            "pretty",
            "quite",
            "somewhat",
            "guess",
        }
        filler_count = sum(1 for w in words if w in fillers)
        filler_ratio = filler_count / total_words
        filler_naturalness = self._clamp(filler_ratio / 0.02)
        scores.append(filler_naturalness)

        # (d) Sentence start variety
        if len(sentences) >= 3:
            starts = [s.split()[0].lower() if s.split() else "" for s in sentences]
            unique_starts = len(set(starts))
            start_variety = unique_starts / len(starts) if starts else 0
            # Too high (>0.95) or too low (<0.4) is unnatural
            if start_variety > 0.9:
                start_score = 0.3  # Too perfect, likely rewritten
            elif start_variety < 0.4:
                start_score = 0.2  # Too repetitive, likely AI
            else:
                start_score = 0.8  # Natural range
            scores.append(start_score)
        else:
            start_score = 0.5
            scores.append(start_score)

        # Naturalness = average of signals (higher = more natural)
        naturalness = sum(scores) / len(scores) if scores else 0.5
        # Invert: low naturalness = high rewrite probability
        unnaturalness = 1.0 - naturalness

        return {
            "naturalness_score": round(naturalness * 100, 2),
            "unnaturalness_signal": round(unnaturalness, 4),
            "punctuation_variety": round(naturalness_from_punct, 4),
            "pronoun_naturalness": round(pronoun_naturalness, 4),
            "filler_naturalness": round(filler_naturalness, 4),
            "start_variety": round(start_score, 4),
            "_scores": scores,
        }

    # ── Signal 4: Vocabulary sophistication consistency ──────────────────

    def _check_vocabulary_consistency(self, text: str, sentences: List[str]) -> Dict[str, Any]:
        """
        Rewritten text has uneven register -- some sentences use simple words
        while others use complex vocabulary (because the paraphraser
        inconsistently replaces words).
        """
        if len(sentences) < 3:
            return {
                "vocab_consistency_score": 0.3,
                "register_variance": 0.0,
                "_scores": [0.3],
            }

        # Compute average word length per sentence as a proxy for sophistication
        per_sentence_complexity: List[float] = []
        for s in sentences:
            s_words = re.findall(r"[a-zA-Z]+", s.lower())
            if s_words:
                avg_len = sum(len(w) for w in s_words) / len(s_words)
                # Also count "complex" words (>= 3 syllables, approximated by length >= 8)
                complex_ratio = sum(1 for w in s_words if len(w) >= 8) / len(s_words)
                complexity = avg_len * 0.6 + complex_ratio * 10 * 0.4
                per_sentence_complexity.append(complexity)

        if len(per_sentence_complexity) < 3:
            return {
                "vocab_consistency_score": 0.3,
                "register_variance": 0.0,
                "_scores": [0.3],
            }

        mean_c = sum(per_sentence_complexity) / len(per_sentence_complexity)
        variance = sum((c - mean_c) ** 2 for c in per_sentence_complexity) / len(
            per_sentence_complexity
        )
        std_c = variance**0.5
        cov = std_c / mean_c if mean_c > 0 else 0

        # High CoV in complexity = inconsistent register = rewrite signal
        # Natural: CoV < 0.15, Rewritten: CoV > 0.2
        inconsistency_score = self._clamp((cov - 0.1) / 0.2)

        return {
            "vocab_consistency_score": round(inconsistency_score, 4),
            "register_variance": round(cov, 4),
            "mean_complexity": round(mean_c, 4),
            "complexity_std": round(std_c, 4),
            "_scores": [inconsistency_score],
        }

    # ── Main analyze method ──────────────────────────────────────────────

    async def analyze(self, text: str) -> dict:
        signal_name = "rewrite_detection"
        sentences = self._sentence_split(text)
        paragraphs = self._paragraph_split(text)

        if len(sentences) < 3:
            return self._empty_result(signal_name, "need >= 3 sentences for rewrite detection")

        # Run all sub-signals
        over_human = self._detect_over_humanization(text, sentences)
        residual = self._detect_residual_ai_patterns(text, sentences, paragraphs)
        naturalness = self._compute_naturalness_score(text, sentences)
        vocab = self._check_vocabulary_consistency(text, sentences)

        # Aggregate all sub-scores
        all_scores = (
            over_human.pop("_scores", [])
            + residual.pop("_scores", [])
            + naturalness.pop("_scores", [])
            + vocab.pop("_scores", [])
        )

        # Combined AI probability from rewrite signals
        ai_prob = self._clamp(
            0.30 * over_human["over_humanization_score"]
            + 0.25 * residual["residual_pattern_score"]
            + 0.25 * naturalness["unnaturalness_signal"]
            + 0.20 * vocab["vocab_consistency_score"]
        )

        rewrite_confidence = self._compute_confidence(all_scores)
        rewrite_detected = ai_prob >= 0.45

        # Collect residual AI patterns found
        residual_ai_patterns: List[str] = []
        if residual["structure_consistency_score"] > 0.6:
            residual_ai_patterns.append("uniform_paragraph_structure")
        if residual["topic_sentence_score"] > 0.5:
            residual_ai_patterns.append("topic_sentence_pattern")
        if residual["transition_density_score"] > 0.5:
            residual_ai_patterns.append("excessive_transitions")
        if over_human["forced_contraction_score"] > 0.5:
            residual_ai_patterns.append("forced_contractions")
        if over_human["awkward_synonym_score"] > 0.4:
            residual_ai_patterns.append("awkward_synonym_substitutions")
        if vocab["vocab_consistency_score"] > 0.5:
            residual_ai_patterns.append("inconsistent_vocabulary_register")

        return {
            "signal": signal_name,
            "ai_probability": round(ai_prob, 4),
            "confidence": rewrite_confidence,
            "rewrite_detected": rewrite_detected,
            "rewrite_confidence": round(ai_prob, 4),
            "residual_ai_patterns": residual_ai_patterns,
            "naturalness_score": naturalness["naturalness_score"],
            "details": {
                "over_humanization": over_human,
                "residual_patterns": residual,
                "naturalness": naturalness,
                "vocabulary_consistency": vocab,
            },
        }
