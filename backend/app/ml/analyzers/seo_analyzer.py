"""
SEO content analysis engine for ClarityAI.

Evaluates text for search-engine optimisation quality: keyword density,
heading structure, readability, paragraph length, transition words,
passive voice, sentence length, internal linking opportunities, and
meta description suitability.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transition words / phrases (English)
# ---------------------------------------------------------------------------
TRANSITION_WORDS: set[str] = {
    # Addition
    "also",
    "furthermore",
    "moreover",
    "additionally",
    "besides",
    "likewise",
    "similarly",
    "equally",
    "too",
    "again",
    "further",
    "then",
    # Contrast
    "however",
    "nevertheless",
    "nonetheless",
    "although",
    "though",
    "whereas",
    "while",
    "but",
    "yet",
    "still",
    "instead",
    "conversely",
    "alternatively",
    "rather",
    "otherwise",
    # Cause / effect
    "because",
    "since",
    "therefore",
    "consequently",
    "thus",
    "hence",
    "accordingly",
    "so",
    # Sequence
    "first",
    "firstly",
    "second",
    "secondly",
    "third",
    "thirdly",
    "finally",
    "next",
    "meanwhile",
    "afterward",
    "afterwards",
    "subsequently",
    "previously",
    "lastly",
    # Emphasis
    "indeed",
    "certainly",
    "surely",
    "clearly",
    "obviously",
    "especially",
    "particularly",
    "notably",
    "importantly",
    "significantly",
    # Example
    "for example",
    "for instance",
    "specifically",
    "namely",
    "such as",
    "including",
    "particularly",
    # Conclusion
    "in conclusion",
    "to summarize",
    "overall",
    "ultimately",
    "in summary",
    "in short",
    "briefly",
    # Comparison
    "similarly",
    "likewise",
    "compared to",
    "in comparison",
    "just as",
    "in the same way",
}

# Multi-word transitions that need phrase matching
_MULTI_WORD_TRANSITIONS: List[str] = [t for t in TRANSITION_WORDS if " " in t]

# Passive voice auxiliary + past participle pattern
_PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|been|being|be|am)\s+(?:\w+\s+)*?"
    r"(?:ed|en|wn|ht|lt|pt|rn|st|ft|nt|xt)\b",
    re.IGNORECASE,
)

# More precise passive: auxiliary + optional adverb + past participle
_PASSIVE_PRECISE_RE = re.compile(
    r"\b(?:is|are|was|were|been|being|be|am|get|gets|got|gotten)\s+"
    r"(?:\w+ly\s+)?(?:\w+ed|written|spoken|taken|given|shown|known|made|done|seen|found|told|gone|built|sent|left|held|kept|brought|bought|thought|caught|taught|sought|fought|meant|said|paid|read|run|set|put|cut|let|hit|shut|split|spread|rid|quit|hurt|cost)\b",
    re.IGNORECASE,
)

# Stop words to exclude from keyword analysis
_STOP_WORDS: set[str] = {
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
    "are",
    "was",
    "were",
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
    "it",
    "its",
    "not",
    "no",
    "nor",
    "so",
    "if",
    "as",
    "up",
    "out",
    "about",
    "into",
    "over",
    "after",
    "than",
    "then",
    "very",
    "just",
    "also",
    "more",
    "most",
    "other",
    "some",
    "such",
    "only",
    "same",
    "both",
    "each",
    "all",
    "any",
    "few",
    "many",
    "much",
    "own",
    "new",
    "old",
    "well",
    "even",
    "here",
    "there",
    "when",
    "where",
    "how",
    "what",
    "which",
    "who",
    "whom",
    "why",
    "our",
    "your",
    "my",
    "his",
    "her",
    "their",
    "we",
    "you",
    "he",
    "she",
    "they",
    "i",
    "me",
    "him",
    "us",
    "them",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _split_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text)


def _count_syllables(word: str) -> int:
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    word = re.sub(r"e$", "", word)
    vowel_groups = re.findall(r"[aeiouy]+", word)
    return max(1, len(vowel_groups))


# ---------------------------------------------------------------------------
# SEO Analyzer
# ---------------------------------------------------------------------------


class SEOAnalyzer:
    """Comprehensive SEO content quality analyzer."""

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Run full SEO analysis.

        Returns
        -------
        dict with keys:
            seo_score          : float 0-100
            keyword_analysis   : list of keyword dicts (top 10)
            recommendations    : list of actionable recommendation strings
            metrics            : dict of individual metric values
        """
        words = _split_words(text)
        sentences = _split_sentences(text)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]

        if not words or not sentences:
            return self._empty_result()

        word_count = len(words)
        sentence_count = len(sentences)
        paragraph_count = len(paragraphs)

        # 1. Keyword density analysis
        keyword_analysis = self._keyword_density(words, word_count)

        # 2. Heading detection
        headings = self._detect_headings(text)

        # 3. Readability (Flesch Reading Ease)
        flesch = self._flesch_reading_ease(words, sentences)

        # 4. Paragraph length check
        para_metrics = self._paragraph_length_check(paragraphs)

        # 5. Transition word percentage
        transition_pct = self._transition_word_percentage(sentences)

        # 6. Passive voice percentage
        passive_pct = self._passive_voice_percentage(sentences)

        # 7. Sentence length distribution
        sentence_metrics = self._sentence_length_metrics(sentences)

        # 8. Meta description check
        meta_check = self._meta_description_check(paragraphs)

        # Build metrics
        metrics = {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "heading_count": len(headings),
            "flesch_reading_ease": flesch,
            "avg_paragraph_sentences": para_metrics["avg_sentences_per_paragraph"],
            "transition_word_percentage": transition_pct,
            "passive_voice_percentage": passive_pct,
            "avg_sentence_length": sentence_metrics["avg_length"],
            "long_sentence_count": sentence_metrics["long_count"],
            "meta_description_length": meta_check["length"],
            "meta_description_ideal": meta_check["is_ideal"],
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, headings, para_metrics)

        # Compute overall SEO score
        seo_score = self._compute_seo_score(metrics, headings)

        return {
            "seo_score": seo_score,
            "keyword_analysis": keyword_analysis,
            "recommendations": recommendations,
            "metrics": metrics,
            "headings": headings,
        }

    # ------------------------------------------------------------------
    # 1. Keyword density
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_density(words: List[str], word_count: int) -> List[Dict[str, Any]]:
        """Return top 10 keywords with frequency and density percentage."""
        filtered = [w.lower() for w in words if w.lower() not in _STOP_WORDS and len(w) > 2]
        counter = Counter(filtered)
        top_10 = counter.most_common(10)

        return [
            {
                "keyword": kw,
                "frequency": freq,
                "density_percent": round((freq / word_count) * 100, 2) if word_count > 0 else 0.0,
            }
            for kw, freq in top_10
        ]

    # ------------------------------------------------------------------
    # 2. Heading detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_headings(text: str) -> List[Dict[str, Any]]:
        """Detect headings: lines starting with # (Markdown) or ALL CAPS lines."""
        headings: List[Dict[str, Any]] = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # Markdown headings
            md_match = re.match(r"^(#{1,6})\s+(.+)", stripped)
            if md_match:
                level = len(md_match.group(1))
                headings.append(
                    {
                        "text": md_match.group(2).strip(),
                        "level": level,
                        "type": "markdown",
                        "line": i + 1,
                    }
                )
                continue

            # ALL CAPS lines (at least 3 words, all uppercase alpha chars)
            words_in_line = re.findall(r"[A-Za-z]+", stripped)
            if (
                len(words_in_line) >= 2
                and len(stripped) < 100
                and stripped == stripped.upper()
                and any(c.isalpha() for c in stripped)
            ):
                headings.append(
                    {
                        "text": stripped,
                        "level": 2,  # treat as H2
                        "type": "all_caps",
                        "line": i + 1,
                    }
                )

        return headings

    # ------------------------------------------------------------------
    # 3. Readability
    # ------------------------------------------------------------------

    @staticmethod
    def _flesch_reading_ease(words: List[str], sentences: List[str]) -> float:
        """Compute Flesch Reading Ease score."""
        num_words = len(words)
        num_sentences = len(sentences)
        if num_words == 0 or num_sentences == 0:
            return 0.0

        num_syllables = sum(_count_syllables(w) for w in words)
        fre = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
        return round(max(0.0, min(100.0, fre)), 2)

    # ------------------------------------------------------------------
    # 4. Paragraph length check
    # ------------------------------------------------------------------

    @staticmethod
    def _paragraph_length_check(paragraphs: List[str]) -> Dict[str, Any]:
        """Check paragraph lengths (ideal: 2-4 sentences each)."""
        para_sentence_counts: List[int] = []
        too_long: List[int] = []
        too_short: List[int] = []

        for i, para in enumerate(paragraphs):
            sents = _split_sentences(para)
            count = len(sents)
            para_sentence_counts.append(count)
            if count > 4:
                too_long.append(i)
            elif count < 2 and len(para.split()) > 5:
                # Only flag short if it has meaningful content
                too_short.append(i)

        avg = sum(para_sentence_counts) / len(para_sentence_counts) if para_sentence_counts else 0

        return {
            "avg_sentences_per_paragraph": round(avg, 2),
            "too_long_paragraphs": too_long,
            "too_short_paragraphs": too_short,
            "paragraph_sentence_counts": para_sentence_counts,
        }

    # ------------------------------------------------------------------
    # 5. Transition word percentage
    # ------------------------------------------------------------------

    @staticmethod
    def _transition_word_percentage(sentences: List[str]) -> float:
        """Percentage of sentences that contain at least one transition word/phrase."""
        if not sentences:
            return 0.0

        count = 0
        for sent in sentences:
            sent_lower = sent.lower()
            # Check multi-word transitions first
            has_transition = False
            for phrase in _MULTI_WORD_TRANSITIONS:
                if phrase in sent_lower:
                    has_transition = True
                    break

            if not has_transition:
                # Check single-word transitions
                words = set(re.findall(r"[a-z]+", sent_lower))
                single_word_transitions = {t for t in TRANSITION_WORDS if " " not in t}
                if words & single_word_transitions:
                    has_transition = True

            if has_transition:
                count += 1

        return round((count / len(sentences)) * 100, 2)

    # ------------------------------------------------------------------
    # 6. Passive voice percentage
    # ------------------------------------------------------------------

    @staticmethod
    def _passive_voice_percentage(sentences: List[str]) -> float:
        """Percentage of sentences containing passive voice constructions."""
        if not sentences:
            return 0.0

        passive_count = 0
        for sent in sentences:
            if _PASSIVE_PRECISE_RE.search(sent):
                passive_count += 1

        return round((passive_count / len(sentences)) * 100, 2)

    # ------------------------------------------------------------------
    # 7. Sentence length distribution
    # ------------------------------------------------------------------

    @staticmethod
    def _sentence_length_metrics(sentences: List[str]) -> Dict[str, Any]:
        """Compute sentence length statistics."""
        if not sentences:
            return {"avg_length": 0.0, "long_count": 0, "distribution": []}

        lengths = [len(s.split()) for s in sentences]
        avg = sum(lengths) / len(lengths)
        long_count = sum(1 for length in lengths if length > 20)

        # Distribution buckets
        buckets = {"1-10": 0, "11-20": 0, "21-30": 0, "31+": 0}
        for length in lengths:
            if length <= 10:
                buckets["1-10"] += 1
            elif length <= 20:
                buckets["11-20"] += 1
            elif length <= 30:
                buckets["21-30"] += 1
            else:
                buckets["31+"] += 1

        return {
            "avg_length": round(avg, 2),
            "long_count": long_count,
            "distribution": buckets,
        }

    # ------------------------------------------------------------------
    # 8. Internal linking opportunities
    # ------------------------------------------------------------------

    @staticmethod
    def _internal_link_opportunities(words: List[str], word_count: int) -> List[Dict[str, Any]]:
        """Detect repeated key phrases that could be internal link anchors."""
        # Build 2-gram and 3-gram counts (excluding stop words at boundaries)
        filtered = [w.lower() for w in words]
        opportunities: List[Dict[str, Any]] = []

        for n in (2, 3):
            ngram_counter: Counter = Counter()
            for i in range(len(filtered) - n + 1):
                gram = tuple(filtered[i : i + n])
                # Skip if starts or ends with stop word
                if gram[0] in _STOP_WORDS or gram[-1] in _STOP_WORDS:
                    continue
                ngram_counter[gram] += 1

            for gram, freq in ngram_counter.most_common(10):
                if freq >= 3:
                    phrase = " ".join(gram)
                    opportunities.append(
                        {
                            "phrase": phrase,
                            "frequency": freq,
                            "suggestion": f"Consider linking '{phrase}' to a relevant internal page.",
                        }
                    )

        # Deduplicate and limit
        seen: set = set()
        deduped: List[Dict[str, Any]] = []
        for opp in opportunities:
            if opp["phrase"] not in seen:
                seen.add(opp["phrase"])
                deduped.append(opp)

        return deduped[:10]

    # ------------------------------------------------------------------
    # 9. Meta description check
    # ------------------------------------------------------------------

    @staticmethod
    def _meta_description_check(paragraphs: List[str]) -> Dict[str, Any]:
        """Check if the first paragraph could serve as a meta description."""
        if not paragraphs:
            return {"length": 0, "is_ideal": False, "suggestion": ""}

        first_para = paragraphs[0].strip()
        length = len(first_para)
        is_ideal = 150 <= length <= 160

        suggestion = ""
        if length < 150:
            suggestion = f"First paragraph is {length} chars. Aim for 150-160 chars for an ideal meta description."
        elif length > 160:
            suggestion = f"First paragraph is {length} chars. Trim to 150-160 chars for an ideal meta description."

        return {
            "length": length,
            "is_ideal": is_ideal,
            "suggestion": suggestion,
        }

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_recommendations(
        metrics: Dict[str, Any],
        headings: List[Dict[str, Any]],
        para_metrics: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable SEO recommendations."""
        recs: List[str] = []

        # Word count
        wc = metrics["word_count"]
        if wc < 300:
            recs.append(
                f"Content is only {wc} words. Aim for at least 300 words for SEO value; 1000+ is ideal."
            )
        elif wc < 1000:
            recs.append(
                f"Content is {wc} words. Longer content (1000+ words) tends to rank better."
            )

        # Headings
        if not headings:
            recs.append(
                "No headings detected. Add H1/H2/H3 headings to structure your content for search engines."
            )
        elif not any(h["level"] == 1 for h in headings):
            recs.append("No H1 heading found. Every page should have exactly one H1.")

        # Readability
        flesch = metrics["flesch_reading_ease"]
        if flesch < 60:
            recs.append(
                f"Readability score is {flesch} (target: 60-70). Simplify sentences and use shorter words."
            )
        elif flesch > 70:
            recs.append(
                f"Readability score is {flesch}. This is easy to read, but ensure depth isn't sacrificed."
            )

        # Paragraph length
        if para_metrics["too_long_paragraphs"]:
            count = len(para_metrics["too_long_paragraphs"])
            recs.append(
                f"{count} paragraph(s) have more than 4 sentences. Break them up for better web readability."
            )

        # Transition words
        trans = metrics["transition_word_percentage"]
        if trans < 25:
            recs.append(
                f"Transition word usage is {trans}% (target: >25%). Add more transitional phrases between ideas."
            )

        # Passive voice
        passive = metrics["passive_voice_percentage"]
        if passive > 15:
            recs.append(
                f"Passive voice is {passive}% (target: <15%). Rewrite passive sentences in active voice."
            )

        # Sentence length
        avg_sent = metrics["avg_sentence_length"]
        if avg_sent > 20:
            recs.append(
                f"Average sentence length is {avg_sent} words (target: <20). Shorten long sentences."
            )

        long_count = metrics["long_sentence_count"]
        if long_count > 0:
            recs.append(f"{long_count} sentence(s) exceed 20 words. Consider splitting them.")

        # Meta description
        if not metrics["meta_description_ideal"]:
            meta_len = metrics["meta_description_length"]
            if meta_len < 150:
                recs.append(
                    f"First paragraph ({meta_len} chars) is too short for a meta description. Aim for 150-160 chars."
                )
            elif meta_len > 160:
                recs.append(
                    f"First paragraph ({meta_len} chars) is too long for a meta description. Trim to 150-160 chars."
                )

        if not recs:
            recs.append("Content meets all major SEO targets. Keep up the good work!")

        return recs

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_seo_score(metrics: Dict[str, Any], headings: List[Dict[str, Any]]) -> float:
        """Compute an overall SEO score 0-100."""
        score = 0.0

        # Word count (max 15 points)
        wc = metrics["word_count"]
        if wc >= 1000:
            score += 15
        elif wc >= 600:
            score += 12
        elif wc >= 300:
            score += 8
        else:
            score += 3

        # Headings (max 15 points)
        if headings:
            score += 8
            if any(h["level"] == 1 for h in headings):
                score += 4
            if len(headings) >= 3:
                score += 3
        # else 0

        # Readability (max 15 points) -- target: 60-70
        flesch = metrics["flesch_reading_ease"]
        if 60 <= flesch <= 70:
            score += 15
        elif 50 <= flesch <= 80:
            score += 10
        elif 40 <= flesch <= 90:
            score += 5
        else:
            score += 2

        # Paragraph length (max 10 points) -- target: 2-4 sentences avg
        avg_para = metrics["avg_paragraph_sentences"]
        if 2 <= avg_para <= 4:
            score += 10
        elif 1.5 <= avg_para <= 5:
            score += 7
        else:
            score += 3

        # Transition words (max 10 points) -- target: >25%
        trans = metrics["transition_word_percentage"]
        if trans >= 25:
            score += 10
        elif trans >= 15:
            score += 7
        elif trans >= 10:
            score += 4
        else:
            score += 1

        # Passive voice (max 10 points) -- target: <15%
        passive = metrics["passive_voice_percentage"]
        if passive <= 15:
            score += 10
        elif passive <= 25:
            score += 7
        elif passive <= 35:
            score += 4
        else:
            score += 1

        # Sentence length (max 10 points) -- target: <20 avg
        avg_sent = metrics["avg_sentence_length"]
        if avg_sent <= 20:
            score += 10
        elif avg_sent <= 25:
            score += 7
        elif avg_sent <= 30:
            score += 4
        else:
            score += 1

        # Meta description (max 15 points)
        if metrics["meta_description_ideal"]:
            score += 15
        elif 120 <= metrics["meta_description_length"] <= 180:
            score += 8
        else:
            score += 3

        return round(min(100.0, score), 1)

    # ------------------------------------------------------------------

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "seo_score": 0.0,
            "keyword_analysis": [],
            "recommendations": ["No text provided for analysis."],
            "metrics": {
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "heading_count": 0,
                "flesch_reading_ease": 0.0,
                "avg_paragraph_sentences": 0.0,
                "transition_word_percentage": 0.0,
                "passive_voice_percentage": 0.0,
                "avg_sentence_length": 0.0,
                "long_sentence_count": 0,
                "meta_description_length": 0,
                "meta_description_ideal": False,
            },
            "headings": [],
        }
