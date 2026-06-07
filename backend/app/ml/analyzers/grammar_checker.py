"""
Grammar and style checker for ClarityAI.

Uses regex patterns and spaCy for grammar error detection and style analysis.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cliches (50+)
# ---------------------------------------------------------------------------

_CLICHES: List[str] = [
    "at the end of the day",
    "think outside the box",
    "it is what it is",
    "low-hanging fruit",
    "hit the ground running",
    "back to the drawing board",
    "it goes without saying",
    "a perfect storm",
    "move the needle",
    "at this point in time",
    "in the nick of time",
    "few and far between",
    "the bottom line",
    "cutting edge",
    "paradigm shift",
    "win-win situation",
    "game changer",
    "best of both worlds",
    "on the same page",
    "take it to the next level",
    "push the envelope",
    "raise the bar",
    "circle back",
    "deep dive",
    "run it up the flagpole",
    "boil the ocean",
    "move the goalposts",
    "elephant in the room",
    "tip of the iceberg",
    "burning the midnight oil",
    "actions speak louder than words",
    "add insult to injury",
    "beat around the bush",
    "bite the bullet",
    "break the ice",
    "costs an arm and a leg",
    "every cloud has a silver lining",
    "the ball is in your court",
    "once in a blue moon",
    "piece of cake",
    "time will tell",
    "under the weather",
    "easier said than done",
    "read between the lines",
    "the writing on the wall",
    "time is money",
    "when all is said and done",
    "leave no stone unturned",
    "the whole nine yards",
    "a blessing in disguise",
    "better late than never",
    "crystal clear",
    "all hands on deck",
    "go the extra mile",
]

# ---------------------------------------------------------------------------
# Wordiness patterns: (verbose phrase, concise replacement)
# ---------------------------------------------------------------------------

_WORDINESS: List[Tuple[str, str]] = [
    ("in order to", "to"),
    ("at this point in time", "now"),
    ("in the event that", "if"),
    ("due to the fact that", "because"),
    ("for the purpose of", "to"),
    ("in the process of", "while"),
    ("it is important to note that", "notably"),
    ("in spite of the fact that", "although"),
    ("on a daily basis", "daily"),
    ("on a regular basis", "regularly"),
    ("at the present time", "now"),
    ("in close proximity to", "near"),
    ("with regard to", "regarding"),
    ("in reference to", "about"),
    ("a large number of", "many"),
    ("a majority of", "most"),
    ("has the ability to", "can"),
    ("is able to", "can"),
    ("make a decision", "decide"),
    ("take into consideration", "consider"),
    ("come to a conclusion", "conclude"),
    ("give consideration to", "consider"),
    ("in light of the fact that", "because"),
    ("by means of", "by"),
    ("in a manner that", "so that"),
    ("on the grounds that", "because"),
    ("with the exception of", "except"),
    ("prior to", "before"),
    ("subsequent to", "after"),
    ("in the near future", "soon"),
    ("in the absence of", "without"),
    ("a number of", "several"),
    ("in excess of", "more than"),
    ("in conjunction with", "with"),
    ("has the capacity to", "can"),
    ("each and every", "each"),
    ("first and foremost", "first"),
    ("basic fundamentals", "fundamentals"),
    ("end result", "result"),
    ("past history", "history"),
    ("free gift", "gift"),
    ("final outcome", "outcome"),
    ("future plans", "plans"),
    ("general consensus", "consensus"),
    ("completely eliminate", "eliminate"),
    ("absolutely essential", "essential"),
]

_WEAK_VERBS: set[str] = {
    "is",
    "am",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "get",
    "gets",
    "got",
    "gotten",
    "do",
    "does",
    "did",
    "make",
    "makes",
    "made",
}


def _load_spacy():
    """Lazy-load spaCy model."""
    try:
        import spacy

        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli import download

            download("en_core_web_sm")
            return spacy.load("en_core_web_sm")
    except ImportError:
        logger.warning("spaCy not installed — grammar checker will use regex-only mode")
        return None


class GrammarChecker:
    """Detects grammar errors and style issues in text."""

    def __init__(self) -> None:
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = _load_spacy()
        return self._nlp

    def analyze(self, text: str) -> Dict[str, Any]:
        """Run full grammar and style check."""
        errors: List[Dict[str, Any]] = []
        style_issues: List[Dict[str, Any]] = []

        doc = self.nlp(text) if self.nlp else None
        sentences = self._split_sentences(text)

        # Grammar checks
        errors.extend(self._check_repeated_words(text))
        errors.extend(self._check_double_negatives(text))
        errors.extend(self._check_run_on_sentences(sentences))
        errors.extend(self._check_sentence_fragments(sentences, doc))
        errors.extend(self._check_subject_verb_agreement(text))
        errors.extend(self._check_comma_splices(text))
        errors.extend(self._check_missing_articles(doc))

        passive_info = self._check_passive_voice(sentences, doc)
        if passive_info["overuse"]:
            errors.append(
                {
                    "type": "grammar",
                    "message": f"Passive voice overuse: {passive_info['percentage']:.0f}% of sentences use passive voice (threshold: 30%)",
                    "position": None,
                    "suggestion": "Rewrite some passive sentences in active voice for stronger writing.",
                }
            )

        # Style checks
        style_issues.extend(self._check_cliches(text))
        style_issues.extend(self._check_wordiness(text))
        style_issues.extend(self._check_adverb_overuse(doc))
        style_issues.extend(self._check_weak_verbs(doc))

        all_issues = errors + style_issues
        error_count = len(errors)
        style_count = len(style_issues)

        # Scores: 100 minus deductions
        grammar_score = max(0, 100 - error_count * 5)
        style_score = max(0, 100 - style_count * 3)

        return {
            "error_count": error_count,
            "style_issue_count": style_count,
            "errors": all_issues,
            "grammar_score": grammar_score,
            "style_score": style_score,
            "passive_voice_percentage": round(passive_info["percentage"], 2),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    # ------------------------------------------------------------------
    # Grammar checks
    # ------------------------------------------------------------------

    def _check_repeated_words(self, text: str) -> List[Dict[str, Any]]:
        """Detect immediately repeated words like 'the the'."""
        issues = []
        pattern = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            issues.append(
                {
                    "type": "grammar",
                    "message": f"Repeated word: '{match.group(1)}'",
                    "position": {"start": match.start(), "end": match.end()},
                    "suggestion": f"Remove the duplicate '{match.group(1)}'.",
                }
            )
        return issues

    def _check_double_negatives(self, text: str) -> List[Dict[str, Any]]:
        """Detect double negatives."""
        issues = []
        patterns = [
            r"\b(don't|doesn't|didn't|can't|won't|shouldn't|wouldn't|couldn't|isn't|aren't|wasn't|weren't)\s+\w*\s*(no|not|never|nothing|nowhere|nobody|none|neither)\b",
            r"\b(not|never)\s+\w*\s*(no|not|never|nothing|nowhere|nobody|none|neither|un\w+)\b",
        ]
        for pat in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                issues.append(
                    {
                        "type": "grammar",
                        "message": f"Possible double negative: '{match.group()}'",
                        "position": {"start": match.start(), "end": match.end()},
                        "suggestion": "Rewrite to use a single negative for clarity.",
                    }
                )
        return issues

    def _check_run_on_sentences(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """Flag sentences with more than 50 words."""
        issues = []
        offset = 0
        for sent in sentences:
            word_count = len(sent.split())
            if word_count > 50:
                issues.append(
                    {
                        "type": "grammar",
                        "message": f"Run-on sentence ({word_count} words). Consider breaking it up.",
                        "position": {"start": offset, "end": offset + len(sent)},
                        "suggestion": "Split this into two or more shorter sentences.",
                    }
                )
            offset += len(sent) + 1
        return issues

    def _check_sentence_fragments(self, sentences: List[str], doc) -> List[Dict[str, Any]]:
        """Detect sentence fragments (no main verb)."""
        issues = []
        if doc is None:
            return issues

        # Process each sentence individually for accuracy
        offset = 0
        for sent_text in sentences:
            sent_doc = self.nlp(sent_text)
            has_verb = any(
                token.pos_ in ("VERB", "AUX") and token.dep_ != "amod" for token in sent_doc
            )
            word_count = len(sent_text.split())
            # Only flag as fragment if more than 3 words and no verb
            if not has_verb and word_count > 3:
                issues.append(
                    {
                        "type": "grammar",
                        "message": f"Possible sentence fragment (no main verb detected): '{sent_text[:60]}...'",
                        "position": {"start": offset, "end": offset + len(sent_text)},
                        "suggestion": "Add a verb or combine with an adjacent sentence.",
                    }
                )
            offset += len(sent_text) + 1
        return issues

    def _check_subject_verb_agreement(self, text: str) -> List[Dict[str, Any]]:
        """Basic subject-verb agreement checks via regex."""
        issues = []
        patterns = [
            (r"\b(he|she|it)\s+(are|were|have)\b", "should use 'is/was/has'"),
            (r"\b(they|we)\s+(is|was|has)\b", "should use 'are/were/have'"),
            (r"\b(I)\s+(is|has|was)\b", "should use 'am/have/was'"),
            (r"\b(you)\s+(is|was|has)\b", "should use 'are/were/have'"),
            (r"\b(this|that)\s+(are|were)\b", "consider 'is/was'"),
            (r"\b(these|those)\s+(is|was)\b", "consider 'are/were'"),
        ]
        for pattern, suggestion in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                issues.append(
                    {
                        "type": "grammar",
                        "message": f"Possible subject-verb agreement issue: '{match.group()}'",
                        "position": {"start": match.start(), "end": match.end()},
                        "suggestion": suggestion,
                    }
                )
        return issues

    def _check_comma_splices(self, text: str) -> List[Dict[str, Any]]:
        """Detect comma splices: two independent clauses joined by only a comma."""
        issues = []
        # Heuristic: comma followed by a pronoun or proper subject starting a new clause
        pattern = re.compile(
            r",\s+(he|she|it|they|we|I|you|this|that|these|those)\s+(is|are|was|were|will|would|can|could|has|have|had|do|does|did)\b",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            issues.append(
                {
                    "type": "grammar",
                    "message": f"Possible comma splice near: '...{text[max(0,match.start()-20):match.end()+10]}...'",
                    "position": {"start": match.start(), "end": match.end()},
                    "suggestion": "Use a semicolon, period, or conjunction instead of a comma.",
                }
            )
        return issues

    def _check_missing_articles(self, doc) -> List[Dict[str, Any]]:
        """Detect potential missing articles before singular countable nouns."""
        issues = []
        if doc is None:
            return issues

        for i, token in enumerate(doc):
            if (
                token.pos_ == "NOUN"
                and token.tag_ in ("NN",)  # singular noun
                and token.dep_ in ("nsubj", "dobj", "attr", "pobj")
            ):
                # Check if preceded by a determiner, possessive, or adjective chain
                has_det = False
                for left in token.lefts:
                    if left.pos_ in ("DET", "PRON") or left.dep_ == "poss":
                        has_det = True
                        break
                    if left.pos_ == "ADJ":
                        for adj_left in left.lefts:
                            if adj_left.pos_ in ("DET", "PRON"):
                                has_det = True
                                break
                # Also check immediate predecessor
                if i > 0 and doc[i - 1].pos_ in ("DET", "PRON", "NUM", "PROPN"):
                    has_det = True
                if i > 0 and doc[i - 1].dep_ == "compound":
                    has_det = True
                # Proper nouns and mass nouns are OK without articles
                if token.ent_type_ or token.text[0].isupper():
                    has_det = True

                if not has_det:
                    issues.append(
                        {
                            "type": "grammar",
                            "message": f"Possible missing article before '{token.text}'",
                            "position": {"start": token.idx, "end": token.idx + len(token.text)},
                            "suggestion": f"Consider adding 'a', 'an', or 'the' before '{token.text}'.",
                        }
                    )
        return issues

    def _check_passive_voice(self, sentences: List[str], doc) -> Dict[str, Any]:
        """Count passive voice sentences."""
        if doc is None or not sentences:
            return {"overuse": False, "percentage": 0.0, "count": 0}

        passive_count = 0
        for sent_text in sentences:
            sent_doc = self.nlp(sent_text)
            for token in sent_doc:
                if token.dep_ in ("nsubjpass", "auxpass"):
                    passive_count += 1
                    break

        pct = (passive_count / len(sentences)) * 100 if sentences else 0
        return {
            "overuse": pct > 30,
            "percentage": pct,
            "count": passive_count,
        }

    # ------------------------------------------------------------------
    # Style checks
    # ------------------------------------------------------------------

    def _check_cliches(self, text: str) -> List[Dict[str, Any]]:
        """Detect cliches in text."""
        issues = []
        text_lower = text.lower()
        for cliche in _CLICHES:
            idx = text_lower.find(cliche)
            if idx != -1:
                issues.append(
                    {
                        "type": "style",
                        "message": f"Cliche detected: '{cliche}'",
                        "position": {"start": idx, "end": idx + len(cliche)},
                        "suggestion": "Consider replacing this cliche with more original phrasing.",
                    }
                )
        return issues

    def _check_wordiness(self, text: str) -> List[Dict[str, Any]]:
        """Detect wordy phrases and suggest concise alternatives."""
        issues = []
        text_lower = text.lower()
        for verbose, concise in _WORDINESS:
            idx = text_lower.find(verbose)
            if idx != -1:
                issues.append(
                    {
                        "type": "style",
                        "message": f"Wordy phrase: '{verbose}'",
                        "position": {"start": idx, "end": idx + len(verbose)},
                        "suggestion": f"Replace with '{concise}'.",
                    }
                )
        return issues

    def _check_adverb_overuse(self, doc) -> List[Dict[str, Any]]:
        """Flag excessive adverb usage (>5% of tokens ending in -ly)."""
        issues = []
        if doc is None:
            return issues

        ly_adverbs = [
            token for token in doc if token.pos_ == "ADV" and token.text.lower().endswith("ly")
        ]
        total = len(doc) or 1
        ratio = len(ly_adverbs) / total

        if ratio > 0.05:
            adverb_examples = [a.text for a in ly_adverbs[:5]]
            issues.append(
                {
                    "type": "style",
                    "message": f"Adverb overuse: {len(ly_adverbs)} -ly adverbs found ({ratio*100:.1f}% of words). Examples: {', '.join(adverb_examples)}",
                    "position": None,
                    "suggestion": "Reduce adverb usage by choosing stronger verbs.",
                }
            )
        return issues

    def _check_weak_verbs(self, doc) -> List[Dict[str, Any]]:
        """Flag overuse of weak verbs (is, was, were, have, get, etc.)."""
        issues = []
        if doc is None:
            return issues

        verb_tokens = [t for t in doc if t.pos_ in ("VERB", "AUX")]
        if not verb_tokens:
            return issues

        weak_count = sum(1 for t in verb_tokens if t.lemma_.lower() in _WEAK_VERBS)
        ratio = weak_count / len(verb_tokens)

        if ratio > 0.5 and weak_count > 5:
            issues.append(
                {
                    "type": "style",
                    "message": f"Weak verb overuse: {weak_count}/{len(verb_tokens)} verbs ({ratio*100:.0f}%) are weak verbs (is, was, have, get, etc.)",
                    "position": None,
                    "suggestion": "Replace weak verbs with stronger, more specific alternatives.",
                }
            )
        return issues
