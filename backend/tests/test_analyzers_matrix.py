"""
Unit tests for the text analyzer modules.

Each analyzer is exercised across a spread of inputs: a normal English
paragraph, empty string, a single word, a very long text, text with special
characters and unicode, and a non-English snippet.  The tests check that no
analyzer throws on these inputs, that the documented keys are present, and that
numeric scores stay inside their valid ranges.  The one model-backed analyzer
(paraphrase detector) is run against its documented word-overlap fallback so the
suite stays fast and offline.
"""

from __future__ import annotations

import pytest

from tests.conftest import AI_TEXT, HUMAN_TEXT


# ---------------------------------------------------------------------------
# Shared input space
# ---------------------------------------------------------------------------

EMPTY = ""
SINGLE_WORD = "Hello"
# ~2000 words built by repeating a short clause.
LONG_TEXT = ("The quick brown fox jumps over the lazy dog every day. " * 250).strip()
SPECIAL_CHARS = 'Café déjà vu — naïve façade! 100% ✓ <tag> #hash @user $99.99 "quote" 😀 emoji.'
NON_ENGLISH = "El rápido zorro marrón salta sobre el perro perezoso todos los días."

# Inputs that every text-in / dict-out analyzer should survive.
ALL_INPUTS = [
    pytest.param(AI_TEXT, id="ai_paragraph"),
    pytest.param(HUMAN_TEXT, id="human_paragraph"),
    pytest.param(EMPTY, id="empty"),
    pytest.param(SINGLE_WORD, id="single_word"),
    pytest.param(LONG_TEXT, id="long_text"),
    pytest.param(SPECIAL_CHARS, id="special_chars"),
    pytest.param(NON_ENGLISH, id="non_english"),
]


def _assert_keys(result: dict, keys) -> None:
    """Every expected key is present in the result."""
    for key in keys:
        assert key in result, f"missing key: {key}"


# ---------------------------------------------------------------------------
# ReadabilityAnalyzer
# ---------------------------------------------------------------------------


