"""
Unit tests for individual ML detectors.

These tests exercise the detector logic directly without loading large
transformer models.  Detectors that rely only on statistical / linguistic
computation (no GPU) are fully exercised.  Model-heavy detectors are tested
for interface conformance using a short input that triggers the
`_empty_result` fallback path.
"""

from __future__ import annotations

import math
import pytest

from tests.conftest import AI_TEXT, HUMAN_TEXT, SHORT_TEXT


# ---------------------------------------------------------------------------
# BaseDetector helpers
# ---------------------------------------------------------------------------


class TestBaseDetectorHelpers:
    """Tests for shared utility methods on BaseDetector."""

    def _make_detector(self):
        """Return a concrete subclass of BaseDetector for testing helpers."""
        from app.ml.detectors.base import BaseDetector

        class _Dummy(BaseDetector):
            async def analyze(self, text: str) -> dict:
                return {}

        return _Dummy()

    def test_sigmoid_zero(self):
        det = self._make_detector()
        assert abs(det._sigmoid(0.0) - 0.5) < 1e-6

    def test_sigmoid_large_positive(self):
        det = self._make_detector()
        assert det._sigmoid(100) > 0.9999

    def test_sigmoid_large_negative(self):
        det = self._make_detector()
        assert det._sigmoid(-100) < 0.0001

    def test_clamp_within_range(self):
        det = self._make_detector()
        assert det._clamp(0.5) == 0.5

    def test_clamp_below_zero(self):
        det = self._make_detector()
        assert det._clamp(-0.5) == 0.0

    def test_clamp_above_one(self):
        det = self._make_detector()
        assert det._clamp(1.5) == 1.0

    def test_compute_confidence_high(self):
        det = self._make_detector()
        assert det._compute_confidence([0.9, 0.85, 0.88]) == "high"

    def test_compute_confidence_low_empty(self):
        det = self._make_detector()
        assert det._compute_confidence([]) == "low"

    def test_empty_result_structure(self):
        det = self._make_detector()
        result = det._empty_result("test_signal")
        assert result["signal"] == "test_signal"
        assert result["ai_probability"] == 0.5
        assert result["confidence"] == "low"
        assert "error" in result


# ---------------------------------------------------------------------------
# EntropyAnalyzerDetector — purely statistical, no model required
# ---------------------------------------------------------------------------


class TestEntropyAnalyzerDetector:
    """Tests for the entropy-based AI detector."""

    @pytest.fixture
    def detector(self):
        from app.ml.detectors.entropy_analyzer import EntropyAnalyzerDetector

        return EntropyAnalyzerDetector()

    @pytest.mark.asyncio
    async def test_short_text_returns_empty_result(self, detector):
        result = await detector.analyze(SHORT_TEXT)
        assert result["ai_probability"] == 0.5
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ai_text_returns_valid_schema(self, detector):
        result = await detector.analyze(AI_TEXT)
        assert "signal" in result
        assert "ai_probability" in result
        assert "confidence" in result
        assert result["signal"] == "entropy_analyzer"

    @pytest.mark.asyncio
    async def test_ai_probability_in_range(self, detector):
        result = await detector.analyze(AI_TEXT)
        assert 0.0 <= result["ai_probability"] <= 1.0

    @pytest.mark.asyncio
    async def test_details_present_for_valid_text(self, detector):
        result = await detector.analyze(AI_TEXT)
        assert "details" in result
        details = result["details"]
        assert "char_entropy" in details
        assert "word_entropy" in details
        assert "buzzword_density" in details

    @pytest.mark.asyncio
    async def test_buzzword_heavy_text_scores_higher(self, detector):
        """AI text loaded with buzzwords should score higher than natural text."""
        ai_result = await detector.analyze(AI_TEXT)
        human_result = await detector.analyze(HUMAN_TEXT)
        # AI text has far more buzzwords — its score should be >= human score
        assert ai_result["ai_probability"] >= human_result["ai_probability"]

    def test_char_entropy_non_empty(self, detector):
        entropy = detector._char_entropy("hello world")
        assert entropy > 0

    def test_char_entropy_empty(self, detector):
        assert detector._char_entropy("") == 0.0

    def test_word_entropy_uniform(self, detector):
        """A text with all identical words has zero word entropy."""
        assert detector._word_entropy(["word"] * 10) == 0.0

    def test_bigram_entropy_single_word(self, detector):
        """Single word produces no bigrams -> 0 entropy."""
        assert detector._bigram_entropy(["hello"]) == 0.0


