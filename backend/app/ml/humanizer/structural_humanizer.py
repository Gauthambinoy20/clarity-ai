"""
Structural humanizer -- applies sentence- and paragraph-level transformations
using spaCy NLP to produce more naturally varied text structure.
"""

import logging
import random
import re
from typing import List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-built phrase banks
# ---------------------------------------------------------------------------
HEDGING_PHRASES = [
    "I think",
    "I believe",
    "It seems like",
    "In my view",
    "From what I can tell",
    "As far as I know",
    "If I had to guess",
    "My sense is",
    "Arguably",
    "Probably",
    "It looks like",
    "I'd say",
]

FRAGMENT_STARTERS = [
    "Especially",
    "Not always, though.",
    "At least in theory.",
    "More or less.",
    "Sometimes.",
    "Worth noting.",
    "Hard to say for sure.",
    "A tricky point.",
    "Big difference.",
    "No surprise there.",
    "Fair enough.",
    "Not quite.",
]

PARENTHETICAL_ASIDES = [
    " (or something like that)",
    " (at least that's how I see it)",
    " (though I could be wrong)",
    " (roughly speaking)",
    " (give or take)",
    " (if that makes sense)",
    " (more or less)",
    " (for what it's worth)",
    " (to put it simply)",
    " (no pun intended)",
]

CONJUNCTION_STARTERS = ["And", "But", "So", "Yet"]

# Styles that should skip informal injections
FORMAL_STYLES = {"academic", "professional", "formal"}


