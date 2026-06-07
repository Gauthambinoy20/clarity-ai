"""
Basic fact verification engine for ClarityAI.

Extracts factual claims from text (numbers, dates, percentages, named entities),
categorises them, and flags vague/unverifiable attributions.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for factual claim extraction
# ---------------------------------------------------------------------------

# Percentages: "45%", "45.2 percent", "45 per cent"
_PCT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:%|percent|per\s*cent)\b", re.IGNORECASE)

# Dates: "January 2024", "01/15/2024", "2024-01-15", "15th of March, 2023"
_DATE_RE = re.compile(
    r"\b(?:"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}"
    r"|"
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r",?\s*\d{4}"
    r"|"
    r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}"
    r"|"
    r"\d{4}[/\-]\d{1,2}[/\-]\d{1,2}"
    r"|"
    r"\b(?:in|since|by|from|until)\s+\d{4}\b"
    r")\b",
    re.IGNORECASE,
)

# Year references: standalone 4-digit years in plausible range
_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|2[01]\d{2})\b")

# Quantities with units: "5 million", "$3.2 billion", "100 kg"
_QUANTITY_RE = re.compile(
    r"\b\$?\d+(?:,\d{3})*(?:\.\d+)?\s*"
    r"(?:million|billion|trillion|thousand|hundred|"
    r"kg|km|miles|meters|metres|pounds|dollars|euros|tons|tonnes|"
    r"people|users|employees|students|patients|participants)\b",
    re.IGNORECASE,
)

# Generic number claims: "there are 42 countries", "more than 500"
_NUMBER_RE = re.compile(
    r"\b(?:approximately|about|around|more than|less than|over|under|nearly|almost|exactly)?"
    r"\s*\d+(?:,\d{3})*(?:\.\d+)?\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Vague attribution patterns (unverifiable without citations)
# ---------------------------------------------------------------------------

_VAGUE_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bstudies\s+(?:have\s+)?show(?:n|s)?\b",
        r"\bresearch\s+(?:has\s+)?(?:shown|indicates?|suggests?|demonstrates?|reveals?)\b",
        r"\bexperts?\s+(?:say|believe|agree|suggest|argue|claim|note)\b",
        r"\bscientists?\s+(?:say|believe|have found|discovered|claim)\b",
        r"\baccording to\s+(?:some|many|most|several|various)\s+(?:studies|experts?|researchers?|sources?)\b",
        r"\bit is widely (?:known|accepted|believed|recognized|acknowledged)\b",
        r"\bmany (?:people|experts?|researchers?|scientists?|scholars?)\s+(?:believe|think|argue|suggest)\b",
        r"\bsome (?:studies|research|experts?|scientists?)\s+(?:suggest|indicate|show|claim)\b",
        r"\bevidence suggests?\b",
        r"\b(?:a |the )?(?:recent|new|latest|growing body of)\s+(?:study|research|evidence|data)\s+(?:shows?|suggests?|indicates?|finds?|found)\b",
        r"\bit (?:has been|is)\s+(?:proven|established|demonstrated|confirmed)\s+that\b",
        r"\bstatistics?\s+(?:show|indicate|suggest|reveal)\b",
        r"\bdata\s+(?:shows?|suggests?|indicates?|reveals?)\b",
        r"\breports?\s+(?:show|indicate|suggest|reveal|claim)\b",
        r"\banalysts?\s+(?:say|believe|predict|expect|suggest)\b",
    ]
]


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _load_spacy():
    """Lazy-load spaCy for NER."""
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
        logger.warning("spaCy not installed; NER-based claim extraction disabled.")
        return None


class FactChecker:
    """
    Extracts factual claims from text, categorises them, and flags
    vague/unverifiable attributions.
    """

    def __init__(self) -> None:
        self._nlp = None
        self._nlp_loaded = False

    @property
    def nlp(self):
        if not self._nlp_loaded:
            self._nlp = _load_spacy()
            self._nlp_loaded = True
        return self._nlp

    # ------------------------------------------------------------------
    # Claim extraction
    # ------------------------------------------------------------------

    def _extract_regex_claims(self, text: str) -> List[Dict[str, Any]]:
        """Extract claims using regex patterns."""
        claims: List[Dict[str, Any]] = []
        seen_spans: set = set()

        # Percentages
        for m in _PCT_RE.finditer(text):
            span = (m.start(), m.end())
            if span not in seen_spans:
                seen_spans.add(span)
                claims.append(
                    {
                        "text": m.group().strip(),
                        "category": "statistical",
                        "start": m.start(),
                        "end": m.end(),
                        "verifiable": True,
                    }
                )

        # Dates
        for m in _DATE_RE.finditer(text):
            span = (m.start(), m.end())
            if span not in seen_spans:
                seen_spans.add(span)
                claims.append(
                    {
                        "text": m.group().strip(),
                        "category": "temporal",
                        "start": m.start(),
                        "end": m.end(),
                        "verifiable": True,
                    }
                )

        # Quantities with units
        for m in _QUANTITY_RE.finditer(text):
            span = (m.start(), m.end())
            if span not in seen_spans:
                seen_spans.add(span)
                claims.append(
                    {
                        "text": m.group().strip(),
                        "category": "quantitative",
                        "start": m.start(),
                        "end": m.end(),
                        "verifiable": True,
                    }
                )

        return claims

    def _extract_ner_claims(self, text: str) -> List[Dict[str, Any]]:
        """Extract named-entity claims using spaCy NER."""
        nlp = self.nlp
        if nlp is None:
            return []

        doc = nlp(text)
        claims: List[Dict[str, Any]] = []
        # Entity types that represent factual claims
        target_labels = {
            "PERSON",
            "ORG",
            "GPE",
            "LOC",
            "DATE",
            "MONEY",
            "QUANTITY",
            "PERCENT",
            "EVENT",
            "PRODUCT",
            "FAC",
            "NORP",
            "LAW",
            "WORK_OF_ART",
        }

        for ent in doc.ents:
            if ent.label_ in target_labels:
                category = "named_entity"
                if ent.label_ in {"DATE"}:
                    category = "temporal"
                elif ent.label_ in {"MONEY", "QUANTITY", "PERCENT"}:
                    category = "quantitative"

                claims.append(
                    {
                        "text": ent.text.strip(),
                        "category": category,
                        "entity_type": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "verifiable": True,
                    }
                )

        return claims

    def _find_vague_claims(self, text: str) -> List[Dict[str, Any]]:
        """Find vague attribution phrases that lack specific citations."""
        vague_claims: List[Dict[str, Any]] = []

        for pattern in _VAGUE_PATTERNS:
            for m in pattern.finditer(text):
                # Get the surrounding sentence for context
                sentence_start = text.rfind(".", 0, m.start())
                sentence_start = sentence_start + 1 if sentence_start != -1 else 0
                sentence_end = text.find(".", m.end())
                sentence_end = sentence_end + 1 if sentence_end != -1 else len(text)
                context = text[sentence_start:sentence_end].strip()

                vague_claims.append(
                    {
                        "text": m.group().strip(),
                        "context": context[:300],
                        "start": m.start(),
                        "end": m.end(),
                        "issue": "vague_attribution",
                        "suggestion": (
                            "Add a specific citation, study name, author, "
                            "or data source to support this claim."
                        ),
                    }
                )

        return vague_claims

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate claims based on overlapping text spans."""
        if not claims:
            return []

        # Sort by start position
        sorted_claims = sorted(claims, key=lambda c: (c["start"], -c["end"]))
        deduped: List[Dict[str, Any]] = [sorted_claims[0]]

        for claim in sorted_claims[1:]:
            last = deduped[-1]
            # Skip if this claim's span is fully within the last one
            if claim["start"] >= last["start"] and claim["end"] <= last["end"]:
                continue
            # Skip if significant overlap
            if claim["start"] < last["end"] and claim["end"] > last["start"]:
                overlap = min(claim["end"], last["end"]) - max(claim["start"], last["start"])
                span_min = min(
                    claim["end"] - claim["start"],
                    last["end"] - last["start"],
                )
                if span_min > 0 and overlap / span_min > 0.5:
                    continue
            deduped.append(claim)

        return deduped

    # ------------------------------------------------------------------
    # Credibility scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_credibility_score(
        total_claims: int,
        verifiable_count: int,
        vague_count: int,
        word_count: int,
    ) -> float:
        """
        Compute a credibility score (0-100) based on:
        - Ratio of verifiable to total claims
        - Penalty for vague attributions
        - Factual density
        """
        if total_claims == 0 and vague_count == 0:
            return 50.0  # neutral -- no claims at all

        score = 50.0  # baseline

        # Reward verifiable claims
        if total_claims > 0:
            verifiable_ratio = verifiable_count / total_claims
            score += verifiable_ratio * 25.0  # up to +25

        # Penalise vague claims
        if vague_count > 0:
            vague_penalty = min(vague_count * 5.0, 30.0)
            score -= vague_penalty

        # Reward factual density (claims per 100 words)
        if word_count > 0:
            density = (total_claims / word_count) * 100
            if density >= 2.0:
                score += 15.0
            elif density >= 1.0:
                score += 10.0
            elif density >= 0.5:
                score += 5.0

        # Bonus if there are zero vague claims and multiple verifiable ones
        if vague_count == 0 and verifiable_count >= 3:
            score += 10.0

        return round(max(0.0, min(100.0, score)), 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for factual claims and credibility.

        Returns
        -------
        dict with keys:
            claims_found         : list of claim dicts
            vague_claims         : list of vague attribution dicts
            vague_claims_count   : int
            verifiable_claims_count : int
            factual_density      : float (claims per 100 words)
            credibility_score    : float 0-100
            claim_categories     : dict of category -> count
        """
        words = text.split()
        word_count = len(words)

        if word_count < 5:
            return {
                "claims_found": [],
                "vague_claims": [],
                "vague_claims_count": 0,
                "verifiable_claims_count": 0,
                "factual_density": 0.0,
                "credibility_score": 50.0,
                "claim_categories": {},
            }

        # Extract claims from both regex and NER
        regex_claims = self._extract_regex_claims(text)
        ner_claims = self._extract_ner_claims(text)

        # Merge and deduplicate
        all_claims = regex_claims + ner_claims
        all_claims = self._deduplicate_claims(all_claims)

        # Extract vague attributions
        vague_claims = self._find_vague_claims(text)

        # Counts
        verifiable_count = sum(1 for c in all_claims if c.get("verifiable", False))
        total_claims = len(all_claims)
        vague_count = len(vague_claims)

        # Factual density
        factual_density = (total_claims / word_count) * 100 if word_count > 0 else 0.0

        # Category breakdown
        categories: Dict[str, int] = {}
        for claim in all_claims:
            cat = claim.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        # Credibility
        credibility = self._compute_credibility_score(
            total_claims, verifiable_count, vague_count, word_count
        )

        return {
            "claims_found": all_claims,
            "vague_claims": vague_claims,
            "vague_claims_count": vague_count,
            "verifiable_claims_count": verifiable_count,
            "factual_density": round(factual_density, 4),
            "credibility_score": credibility,
            "claim_categories": categories,
        }
