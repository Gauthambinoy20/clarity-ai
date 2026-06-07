"""
Regression tests for the detection route's ML wiring.

The original code imported detector class names that never existed, fell
back to an empty roster, and served hardcoded 0.5 "results" — these tests
pin the wiring so that bug can never come back silently.
"""

from __future__ import annotations

import pytest

from app.api.routes import detection
from app.ml.detectors.base import BaseDetector


# ---------------------------------------------------------------------------
# Detector roster
# ---------------------------------------------------------------------------


def test_all_roster_has_fourteen_real_detectors():
    """The full roster must import and instantiate 14 real detectors."""
    detection._detectors_cache.clear()
    roster = detection._get_detectors()
    assert len(roster["all"]) == 14
    assert all(isinstance(d, BaseDetector) for d in roster["all"])


def test_fast_roster_is_a_subset_of_all():
    """Fast mode reuses three instances from the full roster — no copies."""
    detection._detectors_cache.clear()
    roster = detection._get_detectors()
    assert len(roster["fast"]) == 3
    assert all(any(f is a for a in roster["all"]) for f in roster["fast"])


def test_roster_covers_the_strong_signals():
    """The signals the score combiner up-weights must actually be present."""
    detection._detectors_cache.clear()
    roster = detection._get_detectors()
    names = {type(d).__name__ for d in roster["all"]}
    assert {
        "PerplexityBurstinessDetector",
        "GLTRDetector",
        "ZeroShotEnsembleDetector",
        "AIFingerprintDetector",
    } <= names


def test_ensemble_loads():
    """The meta-learner import path must resolve to the real class."""
    ensemble = detection._get_ensemble()
    assert type(ensemble).__name__ == "EnsembleMetaLearner"


def test_sentence_analyzer_loads():
    """The sentence analyzer import path must resolve to the real class."""
    analyzer = detection._get_sentence_analyzer()
    assert type(analyzer).__name__ == "SentenceLevelDetector"


# ---------------------------------------------------------------------------
# _run_detector: async detectors must be awaited, not thrown in a thread
# ---------------------------------------------------------------------------


class _DummyDetector:
    # Pose as a signal the ensemble knows so the score actually moves.
    signal_name = "entropy_analyzer"

    async def analyze(self, text: str) -> dict:
        return {"signal": "entropy_analyzer", "ai_probability": 1.0, "confidence": "high"}


class _ExplodingDetector:
    signal_name = "boom"

    async def analyze(self, text: str) -> dict:
        raise RuntimeError("model fell over")


@pytest.mark.asyncio
async def test_run_detector_awaits_async_analyze():
    """An async analyze() must come back as a dict, not a coroutine."""
    result = await detection._run_detector(_DummyDetector(), "some text")
    assert result == {
        "signal": "entropy_analyzer",
        "ai_probability": 1.0,
        "confidence": "high",
    }


@pytest.mark.asyncio
async def test_run_detector_flags_failures_as_neutral():
    """A crashing detector degrades to a flagged 0.5, never an exception."""
    result = await detection._run_detector(_ExplodingDetector(), "some text")
    assert result["ai_probability"] == 0.5
    assert result["confidence"] == "low"
    assert "model fell over" in result["error"]


# ---------------------------------------------------------------------------
# Signal-name bridge between detectors and the meta-learner
# ---------------------------------------------------------------------------


def test_bridge_splits_perplexity_burstiness_into_two_features():
    signals = [
        {
            "signal": "perplexity_burstiness",
            "ai_probability": 0.7,
            "sub_scores": {"ppl_score": 0.8, "cv_score": 0.6},
        }
    ]
    bridged = detection._bridge_signals(signals)
    assert bridged["perplexity"]["ai_probability"] == 0.8
    assert bridged["burstiness"]["ai_probability"] == 0.6


def test_bridge_translates_renamed_signals():
    signals = [
        {"signal": "entropy_analyzer", "ai_probability": 0.4},
        {"signal": "fast_detectgpt", "ai_probability": 0.6},
        {"signal": "pos_patterns", "ai_probability": 0.3},
    ]
    bridged = detection._bridge_signals(signals)
    assert bridged["entropy"]["ai_probability"] == 0.4
    assert bridged["detectgpt"]["ai_probability"] == 0.6
    assert bridged["pos_pattern"]["ai_probability"] == 0.3


def test_bridge_drops_signals_the_ensemble_does_not_know():
    bridged = detection._bridge_signals([{"signal": "gltr", "ai_probability": 0.9}])
    assert bridged == {}


# ---------------------------------------------------------------------------
# Score combination via the ensemble's dict-based API
# ---------------------------------------------------------------------------


class _FakeEnsemble:
    def predict(self, signal_results: dict) -> dict:
        assert isinstance(signal_results, dict)  # the dict API, not a list
        return {"overall_score": 0.83, "classification": "ai_generated"}


class _BrokenEnsemble:
    def predict(self, signal_results: dict) -> dict:
        raise ValueError("bad feature vector")


def test_combine_scores_uses_ensemble_prediction():
    signals = [{"signal": "entropy_analyzer", "ai_probability": 0.4, "confidence": "low"}]
    assert detection._combine_scores(signals, _FakeEnsemble()) == 0.83


def test_combine_scores_falls_back_to_weighted_average():
    signals = [
        {"signal": "gltr", "ai_probability": 0.9, "confidence": "high"},
        {"signal": "repetition", "ai_probability": 0.3, "confidence": "low"},
    ]
    # gltr weight 2.0, repetition 1.0 -> (0.9*2 + 0.3) / 3 = 0.7
    assert detection._combine_scores(signals, _BrokenEnsemble()) == pytest.approx(0.7)


def test_combine_scores_neutral_on_no_signals():
    assert detection._combine_scores([], _FakeEnsemble()) == 0.5


# ---------------------------------------------------------------------------
# End-to-end: /detect must serve real detector output, never stubs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_returns_wired_signals(client, monkeypatch):
    """With the roster patched to dummies, the response must carry their
    signals — proving the route consumes whatever the roster provides and
    has no hardcoded stub path left."""
    monkeypatch.setitem(detection._detectors_cache, "all", [_DummyDetector()])
    monkeypatch.setitem(detection._detectors_cache, "fast", [_DummyDetector()])

    resp = await client.post(
        "/api/v1/detect",
        json={
            "text": " ".join(["word"] * 60),
            "options": {
                "include_sentence_scores": False,
                "include_gltr_data": False,
                "include_attribution": False,
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [s["signal"] for s in body["signals"]] == ["entropy_analyzer"]
    # A confident signal must move the ensemble off dead-neutral — the old
    # stub path always produced exactly 0.5.
    assert body["overall_score"] > 0.5


@pytest.mark.asyncio
async def test_detect_returns_503_when_roster_is_empty(client, monkeypatch):
    """An empty roster is a deployment bug: loud 503, never fake scores."""
    monkeypatch.setitem(detection._detectors_cache, "all", [])
    monkeypatch.setitem(detection._detectors_cache, "fast", [])

    resp = await client.post("/api/v1/detect", json={"text": " ".join(["word"] * 60)})
    assert resp.status_code == 503