def _load_spacy():
    """Lazy-load spaCy with the small English model."""
    try:
        import spacy

        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Downloading...")
            from spacy.cli import download

            download("en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
        return nlp
    except ImportError:
        logger.error("spaCy is not installed. Structural humanizer will be limited.")
        return None


class StructuralHumanizer:
    """
    Applies structural transformations (sentence splitting/merging, fragments,
    hedging, paragraph variation) to make text read more naturally.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._nlp = None  # lazy loaded
        self._rng = random.Random(seed)

    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = _load_spacy()
        return self._nlp

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def humanize(self, text: str, style: str = "academic") -> str:
        """
        Run structural humanization on *text*.

        Parameters
        ----------
        text  : input text
        style : one of "academic", "casual", "professional", "creative"

        Returns the transformed text.
        """
        if not text or not text.strip():
            return text

        nlp = self.nlp
        if nlp is None:
            logger.warning("spaCy unavailable; returning text with minimal changes.")
            return self._fallback_humanize(text, style)

        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        if not sentences:
            return text

        is_formal = style.lower() in FORMAL_STYLES

        # Step 1: Sentence length variation
        sentences = self._vary_sentence_lengths(sentences)

        # Step 2: Fragment insertion (not for academic/professional)
        if not is_formal:
            sentences = self._insert_fragments(sentences)

        # Step 3: Parenthetical asides (10% chance per sentence)
        sentences = self._inject_parentheticals(sentences, is_formal)

        # Step 4: Hedging phrases (15% chance, non-academic only)
        if not is_formal:
            sentences = self._inject_hedging(sentences)

        # Step 5: Conjunction starters (8% chance)
        sentences = self._inject_conjunction_starters(sentences, is_formal)

        # Reassemble into paragraphs with varied lengths
        result = self._randomize_paragraphs(sentences, style)
        return result

    # ------------------------------------------------------------------
    # Sentence length variation
    # ------------------------------------------------------------------
    def _vary_sentence_lengths(self, sentences: List[str]) -> List[str]:
        result: List[str] = []
        i = 0
        while i < len(sentences):
            sent = sentences[i]
            word_count = len(sent.split())

            # Break long sentences (>30 words)
            if word_count > 30:
                parts = self._break_long_sentence(sent)
                result.extend(parts)
            # Merge short consecutive sentences (<8 words each)
            elif word_count < 8 and i + 1 < len(sentences) and len(sentences[i + 1].split()) < 8:
                merged = self._merge_sentences(sent, sentences[i + 1])
                result.append(merged)
                i += 1  # skip the next since we merged it
            else:
                result.append(sent)
            i += 1
        return result

    def _break_long_sentence(self, sentence: str) -> List[str]:
        """Split a long sentence at a conjunction or punctuation boundary."""
        # Try splitting at common conjunctions
        for conj in [", and ", ", but ", ", so ", "; ", ", which ", ", where "]:
            idx = sentence.find(conj)
            if idx != -1 and idx > 15:
                first = sentence[:idx].strip().rstrip(",")
                second = sentence[idx + len(conj) :].strip()
                # Capitalise the second part
                if second:
                    second = second[0].upper() + second[1:]
                if not first.endswith("."):
                    first += "."
                return [first, second]

        # Try splitting roughly in the middle at a comma
        words = sentence.split()
        mid = len(words) // 2
        # Look for a comma near the middle
        for offset in range(0, min(8, mid)):
            for pos in [mid + offset, mid - offset]:
                if 0 < pos < len(words) and words[pos - 1].endswith(","):
                    first = " ".join(words[:pos]).rstrip(",")
                    second = " ".join(words[pos:])
                    if second:
                        second = second[0].upper() + second[1:]
                    if not first.endswith("."):
                        first += "."
                    return [first, second]

        # Give up -- return as-is
        return [sentence]

    @staticmethod
    def _merge_sentences(s1: str, s2: str) -> str:
        """Merge two short sentences with a joining word."""
        s1 = s1.rstrip(".")
        s2_lower = s2[0].lower() + s2[1:] if s2 else s2
        connectors = [", and ", " -- ", "; "]
        connector = random.choice(connectors)
        return s1 + connector + s2_lower

    # ------------------------------------------------------------------
    # Fragment insertion
    # ------------------------------------------------------------------
    def _insert_fragments(self, sentences: List[str]) -> List[str]:
        """Insert a sentence fragment after ~10% of sentences."""
        result: List[str] = []
        for sent in sentences:
            result.append(sent)
            if self._rng.random() < 0.10:
                fragment = self._rng.choice(FRAGMENT_STARTERS)
                result.append(fragment)
        return result

    # ------------------------------------------------------------------
    # Parenthetical asides
    # ------------------------------------------------------------------
    def _inject_parentheticals(self, sentences: List[str], is_formal: bool) -> List[str]:
        """Add parenthetical asides to ~10% of sentences."""
        if is_formal:
            return sentences

        result: List[str] = []
        for sent in sentences:
            if self._rng.random() < 0.10 and len(sent.split()) > 6:
                aside = self._rng.choice(PARENTHETICAL_ASIDES)
                # Insert before the final punctuation
                if sent and sent[-1] in ".!?":
                    sent = sent[:-1] + aside + sent[-1]
                else:
                    sent = sent + aside
            result.append(sent)
        return result

    # ------------------------------------------------------------------
    # Hedging phrases
    # ------------------------------------------------------------------
    def _inject_hedging(self, sentences: List[str]) -> List[str]:
        """Prepend a hedging phrase to ~15% of declarative sentences."""
        result: List[str] = []
        for sent in sentences:
            if (
                self._rng.random() < 0.15
                and len(sent.split()) > 5
                and not sent.endswith("?")
                and not sent.startswith(tuple(HEDGING_PHRASES))
            ):
                hedge = self._rng.choice(HEDGING_PHRASES)
                # Lower-case the original start
                lowered = sent[0].lower() + sent[1:] if sent else sent
                sent = f"{hedge}, {lowered}"
            result.append(sent)
        return result

    # ------------------------------------------------------------------
    # Conjunction starters
    # ------------------------------------------------------------------
    def _inject_conjunction_starters(self, sentences: List[str], is_formal: bool) -> List[str]:
        """Start ~8% of sentences with 'And', 'But', 'So', etc."""
        result: List[str] = []
        for sent in sentences:
            starts_with_conj = sent.split()[0] in CONJUNCTION_STARTERS if sent.split() else False
            if (
                self._rng.random() < 0.08
                and not is_formal
                and len(sent.split()) > 4
                and not starts_with_conj
            ):
                conj = self._rng.choice(CONJUNCTION_STARTERS)
                lowered = sent[0].lower() + sent[1:] if sent else sent
                sent = f"{conj} {lowered}"
            result.append(sent)
        return result

    # ------------------------------------------------------------------
    # Paragraph randomization
    # ------------------------------------------------------------------
    def _randomize_paragraphs(self, sentences: List[str], style: str) -> str:
        """
        Group sentences into paragraphs with varied lengths.
        Academic / professional → 3-6 sentences per paragraph.
        Casual / creative → 1-4 sentences per paragraph.
        """
        if style.lower() in {"casual", "creative"}:
            min_per_para, max_per_para = 1, 4
        else:
            min_per_para, max_per_para = 3, 6

        paragraphs: List[str] = []
        i = 0
        while i < len(sentences):
            count = self._rng.randint(min_per_para, max_per_para)
            chunk = sentences[i : i + count]
            paragraphs.append(" ".join(chunk))
            i += count

        return "\n\n".join(paragraphs)

    # ------------------------------------------------------------------
    # Fallback if spaCy is unavailable
    # ------------------------------------------------------------------
    def _fallback_humanize(self, text: str, style: str) -> str:
        """Minimal structural changes using regex sentence splitting."""
        # Simple sentence split on '. '
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        is_formal = style.lower() in FORMAL_STYLES

        if not is_formal:
            sentences = self._inject_conjunction_starters(sentences, is_formal)

        return self._randomize_paragraphs(sentences, style)
