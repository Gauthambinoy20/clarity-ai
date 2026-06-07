"""
Unit tests for the ensemble meta-learner.

These exercise the weighted-average fallback path (no trained model on disk),
the watermark override, defaulting of missing signals, score clamping, the
classification thresholds, and the interpretability metadata. Signal dicts
are built by hand so the tests stay deterministic.
"""

from __future__ import annotations

import pytest

from app.ml.ensemble.meta_learner import (
    DEFAULT_WEIGHTS,
    SIGNAL_NAMES,
    EnsembleMetaLearner,
    _extract_feature_vector,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _signals(prob: float, **overrides) -> dict:
    """Build a signal-results dict where every signal has the same probability.

    Pass overrides as ``name={"ai_probability": ..., ...}`` to tweak one signal.
    """
    results = {name: {"ai_probability": prob, "confidence": "medium"} for name in SIGNAL_NAMES}
    results.update(overrides)
    return results


@pytest.fixture
def learner():
    # No model path -> the candidate pkl almost certainly doesn't exist,
    # so this falls back to the weighted-average estimator.
    return EnsembleMetaLearner(model_path=None)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


class TestFeatureVector:
    def test_length_includes_interaction_terms(self):
        vec = _extract_feature_vector(_signals(0.5))
        # 14 base signals + 3 interaction pairs
        assert len(vec) == len(SIGNAL_NAMES) + 3

    def test_missing_signals_default_to_half(self):
        vec = _extract_feature_vector({})
        base = vec[: len(SIGNAL_NAMES)]
        assert all(p == 0.5 for p in base)

    def test_probabilities_are_clamped(self):
        vec = _extract_feature_vector(
            {"perplexity": {"ai_probability": 5.0}, "burstiness": {"ai_probability": -3.0}}
        )
        assert vec[SIGNAL_NAMES.index("perplexity")] == 1.0
        assert vec[SIGNAL_NAMES.index("burstiness")] == 0.0

    def test_interaction_is_product_of_pair(self):
        vec = _extract_feature_vector(
            _signals(0.5, detectgpt={"ai_probability": 0.8}, binoculars={"ai_probability": 0.5})
        )
        # detectgpt * binoculars is the first interaction term
        assert vec[len(SIGNAL_NAMES)] == pytest.approx(0.8 * 0.5)


# ---------------------------------------------------------------------------
# predict() — overall structure and weighted-average path
# ---------------------------------------------------------------------------


class TestPredictShape:
    def test_returns_all_expected_keys(self, learner):
        out = learner.predict(_signals(0.5))
        for key in (
            "overall_score",
            "classification",
            "confidence",
            "signal_agreement",
            "top_contributing_signals",
            "interpretation",
        ):
            assert key in out

    def test_all_neutral_scores_half(self, learner):
        out = learner.predict(_signals(0.5))
        assert out["overall_score"] == pytest.approx(0.5)

    def test_weighted_average_matches_manual(self, learner):
        # One strong signal, rest neutral -> result is a weighted blend.
        signals = _signals(0.5, perplexity={"ai_probability": 1.0})
        out = learner.predict(signals)
        weights = [DEFAULT_WEIGHTS[s] for s in SIGNAL_NAMES]
        probs = [1.0 if s == "perplexity" else 0.5 for s in SIGNAL_NAMES]
        expected = sum(w * p for w, p in zip(weights, probs)) / sum(weights)
        assert out["overall_score"] == pytest.approx(round(expected, 4))

    def test_empty_signals_default_to_half(self, learner):
        out = learner.predict({})
        assert out["overall_score"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Watermark override
# ---------------------------------------------------------------------------


class TestWatermarkOverride:
    def test_detected_watermark_forces_high_score(self, learner):
        # Every other signal screams "human" but the watermark wins.
        signals = _signals(0.0, watermark={"ai_probability": 0.0, "watermark_detected": True})
        out = learner.predict(signals)
        assert out["overall_score"] == 0.95
        assert out["classification"] == "ai"

    def test_no_watermark_leaves_score_alone(self, learner):
        signals = _signals(0.0, watermark={"ai_probability": 0.0, "watermark_detected": False})
        out = learner.predict(signals)
        assert out["overall_score"] < 0.95

    def test_watermark_mentioned_in_interpretation(self, learner):
        signals = _signals(0.5, watermark={"ai_probability": 0.5, "watermark_detected": True})
        out = learner.predict(signals)
        assert "watermark" in out["interpretation"].lower()


# ---------------------------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------------------------


class TestClassification:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.95, "ai"),
            (0.75, "ai"),
            (0.74, "mixed_or_uncertain"),
            (0.50, "mixed_or_uncertain"),
            (0.31, "mixed_or_uncertain"),
            (0.30, "human"),
            (0.05, "human"),
        ],
    )
    def test_thresholds(self, score, expected):
        assert EnsembleMetaLearner._classify(score) == expected

    def test_high_probs_classify_ai(self, learner):
        out = learner.predict(_signals(0.95))
        assert out["classification"] == "ai"

    def test_low_probs_classify_human(self, learner):
        out = learner.predict(_signals(0.05))
        assert out["classification"] == "human"


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_values_are_valid(self, learner):
        out = learner.predict(_signals(0.5))
        assert out["confidence"] in {"low", "medium", "high"}

    def test_strong_agreement_high_confidence(self, learner):
        # All signals near 0.9 -> low spread, high mean -> high confidence.
        out = learner.predict(_signals(0.9))
        assert out["confidence"] == "high"

    def test_split_signals_low_confidence(self, learner):
        # Half the signals at 0 and half at 1 -> huge spread -> low confidence.
        half = len(SIGNAL_NAMES) // 2
        signals = {}
        for i, name in enumerate(SIGNAL_NAMES):
            signals[name] = {"ai_probability": 0.0 if i < half else 1.0}
        out = learner.predict(signals)
        assert out["confidence"] == "low"