class TestReadabilityAnalyzer:
    @pytest.fixture
    def analyzer(self):
        from app.ml.analyzers.readability import ReadabilityAnalyzer

        return ReadabilityAnalyzer()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, analyzer, text):
        result = analyzer.analyze(text)
        _assert_keys(
            result,
            [
                "flesch_kincaid_grade",
                "flesch_reading_ease",
                "overall_grade",
                "word_count",
                "sentence_count",
                "reading_time_minutes",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_reading_ease_in_range(self, analyzer, text):
        result = analyzer.analyze(text)
        assert 0.0 <= result["flesch_reading_ease"] <= 100.0

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_counts_non_negative(self, analyzer, text):
        result = analyzer.analyze(text)
        assert result["word_count"] >= 0
        assert result["sentence_count"] >= 0

    def test_empty_returns_elementary_grade(self, analyzer):
        result = analyzer.analyze(EMPTY)
        assert result["word_count"] == 0
        assert result["overall_grade"] == "Elementary"

    def test_grade_label_is_valid(self, analyzer):
        result = analyzer.analyze(AI_TEXT)
        assert result["overall_grade"] in {
            "Elementary",
            "Middle School",
            "High School",
            "College",
            "Graduate",
        }


# ---------------------------------------------------------------------------
# TextStatisticsAnalyzer
# ---------------------------------------------------------------------------


class TestTextStatisticsAnalyzer:
    @pytest.fixture
    def analyzer(self):
        from app.ml.analyzers.text_statistics import TextStatisticsAnalyzer

        return TextStatisticsAnalyzer()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, analyzer, text):
        result = analyzer.analyze(text)
        _assert_keys(
            result,
            [
                "word_count",
                "character_count_with_spaces",
                "sentence_count",
                "unique_words",
                "vocabulary_richness",
                "detected_language",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_vocabulary_richness_in_range(self, analyzer, text):
        result = analyzer.analyze(text)
        assert 0.0 <= result["vocabulary_richness"] <= 1.0

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_unique_not_more_than_total(self, analyzer, text):
        result = analyzer.analyze(text)
        assert result["unique_words"] <= result["word_count"] or result["word_count"] == 0

    def test_language_detection_shape(self, analyzer):
        result = analyzer.analyze(AI_TEXT)
        lang = result["detected_language"]
        assert "language" in lang
        assert 0.0 <= lang["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# ToneAnalyzer
# ---------------------------------------------------------------------------


class TestToneAnalyzer:
    @pytest.fixture
    def analyzer(self):
        from app.ml.analyzers.tone_analyzer import ToneAnalyzer

        return ToneAnalyzer()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, analyzer, text):
        result = analyzer.analyze(text)
        _assert_keys(
            result,
            [
                "formality_score",
                "sentiment",
                "emotions",
                "objectivity_score",
                "persuasiveness_score",
                "urgency_level",
                "professional_casual_score",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_scores_in_unit_range(self, analyzer, text):
        result = analyzer.analyze(text)
        for key in (
            "formality_score",
            "objectivity_score",
            "persuasiveness_score",
            "professional_casual_score",
        ):
            assert 0.0 <= result[key] <= 1.0, key

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_sentiment_score_in_range(self, analyzer, text):
        result = analyzer.analyze(text)
        assert -1.0 <= result["sentiment"]["score"] <= 1.0
        assert result["sentiment"]["label"] in {"positive", "negative", "neutral"}

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_emotions_in_range(self, analyzer, text):
        result = analyzer.analyze(text)
        for emotion, value in result["emotions"].items():
            assert 0.0 <= value <= 1.0, emotion

    def test_urgency_level_valid(self, analyzer):
        result = analyzer.analyze(AI_TEXT)
        assert result["urgency_level"]["level"] in {"low", "medium", "high"}


# ---------------------------------------------------------------------------
# GrammarChecker
# ---------------------------------------------------------------------------


class TestGrammarChecker:
    @pytest.fixture
    def checker(self):
        from app.ml.analyzers.grammar_checker import GrammarChecker

        return GrammarChecker()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, checker, text):
        result = checker.analyze(text)
        _assert_keys(
            result,
            [
                "error_count",
                "style_issue_count",
                "errors",
                "grammar_score",
                "style_score",
                "passive_voice_percentage",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_scores_in_range(self, checker, text):
        result = checker.analyze(text)
        assert 0 <= result["grammar_score"] <= 100
        assert 0 <= result["style_score"] <= 100
        assert 0.0 <= result["passive_voice_percentage"] <= 100.0

    def test_repeated_word_flagged(self, checker):
        result = checker.analyze("This is is a clear repeated word problem here.")
        assert result["error_count"] >= 1

    def test_cliche_flagged(self, checker):
        result = checker.analyze("At the end of the day we should think outside the box.")
        assert result["style_issue_count"] >= 1


# ---------------------------------------------------------------------------
# WritingSuggestionEngine
# ---------------------------------------------------------------------------


class TestWritingSuggestionEngine:
    @pytest.fixture
    def engine(self):
        from app.ml.analyzers.writing_suggestions import WritingSuggestionEngine

        return WritingSuggestionEngine()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, engine, text):
        result = engine.analyze(text)
        _assert_keys(
            result,
            [
                "overall_writing_score",
                "suggestion_count",
                "suggestions",
                "category_breakdown",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_score_in_range(self, engine, text):
        result = engine.analyze(text)
        assert 0 <= result["overall_writing_score"] <= 100

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_suggestion_count_matches_list(self, engine, text):
        result = engine.analyze(text)
        assert result["suggestion_count"] == len(result["suggestions"])

    def test_jargon_text_gets_suggestions(self, engine):
        result = engine.analyze(AI_TEXT)
        assert result["suggestion_count"] >= 1


# ---------------------------------------------------------------------------
# WritingCoach
# ---------------------------------------------------------------------------


class TestWritingCoach:
    @pytest.fixture
    def coach(self):
        from app.ml.analyzers.writing_coach import WritingCoach

        return WritingCoach()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, coach, text):
        result = coach.analyze(text)
        _assert_keys(
            result,
            [
                "human_score",
                "suggestions",
                "quick_fixes",
                "total_suggestions",
                "high_impact_count",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_human_score_in_range(self, coach, text):
        result = coach.analyze(text)
        assert 0 <= result["human_score"] <= 100

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_total_matches_suggestions(self, coach, text):
        result = coach.analyze(text)
        assert result["total_suggestions"] == len(result["suggestions"])

    def test_formal_word_suggested(self, coach):
        result = coach.analyze("Furthermore, we will utilize the methodology henceforth.")
        assert result["total_suggestions"] >= 1


# ---------------------------------------------------------------------------
# CitationExtractor
# ---------------------------------------------------------------------------


class TestCitationExtractor:
    @pytest.fixture
    def extractor(self):
        from app.ml.analyzers.citation_extractor import CitationExtractor

        return CitationExtractor()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, extractor, text):
        result = extractor.analyze(text)
        _assert_keys(
            result,
            [
                "citations_found",
                "citation_style",
                "inline_citations",
                "references",
                "reference_count",
                "format_issues",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_counts_match_lists(self, extractor, text):
        result = extractor.analyze(text)
        assert result["citations_found"] == len(result["inline_citations"])
        assert result["reference_count"] == len(result["references"])

    def test_apa_citation_detected(self, extractor):
        result = extractor.analyze("The effect is well documented (Smith, 2020).")
        assert result["citations_found"] >= 1
        assert result["inline_citations"][0]["style"] == "APA"

    def test_no_citation_text_is_unknown(self, extractor):
        result = extractor.analyze("Just a plain sentence with no citations at all.")
        assert result["citation_style"] == "unknown"


# ---------------------------------------------------------------------------
# FactChecker
# ---------------------------------------------------------------------------


class TestFactChecker:
    @pytest.fixture
    def checker(self):
        from app.ml.analyzers.fact_checker import FactChecker

        return FactChecker()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, checker, text):
        result = checker.analyze(text)
        _assert_keys(
            result,
            [
                "claims_found",
                "vague_claims",
                "vague_claims_count",
                "verifiable_claims_count",
                "factual_density",
                "credibility_score",
                "claim_categories",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_credibility_in_range(self, checker, text):
        result = checker.analyze(text)
        assert 0.0 <= result["credibility_score"] <= 100.0

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_counts_match_lists(self, checker, text):
        result = checker.analyze(text)
        assert result["vague_claims_count"] == len(result["vague_claims"])

    def test_percentage_claim_extracted(self, checker):
        result = checker.analyze("In the survey, about 45% of the people agreed with the change.")
        assert result["verifiable_claims_count"] >= 1

    def test_vague_attribution_flagged(self, checker):
        result = checker.analyze("Studies have shown that this approach works better in practice.")
        assert result["vague_claims_count"] >= 1


# ---------------------------------------------------------------------------
# SEOAnalyzer
# ---------------------------------------------------------------------------


class TestSEOAnalyzer:
    @pytest.fixture
    def analyzer(self):
        from app.ml.analyzers.seo_analyzer import SEOAnalyzer

        return SEOAnalyzer()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, analyzer, text):
        result = analyzer.analyze(text)
        _assert_keys(
            result,
            ["seo_score", "keyword_analysis", "recommendations", "metrics", "headings"],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_score_in_range(self, analyzer, text):
        result = analyzer.analyze(text)
        assert 0.0 <= result["seo_score"] <= 100.0

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_keyword_density_in_range(self, analyzer, text):
        result = analyzer.analyze(text)
        for kw in result["keyword_analysis"]:
            assert 0.0 <= kw["density_percent"] <= 100.0

    def test_markdown_heading_detected(self, analyzer):
        text = "# Title\n\nA real paragraph of content goes here with several words.\n"
        result = analyzer.analyze(text)
        assert result["metrics"]["heading_count"] >= 1

    def test_empty_gives_no_text_recommendation(self, analyzer):
        result = analyzer.analyze(EMPTY)
        assert result["seo_score"] == 0.0
        assert result["recommendations"]


# ---------------------------------------------------------------------------
# TextComparisonEngine (two-argument interface)
# ---------------------------------------------------------------------------


class TestTextComparisonEngine:
    @pytest.fixture
    def engine(self):
        from app.ml.analyzers.comparison import TextComparisonEngine

        return TextComparisonEngine()

    @pytest.mark.parametrize(
        "a, b",
        [
            pytest.param(AI_TEXT, HUMAN_TEXT, id="two_paragraphs"),
            pytest.param(EMPTY, EMPTY, id="both_empty"),
            pytest.param(SINGLE_WORD, SINGLE_WORD, id="identical_word"),
            pytest.param(AI_TEXT, EMPTY, id="one_empty"),
            pytest.param(SPECIAL_CHARS, NON_ENGLISH, id="special_vs_non_english"),
            pytest.param(LONG_TEXT, LONG_TEXT, id="identical_long"),
        ],
    )
    def test_returns_documented_keys(self, engine, a, b):
        result = engine.analyze(a, b)
        _assert_keys(
            result,
            [
                "similarity_score",
                "cosine_similarity",
                "jaccard_similarity",
                "edit_distance_ratio",
                "common_phrases",
                "diff_data",
                "structural_comparison",
            ],
        )

    @pytest.mark.parametrize(
        "a, b",
        [
            (AI_TEXT, HUMAN_TEXT),
            (EMPTY, EMPTY),
            (AI_TEXT, EMPTY),
            (LONG_TEXT, LONG_TEXT),
        ],
    )
    def test_similarities_in_range(self, engine, a, b):
        result = engine.analyze(a, b)
        for key in ("similarity_score", "cosine_similarity", "jaccard_similarity"):
            assert 0.0 <= result[key] <= 1.0, key

    def test_identical_text_is_fully_similar(self, engine):
        result = engine.analyze(AI_TEXT, AI_TEXT)
        assert result["cosine_similarity"] == pytest.approx(1.0, abs=1e-6)
        assert result["jaccard_similarity"] == pytest.approx(1.0, abs=1e-6)

    def test_empty_pair_is_zero_similarity(self, engine):
        result = engine.analyze(EMPTY, EMPTY)
        assert result["cosine_similarity"] == 0.0
        assert result["jaccard_similarity"] == 0.0


# ---------------------------------------------------------------------------
# ParaphraseDetector — run against the documented word-overlap fallback
# ---------------------------------------------------------------------------


class TestParaphraseDetector:
    @pytest.fixture
    def detector(self, monkeypatch):
        """Detector with the transformer boundary disabled so the Jaccard fallback runs."""
        from app.ml.analyzers.paraphrase_detector import ParaphraseDetector

        det = ParaphraseDetector()
        # Force the documented offline fallback path: no model available.
        monkeypatch.setattr(det, "_get_model", lambda: None)
        return det

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, detector, text):
        result = detector.analyze(text)
        _assert_keys(
            result,
            [
                "repetition_score",
                "flagged_pairs",
                "self_plagiarism_pairs",
                "clusters",
                "unique_content_ratio",
                "total_sentences",
                "paragraph_count",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_scores_in_range(self, detector, text):
        result = detector.analyze(text)
        assert 0.0 <= result["repetition_score"] <= 1.0
        assert 0.0 <= result["unique_content_ratio"] <= 1.0

    def test_short_text_returns_empty(self, detector):
        result = detector.analyze(SINGLE_WORD)
        assert result["total_sentences"] <= 1
        assert result["flagged_pairs"] == []

    def test_repeated_sentences_flagged(self, detector):
        text = (
            "The committee approved the new budget proposal yesterday afternoon. "
            "The committee approved the new budget proposal yesterday afternoon. "
            "An unrelated note about the weather closes this short document."
        )
        result = detector.analyze(text)
        assert result["self_plagiarism_pairs"], "expected identical sentences to flag"


# ---------------------------------------------------------------------------
# OriginalityScorer (extra ai_score / plagiarism_score args)
# ---------------------------------------------------------------------------


class TestOriginalityScorer:
    @pytest.fixture
    def scorer(self):
        from app.ml.analyzers.originality_score import OriginalityScorer

        return OriginalityScorer()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_score_and_category(self, scorer, text):
        result = scorer.analyze(text)
        assert "originality_score" in result
        assert "category" in result

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_score_in_range(self, scorer, text):
        result = scorer.analyze(text)
        assert 0.0 <= result["originality_score"] <= 100.0

    def test_short_text_is_partially_original(self, scorer):
        result = scorer.analyze(SINGLE_WORD)
        assert result["category"] == "Partially Original"
        assert "error" in result

    def test_high_ai_score_lowers_originality(self, scorer):
        low_ai = scorer.analyze(HUMAN_TEXT, ai_score=0.0, plagiarism_score=0.0)
        high_ai = scorer.analyze(HUMAN_TEXT, ai_score=1.0, plagiarism_score=0.0)
        assert high_ai["originality_score"] <= low_ai["originality_score"]

    def test_category_label_valid(self, scorer):
        result = scorer.analyze(HUMAN_TEXT)
        assert result["category"] in {
            "Highly Original",
            "Mostly Original",
            "Partially Original",
            "Low Originality",
            "Not Original",
        }


# ---------------------------------------------------------------------------
# LanguageDetector
# ---------------------------------------------------------------------------


class TestLanguageDetector:
    @pytest.fixture
    def detector(self):
        from app.ml.analyzers.language_detector import LanguageDetector

        return LanguageDetector()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_returns_documented_keys(self, detector, text):
        result = detector.analyze(text)
        _assert_keys(
            result,
            ["primary_language", "confidence", "all_languages_scores", "is_mixed"],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_confidence_in_range(self, detector, text):
        result = detector.analyze(text)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_short_text_is_unknown(self, detector):
        result = detector.analyze(SINGLE_WORD)
        # "Hello" is 5 chars so it is detected; the empty path is the short one.
        result_empty = detector.analyze(EMPTY)
        assert result_empty["primary_language"] == "unknown"
        assert "error" in result_empty

    def test_english_paragraph_detected(self, detector):
        result = detector.analyze(HUMAN_TEXT)
        assert result["primary_language"] == "English"


# ---------------------------------------------------------------------------
# DocumentFingerprinter (generate / verify interface)
# ---------------------------------------------------------------------------


class TestDocumentFingerprinter:
    @pytest.fixture
    def fingerprinter(self):
        from app.ml.analyzers.document_fingerprint import DocumentFingerprinter

        return DocumentFingerprinter()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_fingerprint_has_keys(self, fingerprinter, text):
        fp = fingerprinter.generate_fingerprint(text)
        _assert_keys(
            fp,
            ["fingerprint_id", "text_hash", "content_hash", "structure_hash", "word_count"],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_hash_lengths(self, fingerprinter, text):
        fp = fingerprinter.generate_fingerprint(text)
        for key in ("text_hash", "content_hash", "structure_hash"):
            assert len(fp[key]) == 64, key  # SHA-256 hex digest

    def test_identical_text_matches(self, fingerprinter):
        fp1 = fingerprinter.generate_fingerprint(AI_TEXT)
        fp2 = fingerprinter.generate_fingerprint(AI_TEXT)
        result = fingerprinter.verify_fingerprints(fp1, fp2)
        assert result["exact_match"] is True
        assert result["content_similarity"] == pytest.approx(1.0, abs=1e-6)

    def test_different_text_not_exact(self, fingerprinter):
        fp1 = fingerprinter.generate_fingerprint(AI_TEXT)
        fp2 = fingerprinter.generate_fingerprint(HUMAN_TEXT)
        result = fingerprinter.verify_fingerprints(fp1, fp2)
        assert result["exact_match"] is False
        assert 0.0 <= result["content_similarity"] <= 1.0


# ---------------------------------------------------------------------------
# VersionTracker (stateful add_version / get_history interface)
# ---------------------------------------------------------------------------


class TestVersionTracker:
    @pytest.fixture
    def tracker(self):
        from app.ml.analyzers.version_tracker import VersionTracker

        return VersionTracker()

    @pytest.fixture(autouse=True)
    def _clear_store(self):
        """Reset the class-level store so tests don't bleed into each other."""
        from app.ml.analyzers.version_tracker import VersionTracker

        VersionTracker._store.clear()
        yield
        VersionTracker._store.clear()

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_add_version_returns_keys(self, tracker, text):
        result = tracker.add_version("doc-x", text)
        _assert_keys(
            result,
            [
                "document_id",
                "version_number",
                "current_score",
                "score_change",
                "diff_summary",
                "total_versions",
            ],
        )

    @pytest.mark.parametrize("text", ALL_INPUTS)
    def test_score_in_range(self, tracker, text):
        result = tracker.add_version("doc-y", text)
        assert 0.0 <= result["current_score"] <= 1.0

    def test_version_numbers_increment(self, tracker):
        first = tracker.add_version("doc-z", AI_TEXT)
        second = tracker.add_version("doc-z", HUMAN_TEXT)
        assert first["version_number"] == 1
        assert second["version_number"] == 2
        assert second["previous_score"] == first["current_score"]

    def test_get_history_after_adds(self, tracker):
        tracker.add_version("doc-h", AI_TEXT)
        tracker.add_version("doc-h", HUMAN_TEXT)
        history = tracker.get_history("doc-h")
        assert history["total_versions"] == 2
        assert len(history["score_trajectory"]) == 2

    def test_get_history_missing_doc(self, tracker):
        assert tracker.get_history("nope") is None


# ---------------------------------------------------------------------------
# BatchProcessor (list-of-texts interface)
# ---------------------------------------------------------------------------


class TestBatchProcessor:
    @pytest.fixture
    def processor(self):
        from app.ml.analyzers.batch_processor import BatchProcessor

        return BatchProcessor()

    def test_returns_documented_keys(self, processor):
        result = processor.process_batch([AI_TEXT, HUMAN_TEXT])
        _assert_keys(
            result,
            [
                "batch_id",
                "total_files",
                "avg_score",
                "score_distribution",
                "flagged_count",
                "results",
            ],
        )

    def test_mixed_input_batch(self, processor):
        texts = [AI_TEXT, HUMAN_TEXT, EMPTY, SINGLE_WORD, LONG_TEXT, SPECIAL_CHARS, NON_ENGLISH]
        result = processor.process_batch(texts)
        assert result["total_files"] == len(texts)
        assert len(result["results"]) == len(texts)
        assert 0.0 <= result["avg_score"] <= 1.0

    def test_scores_sorted_descending(self, processor):
        result = processor.process_batch([HUMAN_TEXT, AI_TEXT, LONG_TEXT])
        scores = [r["ai_score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_classification_labels_valid(self, processor):
        result = processor.process_batch([AI_TEXT, HUMAN_TEXT])
        for r in result["results"]:
            assert r["classification"] in {"ai_generated", "mixed", "human_written"}

    def test_distribution_has_ten_bins(self, processor):
        result = processor.process_batch([AI_TEXT, HUMAN_TEXT])
        assert len(result["score_distribution"]) == 10

    def test_filename_padding(self, processor):
        """Fewer filenames than texts get padded, not dropped."""
        result = processor.process_batch([AI_TEXT, HUMAN_TEXT], filenames=["only_one.txt"])
        assert result["total_files"] == 2

    def test_empty_batch(self, processor):
        result = processor.process_batch([])
        assert result["total_files"] == 0
        assert result["results"] == []
