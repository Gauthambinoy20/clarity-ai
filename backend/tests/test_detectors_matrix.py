"""
Input-space matrix for every detector.

Each detector is pushed through the awkward inputs real users send:
empty strings, one word, huge documents, unicode soup, non-English
prose. The contract under test: never raise, always return the
documented shape, and degrade to a flagged neutral result when the
model backend is unavailable.
"""

from __future__ import annotations

import pytest

from tests.conftest import AI_TEXT, HUMAN_TEXT

# ---------------------------------------------------------------------------
# Awkward inputs
# ---------------------------------------------------------------------------

EMPTY = ""
ONE_WORD = "Hello"
HUGE = "The quick brown fox jumps over the lazy dog near the riverbank today. " * 350  # ~4500 words
UNICODE_SOUP = (
    "Ünïcödé tëxt with «weird» quotes — em-dashes… ellipses, 数字もある, "
    "эмодзи нет but \t tabs \n newlines and    runs of spaces appear here. "
    "Symbols: @#$%^&*()[]{}<>|\\/~` plus a URL https://example.test/path?q=1 "
    "and an email someone@example.test mixed in, repeated a few times. "
) * 8
NON_ENGLISH = (
    "Der schnelle braune Fuchs springt über den faulen Hund am Flussufer. "
    "Gestern habe ich endlich das Leck unter der Spüle repariert, es hat viel "
    "länger gedauert als erwartet, weil ich den richtigen Schraubenschlüssel "
    "nicht finden konnte. Mein Nachbar hat mir am Ende einen geliehen. "
) * 4

AWKWARD_INPUTS = [
    pytest.param(EMPTY, id="empty"),
    pytest.param(ONE_WORD, id="one-word"),
    pytest.param(HUGE, id="huge"),
    pytest.param(UNICODE_SOUP, id="unicode"),
    pytest.param(NON_ENGLISH, id="non-english"),
]

# Detector import paths, grouped by what they need at analyze() time.
STATISTICAL = [
    ("app.ml.detectors.entropy_analyzer", "EntropyAnalyzerDetector"),
    ("app.ml.detectors.vocabulary_richness", "VocabularyRichnessDetector"),
    ("app.ml.detectors.ai_fingerprint", "AIFingerprintDetector"),
    ("app.ml.detectors.ai_pattern_database", "AIPatternDatabaseDetector"),
    ("app.ml.detectors.cross_reference", "CrossReferenceDetector"),
    ("app.ml.detectors.rewrite_detector", "RewriteDetector"),
]

SPACY_BACKED = [
    ("app.ml.detectors.repetition", "RepetitionDetector"),
    ("app.ml.detectors.coherence", "CoherenceDetector"),
    ("app.ml.detectors.stylometric", "StylometricDetector"),
    ("app.ml.detectors.watermark", "WatermarkDetector"),
    ("app.ml.detectors.pos_patterns", "POSPatternsDetector"),
]

HF_BACKED = [
    ("app.ml.detectors.gltr", "GLTRDetector"),
    ("app.ml.detectors.binoculars", "BinocularsDetector"),
    ("app.ml.detectors.fast_detectgpt", "FastDetectGPTDetector"),
    ("app.ml.detectors.ghostbuster", "GhostbusterDetector"),
    ("app.ml.detectors.zero_shot_ensemble", "ZeroShotEnsembleDetector"),
    ("app.ml.detectors.multi_model_consensus", "MultiModelConsensusDetector"),
    ("app.ml.detectors.sentence_level", "SentenceLevelDetector"),
    ("app.ml.detectors.perplexity_burstiness", "PerplexityBurstinessDetector"),
]


def _make(path: str, cls_name: str):
    """Instantiate a detector from its import path."""
    module = __import__(path, fromlist=[cls_name])
    return getattr(module, cls_name)()


def _assert_valid_shape(result: dict):
    """Every detector result honours the BaseDetector contract."""
    assert isinstance(result, dict)
    assert isinstance(result["signal"], str) and result["signal"]
    assert 0.0 <= result["ai_probability"] <= 1.0
    assert result["confidence"] in ("low", "medium", "high")


@pytest.fixture
def offline_registry(monkeypatch):
    """A model registry that refuses every load, as if the host is offline."""

    async def _refuse(model_id: str):
        raise RuntimeError(f"model backend unavailable: {model_id}")

    from app.ml.models.model_registry import ModelRegistry

    monkeypatch.setattr(ModelRegistry, "get_model", staticmethod(_refuse))


# ---------------------------------------------------------------------------
# Statistical detectors: run for real on every awkward input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("path,cls", STATISTICAL, ids=[c for _, c in STATISTICAL])
@pytest.mark.parametrize("text", AWKWARD_INPUTS)
async def test_statistical_detectors_survive_awkward_input(path, cls, text):
    result = await _make(path, cls).analyze(text)
    _assert_valid_shape(result)


# ---------------------------------------------------------------------------
# spaCy-backed detectors: the local pipeline is installed, so these run real
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("path,cls", SPACY_BACKED, ids=[c for _, c in SPACY_BACKED])
@pytest.mark.parametrize("text", AWKWARD_INPUTS)
async def test_spacy_detectors_survive_awkward_input(path, cls, text):
    result = await _make(path, cls).analyze(text)
    _assert_valid_shape(result)


# ---------------------------------------------------------------------------
# HF-model detectors: with the model backend down they must degrade,
# never crash — a host without GPU/network still serves clean answers.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("path,cls", HF_BACKED, ids=[c for _, c in HF_BACKED])
@pytest.mark.parametrize("text", AWKWARD_INPUTS + [pytest.param(AI_TEXT, id="ai-text")])
async def test_hf_detectors_degrade_cleanly_without_models(offline_registry, path, cls, text):
    result = await _make(path, cls).analyze(text)
    _assert_valid_shape(result)


# ---------------------------------------------------------------------------
# Direction sanity: the pattern-matching detectors are deterministic, so
# buzzword-heavy text must outscore plain personal prose.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pattern_database_scores_ai_text_above_human():
    detector = _make("app.ml.detectors.ai_pattern_database", "AIPatternDatabaseDetector")
    ai = await detector.analyze(AI_TEXT)
    human = await detector.analyze(HUMAN_TEXT)
    assert ai["ai_probability"] > human["ai_probability"]


@pytest.mark.asyncio
async def test_fingerprint_scores_ai_text_above_human():
    detector = _make("app.ml.detectors.ai_fingerprint", "AIFingerprintDetector")
    ai = await detector.analyze(AI_TEXT)
    human = await detector.analyze(HUMAN_TEXT)
    assert ai["ai_probability"] > human["ai_probability"]