# ---------------------------------------------------------------------------
# VocabularyRichnessDetector — purely statistical, no model required
# ---------------------------------------------------------------------------


class TestVocabularyRichnessDetector:
    """Tests for the vocabulary-richness detector."""

    @pytest.fixture
    def detector(self):
        from app.ml.detectors.vocabulary_richness import VocabularyRichnessDetector

        return VocabularyRichnessDetector()

    @pytest.mark.asyncio
    async def test_short_text_returns_empty_result(self, detector):
        result = await detector.analyze(SHORT_TEXT)
        assert result["ai_probability"] == 0.5
        assert "error" in result

    @pytest.mark.asyncio
    async def test_valid_text_schema(self, detector):
        result = await detector.analyze(AI_TEXT)
        assert result["signal"] == "vocabulary_richness"
        assert 0.0 <= result["ai_probability"] <= 1.0
        assert result["confidence"] in {"low", "medium", "high"}

    @pytest.mark.asyncio
    async def test_details_keys_present(self, detector):
        result = await detector.analyze(HUMAN_TEXT)
        details = result.get("details", {})
        for key in ("yules_k", "hapax_ratio", "brunets_w", "honores_h", "sichels_s"):
            assert key in details, f"Missing key: {key}"

    def test_hapax_ratio_all_unique(self, detector):
        tokens = ["a", "b", "c", "d", "e"]
        assert detector._hapax_ratio(tokens) == 1.0

    def test_hapax_ratio_no_unique(self, detector):
        tokens = ["a", "a", "b", "b"]
        assert detector._hapax_ratio(tokens) == 0.0

    def test_hapax_ratio_empty(self, detector):
        assert detector._hapax_ratio([]) == 0.0

    def test_yules_k_empty(self, detector):
        assert detector._yules_k([]) == 0.0

    def test_sichels_s_empty(self, detector):
        assert detector._sichels_s([]) == 0.0


# ---------------------------------------------------------------------------
# RepetitionDetector helpers — no spaCy model needed for static methods
# ---------------------------------------------------------------------------


class TestRepetitionDetectorHelpers:
    """Tests for the repetition detector's static/helper methods."""

    @pytest.fixture
    def detector(self):
        from app.ml.detectors.repetition import RepetitionDetector

        return RepetitionDetector()

    def test_tokenize_basic(self, detector):
        tokens = detector._tokenize("Hello, World!")
        assert tokens == ["hello", "world"]

    def test_ngram_repetition_rate_no_repeats(self, detector):
        tokens = ["a", "b", "c", "d", "e"]
        rate = detector._ngram_repetition_rate(tokens, 2)
        assert rate == 0.0

    def test_ngram_repetition_rate_all_same(self, detector):
        tokens = ["a", "b"] * 5
        rate = detector._ngram_repetition_rate(tokens, 2)
        assert rate > 0.0

    def test_sentence_split_basic(self, detector):
        text = "Hello world. How are you? Fine thanks."
        sentences = detector._sentence_split(text)
        assert len(sentences) == 3

    def test_opener_diversity_all_same(self, detector):
        sentences = ["The cat sat.", "The dog ran.", "The bird flew."]
        diversity = detector._sentence_opener_diversity(sentences)
        # All start with "the <word>" — diversity should be 1/3
        assert abs(diversity - 1 / 3) < 0.01

    def test_opener_diversity_all_different(self, detector):
        sentences = ["Cats are great.", "Dogs are friendly.", "Birds sing well."]
        diversity = detector._sentence_opener_diversity(sentences)
        assert diversity == 1.0

    def test_over_variation_uniform_lengths(self, detector):
        """Sentences of identical length should flag as suspicious (high score)."""
        sentences = ["This is one." for _ in range(5)]
        score = detector._over_variation_score(sentences)
        assert score >= 0.5

    @pytest.mark.asyncio
    async def test_analyze_short_text_returns_empty_result(self, detector):
        result = await detector.analyze(SHORT_TEXT)
        assert result["ai_probability"] == 0.5
        assert "error" in result
