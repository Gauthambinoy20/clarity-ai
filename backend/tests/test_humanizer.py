"""
Unit tests for the humanizer subsystem.

The rule-based humanizers (lexical, structural, targeted) run for real on
deterministic seeds. Ollama is an external boundary, so every HTTP call to it
is mocked -- nothing here touches the network. The pipeline tests check that
the layers compose and that the whole thing degrades cleanly when Ollama is
down.
"""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import AI_TEXT, HUMAN_TEXT

from app.ml.humanizer.lexical_humanizer import LexicalHumanizer
from app.ml.humanizer.structural_humanizer import StructuralHumanizer
from app.ml.humanizer.ollama_humanizer import OllamaHumanizer
from app.ml.humanizer.pipeline import AdversarialHumanizationPipeline, HumanizationResult


EDGE_INPUTS = ["", "   ", "word", "café déjà-vu naïve résumé", "First. Second! Third?"]


# ---------------------------------------------------------------------------
# Fake Ollama HTTP boundary
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=httpx.Request("POST", "http://x"), response=self
            )


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient.

    ``behaviour`` is either a _FakeResponse or an exception instance to raise.
    """

    def __init__(self, behaviour, *args, **kwargs):
        self._behaviour = behaviour

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def _act(self):
        if isinstance(self._behaviour, Exception):
            raise self._behaviour
        return self._behaviour

    async def post(self, *args, **kwargs):
        return await self._act()

    async def get(self, *args, **kwargs):
        return await self._act()


def _patch_ollama(monkeypatch, behaviour):
    """Make httpx.AsyncClient (as used by the humanizer) return ``behaviour``."""
    monkeypatch.setattr(
        "app.ml.humanizer.ollama_humanizer.httpx.AsyncClient",
        lambda *a, **k: _FakeAsyncClient(behaviour),
    )


# ---------------------------------------------------------------------------
# LexicalHumanizer
# ---------------------------------------------------------------------------


class TestLexicalHumanizer:
    @pytest.fixture
    def lex(self):
        return LexicalHumanizer(seed=7)

    def test_returns_string(self, lex):
        out = lex.humanize(AI_TEXT)
        assert isinstance(out, str)
        assert out.strip()

    def test_strips_known_buzzwords(self, lex):
        out = lex.humanize("We utilize and leverage comprehensive synergy.")
        lowered = out.lower()
        assert "utilize" not in lowered
        assert "leverage" not in lowered

    def test_buzzword_preserves_leading_capital(self, lex):
        out = lex.humanize("Utilize this.")
        # The replacement should keep an upper-case first letter.
        assert out[0].isupper()

    def test_contractions_injected_when_certain(self):
        # Probability 1.0 forces every contraction to fire.
        lex = LexicalHumanizer(contraction_probability=1.0, seed=1)
        out = lex.humanize("It is clear they are here and we are not leaving.")
        assert "it's" in out.lower() or "they're" in out.lower()

    def test_contractions_skipped_when_probability_zero(self):
        lex = LexicalHumanizer(contraction_probability=0.0, seed=1)
        out = lex.humanize("It is here.")
        assert "it's" not in out.lower()

    def test_ai_phrase_pattern_rewritten(self, lex):
        out = lex.humanize("In today's rapidly evolving world, things change.")
        assert "rapidly evolving world" not in out.lower()

    def test_human_text_stays_sane(self, lex):
        out = lex.humanize(HUMAN_TEXT)
        # Roughly the same size -- lexical swaps don't balloon the text.
        assert 0.5 * len(HUMAN_TEXT) < len(out) < 2.0 * len(HUMAN_TEXT)

    @pytest.mark.parametrize("text", EDGE_INPUTS)
    def test_survives_edge_inputs(self, lex, text):
        out = lex.humanize(text)
        assert isinstance(out, str)

    def test_deterministic_with_seed(self):
        a = LexicalHumanizer(seed=42).humanize(AI_TEXT)
        b = LexicalHumanizer(seed=42).humanize(AI_TEXT)
        assert a == b


# ---------------------------------------------------------------------------
# StructuralHumanizer  (spaCy runs for real)
# ---------------------------------------------------------------------------


class TestStructuralHumanizer:
    @pytest.fixture
    def struct(self):
        return StructuralHumanizer(seed=3)

    def test_returns_non_empty_string(self, struct):
        out = struct.humanize(AI_TEXT, style="academic")
        assert isinstance(out, str)
        assert out.strip()

    @pytest.mark.parametrize("style", ["academic", "casual", "professional", "creative"])
    def test_all_styles_produce_text(self, struct, style):
        out = struct.humanize(AI_TEXT, style=style)
        assert out.strip()

    def test_empty_input_returned_unchanged(self, struct):
        assert struct.humanize("") == ""
        assert struct.humanize("   ") == "   "

    def test_single_word_survives(self, struct):
        out = struct.humanize("Hello")
        assert isinstance(out, str)

    def test_unicode_preserved(self, struct):
        out = struct.humanize("Café déjà-vu. Naïve résumé writing.", style="casual")
        assert isinstance(out, str)
        assert out.strip()

    def test_fallback_without_spacy_still_works(self, struct):
        # Force the spaCy-unavailable branch.
        struct._nlp = None
        out = struct._fallback_humanize(
            "This is one sentence. Here is another. And a third one too.", "casual"
        )
        assert out.strip()

    def test_paragraph_breaks_for_long_text(self, struct):
        # Concatenate enough sentences to span multiple paragraphs.
        text = " ".join(["This is a fairly ordinary test sentence here."] * 12)
        out = struct.humanize(text, style="academic")
        assert "\n\n" in out


# ---------------------------------------------------------------------------
# TargetedHumanizer  (real sentence-level detector under the hood)
# ---------------------------------------------------------------------------


class TestTargetedHumanizer:
    def test_sentence_split_drops_short_fragments(self):
        from app.ml.humanizer.targeted_humanizer import TargetedHumanizer

        th = TargetedHumanizer(seed=1)
        parts = th._sentence_split("A real sentence here. Hi. Another full one here.")
        # "Hi." is under 10 chars and should be dropped.
        assert all(len(p) > 10 for p in parts)

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_result(self):
        from app.ml.humanizer.targeted_humanizer import TargetedHumanizer

        th = TargetedHumanizer(seed=1)
        result = await th.humanize("")
        assert result.humanized_text == ""
        assert result.sentences_modified == 0
        assert result.sentences_preserved == 0

    @pytest.mark.asyncio
    async def test_normal_text_returns_result_shape(self):
        from app.ml.humanizer.targeted_humanizer import TargetedHumanizer

        th = TargetedHumanizer(seed=1)
        result = await th.humanize(AI_TEXT, style="academic")
        assert isinstance(result.humanized_text, str)
        assert result.humanized_text.strip()
        # Every original sentence is either rewritten or preserved.
        total = result.sentences_modified + result.sentences_preserved
        assert total >= 1
        assert len(result.modifications) == result.sentences_modified

    def test_humanize_single_sentence_collapses_paragraphs(self):
        from app.ml.humanizer.targeted_humanizer import TargetedHumanizer

        th = TargetedHumanizer(seed=1)
        out = th._humanize_sentence("We utilize comprehensive frameworks to optimize outcomes.")
        assert "\n\n" not in out
        assert out.strip()


# ---------------------------------------------------------------------------
# OllamaHumanizer  (HTTP boundary mocked)
# ---------------------------------------------------------------------------


class TestOllamaHumanizer:
    @pytest.fixture
    def ollama(self):
        return OllamaHumanizer(timeout=5)

    @pytest.mark.asyncio
    async def test_empty_text_short_circuits(self, ollama, monkeypatch):
        # Should never even build an HTTP client for empty input.
        _patch_ollama(monkeypatch, httpx.ConnectError("should not be called"))
        assert await ollama.humanize("") == ""

    @pytest.mark.asyncio
    async def test_server_up_returns_rewrite(self, ollama, monkeypatch):
        _patch_ollama(monkeypatch, _FakeResponse(200, {"response": "  rewritten text  "}))
        out = await ollama.humanize("original text", style="casual")
        assert out == "rewritten text"

    @pytest.mark.asyncio
    async def test_empty_model_response_falls_back_to_original(self, ollama, monkeypatch):
        _patch_ollama(monkeypatch, _FakeResponse(200, {"response": "   "}))
        out = await ollama.humanize("original text")
        assert out == "original text"

    @pytest.mark.asyncio
    async def test_server_down_returns_original_with_note(self, ollama, monkeypatch):
        _patch_ollama(monkeypatch, httpx.ConnectError("connection refused"))
        out = await ollama.humanize("original text")
        assert out.startswith("original text")
        assert "unavailable" in out.lower()

    @pytest.mark.asyncio
    async def test_timeout_returns_original_with_note(self, ollama, monkeypatch):
        _patch_ollama(monkeypatch, httpx.TimeoutException("too slow"))
        out = await ollama.humanize("original text")
        assert out.startswith("original text")
        assert "timed out" in out.lower()

    @pytest.mark.asyncio
    async def test_http_error_returns_original_with_note(self, ollama, monkeypatch):
        _patch_ollama(monkeypatch, _FakeResponse(500, {}))
        out = await ollama.humanize("original text")
        assert out.startswith("original text")
        assert "error" in out.lower()

    @pytest.mark.asyncio
    async def test_unknown_style_defaults_to_academic(self, ollama, monkeypatch):
        # Just needs to not blow up on an unrecognised style.
        _patch_ollama(monkeypatch, _FakeResponse(200, {"response": "ok"}))
        out = await ollama.humanize("text", style="nonsense-style")
        assert out == "ok"

    @pytest.mark.asyncio
    async def test_is_available_true_on_200(self, ollama, monkeypatch):
        _patch_ollama(monkeypatch, _FakeResponse(200, {}))
        assert await ollama.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_false_when_down(self, ollama, monkeypatch):
        _patch_ollama(monkeypatch, httpx.ConnectError("nope"))
        assert await ollama.is_available() is False


# ---------------------------------------------------------------------------
# Pipeline helpers (no network, no models)
# ---------------------------------------------------------------------------


class TestPipelineHelpers:
    @pytest.fixture
    def pipe(self):
        return AdversarialHumanizationPipeline()

    def test_heuristic_score_in_range(self, pipe):
        for text in (AI_TEXT, HUMAN_TEXT, "short"):
            score = pipe._heuristic_ai_score(text)
            assert 0.0 <= score <= 1.0

    def test_heuristic_score_empty_is_neutral(self, pipe):
        assert pipe._heuristic_ai_score("") == 0.5

    def test_word_overlap_identical_is_one(self, pipe):
        assert pipe._word_overlap_similarity("the cat sat", "the cat sat") == 1.0

    def test_word_overlap_disjoint_is_zero(self, pipe):
        assert pipe._word_overlap_similarity("alpha beta", "gamma delta") == 0.0

    def test_word_overlap_empty_is_zero(self, pipe):
        assert pipe._word_overlap_similarity("", "anything") == 0.0


# ---------------------------------------------------------------------------
# Pipeline end-to-end with Ollama mocked down
# ---------------------------------------------------------------------------


class TestPipelineComposition:
    @pytest.mark.asyncio
    async def test_already_below_target_skips_processing(self, monkeypatch):
        pipe = AdversarialHumanizationPipeline(target_ai_score=0.9)
        # Force a low baseline so the early-exit path triggers.
        monkeypatch.setattr(pipe, "_score_text", _const_score(0.05))

        result = await pipe.humanize("Some ordinary text to leave alone.")
        assert isinstance(result, HumanizationResult)
        assert result.iterations == 0
        assert result.targets_met is True
        assert result.humanized_text == result.original_text

    @pytest.mark.asyncio
    async def test_pipeline_runs_layers_when_ollama_down(self, monkeypatch):
        # Ollama unreachable -> the LLM layer degrades to original-with-note,
        # but lexical + structural layers still run and the pipeline finishes.
        _patch_ollama(monkeypatch, httpx.ConnectError("down"))

        pipe = AdversarialHumanizationPipeline(target_ai_score=0.10, max_iterations=1)
        # Keep the score above target so layers actually execute, and avoid
        # loading the real detection ensemble / sentence-transformers.
        monkeypatch.setattr(pipe, "_score_text", _const_score(0.6))
        monkeypatch.setattr(pipe, "_compute_similarity", lambda a, b: 0.95)
        monkeypatch.setattr(pipe, "_check_plagiarism", _const_score(0.0))

        result = await pipe.humanize(AI_TEXT, style="academic")
        assert isinstance(result, HumanizationResult)
        # baseline + lexical + structural + ollama stages were recorded.
        stages = [s["stage"] for s in result.score_timeline]
        assert stages[:4] == ["baseline", "lexical", "structural", "ollama"]
        assert result.humanized_text.strip()

    @pytest.mark.asyncio
    async def test_meaning_drop_stops_adversarial_loop(self, monkeypatch):
        _patch_ollama(monkeypatch, _FakeResponse(200, {"response": "rewritten body"}))

        pipe = AdversarialHumanizationPipeline(
            target_ai_score=0.10, max_iterations=3, similarity_threshold=0.80
        )
        monkeypatch.setattr(pipe, "_score_text", _const_score(0.6))
        # Similarity below the threshold -> loop should bail after one pass.
        monkeypatch.setattr(pipe, "_compute_similarity", lambda a, b: 0.1)
        monkeypatch.setattr(pipe, "_check_plagiarism", _const_score(0.0))

        result = await pipe.humanize(AI_TEXT, style="casual")
        assert result.iterations == 1


def _const_score(value):
    """Return an async function that ignores its args and yields ``value``."""

    async def _inner(*args, **kwargs):
        return value

    return _inner