# ---------------------------------------------------------------------------
# Signal agreement
# ---------------------------------------------------------------------------


class TestSignalAgreement:
    def test_perfect_agreement_is_one(self, learner):
        out = learner.predict(_signals(0.8))
        assert out["signal_agreement"] == pytest.approx(1.0)

    def test_disagreement_lowers_agreement(self, learner):
        half = len(SIGNAL_NAMES) // 2
        signals = {
            name: {"ai_probability": 0.0 if i < half else 1.0}
            for i, name in enumerate(SIGNAL_NAMES)
        }
        out = learner.predict(signals)
        assert out["signal_agreement"] < 0.1

    def test_agreement_in_unit_range(self, learner):
        out = learner.predict(_signals(0.3))
        assert 0.0 <= out["signal_agreement"] <= 1.0

    def test_empty_probs_agreement_is_zero(self):
        import numpy as np

        assert EnsembleMetaLearner._signal_agreement(np.array([])) == 0.0


# ---------------------------------------------------------------------------
# Top contributing signals
# ---------------------------------------------------------------------------


class TestTopContributingSignals:
    def test_returns_at_most_five(self, learner):
        out = learner.predict(_signals(0.9))
        assert len(out["top_contributing_signals"]) == 5

    def test_entries_have_expected_shape(self, learner):
        out = learner.predict(_signals(0.9))
        entry = out["top_contributing_signals"][0]
        assert set(entry) == {"signal", "ai_probability", "confidence", "contribution"}

    def test_sorted_by_contribution_descending(self, learner):
        out = learner.predict(_signals(0.9))
        contribs = [s["contribution"] for s in out["top_contributing_signals"]]
        assert contribs == sorted(contribs, reverse=True)

    def test_strong_high_weight_signal_ranks_top(self, learner):
        # detectgpt has one of the highest weights; push it to the extreme.
        signals = _signals(0.5, detectgpt={"ai_probability": 1.0, "confidence": "high"})
        out = learner.predict(signals)
        assert out["top_contributing_signals"][0]["signal"] == "detectgpt"

    def test_neutral_signals_contribute_nothing(self, learner):
        # At 0.5 every signal is exactly undecided -> zero contribution.
        out = learner.predict(_signals(0.5))
        assert all(s["contribution"] == 0.0 for s in out["top_contributing_signals"])


# ---------------------------------------------------------------------------
# Interpretation text
# ---------------------------------------------------------------------------


class TestInterpretation:
    @pytest.mark.parametrize("prob", [0.05, 0.5, 0.95])
    def test_non_empty_for_each_class(self, learner, prob):
        out = learner.predict(_signals(prob))
        assert isinstance(out["interpretation"], str)
        assert out["interpretation"].strip()

    def test_ai_phrasing(self, learner):
        out = learner.predict(_signals(0.95))
        assert "AI-generated" in out["interpretation"]

    def test_human_phrasing(self, learner):
        out = learner.predict(_signals(0.05))
        assert "human-written" in out["interpretation"]

    def test_uncertain_phrasing(self, learner):
        out = learner.predict(_signals(0.5))
        assert "uncertain" in out["interpretation"].lower()

    def test_mentions_top_signals(self, learner):
        out = learner.predict(_signals(0.9))
        # The lead names the three most influential signals.
        assert "influential signals" in out["interpretation"]


# ---------------------------------------------------------------------------
# Score clamping
# ---------------------------------------------------------------------------


class TestScoreClamping:
    def test_score_stays_in_unit_range(self, learner):
        for prob in (0.0, 0.25, 0.5, 0.75, 1.0):
            out = learner.predict(_signals(prob))
            assert 0.0 <= out["overall_score"] <= 1.0

    def test_out_of_range_inputs_are_clamped(self, learner):
        # Feature extraction clamps each prob, so the blend stays valid.
        out = learner.predict(_signals(0.5, perplexity={"ai_probability": 99.0}))
        assert 0.0 <= out["overall_score"] <= 1.0
