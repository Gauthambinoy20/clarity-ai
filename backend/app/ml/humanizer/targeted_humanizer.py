"""
Targeted / surgical humanizer for ClarityAI.

Instead of rewriting the entire text, this humanizer:
1. Uses the SentenceLevelDetector to identify which sentences are AI-generated.
2. Rewrites ONLY those sentences using the lexical + structural humanizers.
3. Preserves human-written sentences untouched.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Threshold: sentences with AI probability above this get rewritten
AI_REWRITE_THRESHOLD = 0.65


@dataclass
class TargetedHumanizationResult:
    original_text: str
    humanized_text: str
    sentences_modified: int
    sentences_preserved: int
    modifications: List[Dict[str, Any]]


class TargetedHumanizer:
    """
    Surgically humanizes only AI-detected sentences while leaving
    human-written content untouched.
    """

    def __init__(
        self,
        ai_threshold: float = AI_REWRITE_THRESHOLD,
        seed: int | None = None,
    ) -> None:
        self.ai_threshold = ai_threshold
        self._seed = seed
        self._detector = None
        self._lexical = None
        self._structural = None

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------

    def _get_detector(self):
        if self._detector is None:
            from app.ml.detectors.sentence_level import SentenceLevelDetector

            self._detector = SentenceLevelDetector()
        return self._detector

    def _get_lexical(self):
        if self._lexical is None:
            from app.ml.humanizer.lexical_humanizer import LexicalHumanizer

            self._lexical = LexicalHumanizer(seed=self._seed)
        return self._lexical

    def _get_structural(self):
        if self._structural is None:
            from app.ml.humanizer.structural_humanizer import StructuralHumanizer

            self._structural = StructuralHumanizer(seed=self._seed)
        return self._structural

    # ------------------------------------------------------------------
    # Sentence splitting (mirrors SentenceLevelDetector)
    # ------------------------------------------------------------------

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        """Split text into sentences, preserving those >10 chars."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    # ------------------------------------------------------------------
    # Humanize a single sentence
    # ------------------------------------------------------------------

    def _humanize_sentence(self, sentence: str, style: str = "academic") -> str:
        """Apply lexical + structural humanization to a single sentence."""
        lexical = self._get_lexical()
        structural = self._get_structural()

        # Step 1: Lexical replacements
        rewritten = lexical.humanize(sentence)

        # Step 2: Structural changes (applied to single sentence)
        # We pass the single sentence to structural humanizer
        # and extract the result (structural may add paragraph breaks, so we
        # collapse them back to a single sentence block)
        rewritten = structural.humanize(rewritten, style=style)

        # Collapse any paragraph breaks the structural humanizer introduced
        rewritten = re.sub(r"\n\s*\n", " ", rewritten).strip()

        return rewritten

    # ------------------------------------------------------------------
    # Reconstruct text preserving original structure
    # ------------------------------------------------------------------

    @staticmethod
    def _reconstruct_text(
        original_text: str,
        original_sentences: List[str],
        new_sentences: List[str],
    ) -> str:
        """
        Rebuild the full text by replacing each original sentence with
        its (possibly rewritten) counterpart, preserving surrounding
        whitespace and paragraph structure.
        """
        result = original_text
        for orig, new in zip(original_sentences, new_sentences):
            if orig != new:
                # Replace first occurrence to avoid duplicates
                result = result.replace(orig, new, 1)
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def humanize(
        self,
        text: str,
        style: str = "academic",
    ) -> TargetedHumanizationResult:
        """
        Analyze the text sentence-by-sentence, then rewrite only
        AI-flagged sentences.

        Parameters
        ----------
        text  : input text
        style : writing style hint for structural humanizer

        Returns
        -------
        TargetedHumanizationResult
        """
        if not text or not text.strip():
            return TargetedHumanizationResult(
                original_text=text,
                humanized_text=text,
                sentences_modified=0,
                sentences_preserved=0,
                modifications=[],
            )

        # Step 1: Run sentence-level AI detection
        detector = self._get_detector()
        detection_result = await detector.analyze(text)

        # If detection failed or returned an error, fall back to no changes
        if "error" in detection_result or "per_sentence" not in detection_result:
            logger.warning(
                "Sentence-level detection unavailable: %s. Returning text unchanged.",
                detection_result.get("error", "unknown"),
            )
            sentences = self._sentence_split(text)
            return TargetedHumanizationResult(
                original_text=text,
                humanized_text=text,
                sentences_modified=0,
                sentences_preserved=len(sentences),
                modifications=[],
            )

        per_sentence = detection_result["per_sentence"]

        # Step 2: Determine which sentences to rewrite
        original_sentences = self._sentence_split(text)
        new_sentences: List[str] = []
        modifications: List[Dict[str, Any]] = []
        modified_count = 0
        preserved_count = 0

        for i, sent in enumerate(original_sentences):
            # Find the corresponding detection result
            sent_result = None
            if i < len(per_sentence):
                sent_result = per_sentence[i]

            ai_prob = sent_result["ai_probability"] if sent_result else 0.0

            if ai_prob >= self.ai_threshold:
                # This sentence is flagged as AI -- rewrite it
                rewritten = self._humanize_sentence(sent, style=style)
                new_sentences.append(rewritten)
                modified_count += 1
                modifications.append(
                    {
                        "sentence_index": i,
                        "original": sent[:300],
                        "rewritten": rewritten[:300],
                        "ai_probability": round(ai_prob, 4),
                        "action": "rewritten",
                    }
                )
            else:
                # Human or uncertain -- preserve as-is
                new_sentences.append(sent)
                preserved_count += 1

        # Step 3: Reconstruct full text
        humanized_text = self._reconstruct_text(text, original_sentences, new_sentences)

        return TargetedHumanizationResult(
            original_text=text,
            humanized_text=humanized_text,
            sentences_modified=modified_count,
            sentences_preserved=preserved_count,
            modifications=modifications,
        )
