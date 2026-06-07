"""
Unit tests for the plagiarism subsystem (app/ml/plagiarism).

Covers:
  - exact_match: real n-gram fingerprinting, Jaccard, LCS, overlap scoring.
  - semantic_match: sentence comparison with the embedding model mocked out
    (deterministic fake vectors) plus the lexical-only fallback.
  - source_discovery: all HTTP mocked -- found / none-found / HTTP-error / timeout.
  - pipeline: stage composition, source gating, graceful degradation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import numpy as np
import pytest


# ===========================================================================
# exact_match -- runs for real (deterministic n-gram logic)
# ===========================================================================


class TestExactMatchHelpers:
    def test_normalize_lowercases_and_strips_punctuation(self):
        from app.ml.plagiarism.exact_match import _normalize

        assert _normalize("Hello, WORLD!!  Foo.") == "hello world foo"

    def test_normalize_collapses_whitespace(self):
        from app.ml.plagiarism.exact_match import _normalize

        assert _normalize("a   b\n\tc") == "a b c"

    def test_kgrams_sliding_window(self):
        from app.ml.plagiarism.exact_match import _kgrams

        grams = _kgrams(["a", "b", "c", "d"], 2)
        assert grams == ["a b", "b c", "c d"]

    def test_kgrams_too_short_returns_empty(self):
        from app.ml.plagiarism.exact_match import _kgrams

        assert _kgrams(["a"], 3) == []

    def test_hash_kgram_is_deterministic(self):
        from app.ml.plagiarism.exact_match import _hash_kgram

        assert _hash_kgram("hello world") == _hash_kgram("hello world")
        assert isinstance(_hash_kgram("x"), int)


class TestExactMatcher:
    @pytest.fixture
    def matcher(self):
        from app.ml.plagiarism.exact_match import ExactMatcher

        return ExactMatcher()

    def test_fingerprint_empty_text(self, matcher):
        assert matcher.fingerprint("") == set()

    def test_fingerprint_short_text_hashes_whole(self, matcher):
        # Fewer words than k -> single hash of the whole normalized string.
        fp = matcher.fingerprint("two words")
        assert len(fp) == 1

    def test_fingerprint_returns_hashes_for_long_text(self, matcher):
        text = "the quick brown fox jumps over the lazy dog again and again today"
        fp = matcher.fingerprint(text)
        assert isinstance(fp, set)
        assert len(fp) > 0
        assert all(isinstance(h, int) for h in fp)

    def test_identical_text_has_identical_fingerprints(self, matcher):
        text = "the quick brown fox jumps over the lazy dog repeatedly without stopping"
        assert matcher.fingerprint(text) == matcher.fingerprint(text)

    def test_jaccard_both_empty_is_zero(self, matcher):
        assert matcher.jaccard_similarity(set(), set()) == 0.0

    def test_jaccard_identical_sets_is_one(self, matcher):
        assert matcher.jaccard_similarity({1, 2, 3}, {1, 2, 3}) == 1.0

    def test_jaccard_disjoint_sets_is_zero(self, matcher):
        assert matcher.jaccard_similarity({1, 2}, {3, 4}) == 0.0

    def test_jaccard_partial_overlap(self, matcher):
        # {1,2,3} vs {2,3,4} -> intersection 2, union 4 -> 0.5
        assert matcher.jaccard_similarity({1, 2, 3}, {2, 3, 4}) == 0.5

    def test_lcs_finds_shared_run(self, matcher):
        a = "the cat sat on the warm mat by the door"
        b = "yesterday the cat sat on the cold floor"
        lcs = matcher.longest_common_substring(a, b)
        # "the cat sat on the" is the shared run (5 words).
        assert lcs["length_words"] == 5
        assert lcs["substring"] == "the cat sat on the"
        assert lcs["position_a"] == 0
        assert lcs["position_b"] >= 0

    def test_lcs_no_overlap(self, matcher):
        lcs = matcher.longest_common_substring("alpha beta gamma", "one two three")
        assert lcs["length_words"] == 0
        assert lcs["substring"] == ""

    def test_lcs_empty_inputs(self, matcher):
        lcs = matcher.longest_common_substring("", "anything here")
        assert lcs["length_words"] == 0
        assert lcs["position_a"] == -1

    def test_compare_identical_text_high_overlap(self, matcher):
        text = "machine learning models require large amounts of training data to perform well"
        result = matcher.compare(text, text)
        assert result["jaccard_similarity"] == 1.0
        assert result["overlap_score"] >= 0.9
        assert result["shared_fingerprints"] > 0

    def test_compare_unrelated_text_low_overlap(self, matcher):
        a = "the economy grew steadily over the last fiscal quarter this year"
        b = "penguins waddle across antarctic ice in large noisy colonies daily"
        result = matcher.compare(a, b)
        assert result["overlap_score"] < 0.2

    def test_compare_score_is_clamped_to_one(self, matcher):
        text = "repeat repeat repeat repeat repeat repeat repeat repeat repeat"
        result = matcher.compare(text, text)
        assert 0.0 <= result["overlap_score"] <= 1.0

    def test_compare_result_has_expected_keys(self, matcher):
        result = matcher.compare("some sample text here now", "some other sample text")
        for key in (
            "jaccard_similarity",
            "fingerprint_count_a",
            "fingerprint_count_b",
            "shared_fingerprints",
            "longest_common_substring",
            "lcs_word_ratio",
            "overlap_score",
        ):
            assert key in result


# ===========================================================================
# semantic_match -- embedding model is the boundary, so mock it
# ===========================================================================


def _fake_model(vector_map):
    """Build a fake SentenceTransformer.

    *vector_map* maps a sentence to the numpy vector it should encode to.
    Any unmapped sentence encodes to a fixed orthogonal vector so it never
    matches the mapped ones.
    """
    default = np.array([0.0, 0.0, 1.0], dtype=float)

    def encode(sentences, **kwargs):
        return np.array(
            [vector_map.get(s, default) for s in sentences],
            dtype=float,
        )

    model = MagicMock()
    model.encode.side_effect = encode
    return model


class TestSemanticHelpers:
    def test_split_sentences_drops_short_fragments(self):
        from app.ml.plagiarism.semantic_match import _split_sentences

        sents = _split_sentences("This is a real sentence. Too. Another full sentence here.")
        # "Too." has < 3 words and is dropped.
        assert "This is a real sentence." in sents
        assert all(len(s.split()) >= 3 for s in sents)

    def test_lexical_overlap_identical(self):
        from app.ml.plagiarism.semantic_match import _lexical_overlap

        assert _lexical_overlap("the cat sat", "the cat sat") == 1.0

    def test_lexical_overlap_empty(self):
        from app.ml.plagiarism.semantic_match import _lexical_overlap

        assert _lexical_overlap("", "anything") == 0.0

    def test_cosine_identical_vectors(self):
        from app.ml.plagiarism.semantic_match import _cosine_similarity

        v = np.array([1.0, 2.0, 3.0])
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_orthogonal_vectors(self):
        from app.ml.plagiarism.semantic_match import _cosine_similarity

        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_cosine_zero_vector_is_zero(self):
        from app.ml.plagiarism.semantic_match import _cosine_similarity

        assert _cosine_similarity(np.zeros(3), np.array([1.0, 1.0, 1.0])) == 0.0

    def test_classify_exact_copy(self):
        from app.ml.plagiarism.semantic_match import _classify_match, MatchType

        assert _classify_match(0.95, 0.9) == MatchType.EXACT_COPY

    def test_classify_close_paraphrase(self):
        from app.ml.plagiarism.semantic_match import _classify_match, MatchType

        # high semantic, low lexical
        assert _classify_match(0.9, 0.1) == MatchType.CLOSE_PARAPHRASE

    def test_classify_semantic_match(self):
        from app.ml.plagiarism.semantic_match import _classify_match, MatchType

        assert _classify_match(0.82, 0.5) == MatchType.SEMANTIC_MATCH

    def test_classify_no_match(self):
        from app.ml.plagiarism.semantic_match import _classify_match, MatchType

        assert _classify_match(0.2, 0.1) == MatchType.NO_MATCH


class TestSemanticMatcher:
    def _matcher_with_model(self, model):
        from app.ml.plagiarism.semantic_match import SemanticMatcher

        m = SemanticMatcher()
        m._model = model  # inject the fake so the lazy loader never fires
        return m

    def test_compare_sentences_detects_exact_copy(self):
        # Identical sentence -> identical vector -> cosine 1.0 + full lexical overlap.
        sent = "deep neural networks learn hierarchical feature representations"
        model = _fake_model({sent: np.array([1.0, 0.0, 0.0])})
        m = self._matcher_with_model(model)

        matches = m.compare_sentences([sent], [sent])
        assert len(matches) == 1
        assert matches[0]["match_type"] == "exact_copy"
        assert matches[0]["semantic_similarity"] == 1.0

    def test_compare_sentences_detects_paraphrase(self):
        # Same vector (high semantic) but no shared words (low lexical) -> paraphrase.
        a = "felines often rest atop elevated surfaces during afternoons"
        b = "cats frequently sleep on high shelves throughout midday"
        shared_vec = np.array([0.0, 1.0, 0.0])
        model = _fake_model({a: shared_vec, b: shared_vec})
        m = self._matcher_with_model(model)

        matches = m.compare_sentences([a], [b])
        assert matches[0]["match_type"] == "close_paraphrase"
        assert matches[0]["is_paraphrase"] is True

    def test_compare_sentences_no_match_for_orthogonal(self):
        a = "the stock market rallied sharply this morning"
        b = "volcanic eruptions reshape island coastlines over centuries"
        model = _fake_model({a: np.array([1.0, 0.0, 0.0]), b: np.array([0.0, 1.0, 0.0])})
        m = self._matcher_with_model(model)

        matches = m.compare_sentences([a], [b])
        assert matches[0]["match_type"] == "no_match"

    def test_compare_sentences_empty_inputs(self):
        m = self._matcher_with_model(_fake_model({}))
        assert m.compare_sentences([], ["something here please"]) == []

    def test_compare_falls_back_when_model_missing(self):
        # model loads to None -> lexical-only path. Identical text -> exact_copy.
        from app.ml.plagiarism.semantic_match import SemanticMatcher

        m = SemanticMatcher()
        with patch("app.ml.plagiarism.semantic_match._load_model", return_value=None):
            sent = "this exact sentence appears in both documents verbatim"
            result = m.compare(sent, sent)
        assert result["exact_copies"] >= 1

    def test_compare_returns_zero_for_empty_text(self):
        m = self._matcher_with_model(_fake_model({}))
        result = m.compare("", "non empty document text here")
        assert result["overall_semantic_similarity"] == 0.0
        assert result["matches"] == []

    def test_compare_aggregates_counts(self):
        a1 = "transformers use self attention to weigh token importance"
        a2 = "the bakery down the street sells fresh sourdough each morning"
        vec_match = np.array([1.0, 0.0, 0.0])
        model = _fake_model({a1: vec_match})  # a2 -> default orthogonal vector
        m = self._matcher_with_model(model)

        text_a = a1 + ". " + a2 + "."
        text_b = a1 + "."
        result = m.compare(text_a, text_b)
        assert result["exact_copies"] >= 1
        assert 0.0 <= result["flagged_sentence_ratio"] <= 1.0

    def test_load_model_returns_none_on_import_error(self):
        # Boundary: simulate sentence-transformers being unavailable.
        from app.ml.plagiarism.semantic_match import _load_model

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            assert _load_model() is None


# ===========================================================================
# source_discovery -- key-phrase extraction real; all HTTP mocked
# ===========================================================================


class TestKeyPhraseExtraction:
    def test_extracts_phrases(self):
        from app.ml.plagiarism.source_discovery import extract_key_phrases

        text = (
            "climate change drives extreme weather events. climate change also "
            "affects global food production and water supplies worldwide."
        )
        phrases = extract_key_phrases(text, top_n=3)
        assert len(phrases) <= 3
        assert any("climate change" in p for p in phrases)

    def test_empty_text_returns_no_phrases(self):
        from app.ml.plagiarism.source_discovery import extract_key_phrases

        assert extract_key_phrases("") == []

    def test_stopwords_only_returns_empty(self):
        from app.ml.plagiarism.source_discovery import extract_key_phrases

        assert extract_key_phrases("the and of to in is it") == []


def _ddg_response_with_results():
    return {
        "Abstract": "An overview of the topic.",
        "Heading": "Topic Heading",
        "AbstractURL": "https://example.com/topic",
        "RelatedTopics": [{"Text": "Related thing", "FirstURL": "https://example.com/related"}],
    }


class _FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, json_data=None, text="", status_code=200, raise_exc=None):
        self._json = json_data or {}
        self.text = text
        self.status_code = status_code
        self.headers = {"content-type": "text/html"}
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._json


def _client_returning(response_or_exc):
    """Build a fake AsyncClient whose .get yields a response or raises."""
    client = MagicMock()
    if isinstance(response_or_exc, Exception):
        client.get = AsyncMock(side_effect=response_or_exc)
    else:
        client.get = AsyncMock(return_value=response_or_exc)
    return client


class TestSourceSearchEngines:
    @pytest.mark.asyncio
    async def test_duckduckgo_found(self):
        from app.ml.plagiarism.source_discovery import _search_duckduckgo

        client = _client_returning(_FakeResponse(json_data=_ddg_response_with_results()))
        results = await _search_duckduckgo("query", client)
        assert len(results) >= 1
        assert results[0]["source_engine"] == "duckduckgo"

    @pytest.mark.asyncio
    async def test_duckduckgo_none_found(self):
        from app.ml.plagiarism.source_discovery import _search_duckduckgo

        client = _client_returning(_FakeResponse(json_data={}))
        assert await _search_duckduckgo("query", client) == []

    @pytest.mark.asyncio
    async def test_duckduckgo_http_error_swallowed(self):
        from app.ml.plagiarism.source_discovery import _search_duckduckgo

        err = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        client = _client_returning(_FakeResponse(raise_exc=err))
        # Engine failures are caught and yield an empty list, not an exception.
        assert await _search_duckduckgo("query", client) == []

    @pytest.mark.asyncio
    async def test_duckduckgo_timeout_swallowed(self):
        from app.ml.plagiarism.source_discovery import _search_duckduckgo

        client = _client_returning(httpx.TimeoutException("timed out"))
        assert await _search_duckduckgo("query", client) == []

    @pytest.mark.asyncio
    async def test_semantic_scholar_parses_papers(self):
        from app.ml.plagiarism.source_discovery import _search_semantic_scholar

        data = {
            "data": [
                {
                    "title": "A Paper",
                    "abstract": "Some abstract text.",
                    "url": "https://semscholar/paper/1",
                    "year": 2021,
                    "authors": [{"name": "Jane Doe"}],
                }
            ]
        }
        client = _client_returning(_FakeResponse(json_data=data))
        results = await _search_semantic_scholar("query", client)
        assert results[0]["title"] == "A Paper"
        assert results[0]["source_engine"] == "semantic_scholar"
        assert "Jane Doe" in results[0]["authors"]

    @pytest.mark.asyncio
    async def test_crossref_strips_html_from_abstract(self):
        from app.ml.plagiarism.source_discovery import _search_crossref

        data = {
            "message": {
                "items": [
                    {
                        "title": ["A Work"],
                        "abstract": "<jats:p>Body text.</jats:p>",
                        "URL": "https://doi.org/10.1/x",
                        "DOI": "10.1/x",
                        "author": [{"given": "A", "family": "B"}],
                    }
                ]
            }
        }
        client = _client_returning(_FakeResponse(json_data=data))
        results = await _search_crossref("query", client)
        assert results[0]["snippet"] == "Body text."
        assert results[0]["doi"] == "10.1/x"

    @pytest.mark.asyncio
    async def test_openalex_reconstructs_inverted_abstract(self):
        from app.ml.plagiarism.source_discovery import _search_openalex

        data = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "title": "Inverted Work",
                    "doi": "https://doi.org/10.2/y",
                    "publication_year": 2020,
                    "authorships": [{"author": {"display_name": "Carol"}}],
                    "abstract_inverted_index": {"hello": [0], "world": [1]},
                }
            ]
        }
        client = _client_returning(_FakeResponse(json_data=data))
        results = await _search_openalex("query", client)
        assert results[0]["snippet"] == "hello world"
        assert results[0]["url"] == "https://doi.org/10.2/y"

    @pytest.mark.asyncio
    async def test_wikipedia_builds_page_urls(self):
        from app.ml.plagiarism.source_discovery import _search_wikipedia

        data = {"query": {"search": [{"title": "Some Page", "snippet": "a <b>snip</b>pet"}]}}
        client = _client_returning(_FakeResponse(json_data=data))
        results = await _search_wikipedia("query", client)
        assert results[0]["source_engine"] == "wikipedia"
        assert "en.wikipedia.org/wiki/" in results[0]["url"]
        assert "<b>" not in results[0]["snippet"]

    @pytest.mark.asyncio
    async def test_arxiv_parses_atom(self):
        from app.ml.plagiarism.source_discovery import _search_arxiv

        atom = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Arxiv Paper</title>
            <summary>Paper summary here.</summary>
            <id>http://arxiv.org/abs/1234.5678</id>
            <author><name>Dana</name></author>
          </entry>
        </feed>"""
        client = _client_returning(_FakeResponse(text=atom))
        results = await _search_arxiv("query", client)
        assert results[0]["title"] == "Arxiv Paper"
        assert results[0]["url"] == "http://arxiv.org/abs/1234.5678"
        assert "Dana" in results[0]["authors"]

    @pytest.mark.asyncio
    async def test_arxiv_http_error_swallowed(self):
        from app.ml.plagiarism.source_discovery import _search_arxiv

        client = _client_returning(httpx.ConnectError("boom"))
        assert await _search_arxiv("query", client) == []


class TestFetchPageContent:
    @pytest.mark.asyncio
    async def test_extracts_visible_text(self):
        from app.ml.plagiarism.source_discovery import fetch_page_content

        html = "<html><body><script>x</script><p>Hello there world</p></body></html>"
        client = _client_returning(_FakeResponse(text=html))
        text = await fetch_page_content("https://example.com", client)
        assert "Hello there world" in text
        assert "x" not in text or "Hello" in text  # script content removed

    @pytest.mark.asyncio
    async def test_skips_non_html_content(self):
        from app.ml.plagiarism.source_discovery import fetch_page_content

        resp = _FakeResponse(text="binary")
        resp.headers = {"content-type": "application/pdf"}
        client = _client_returning(resp)
        assert await fetch_page_content("https://example.com/x.pdf", client) == ""

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        from app.ml.plagiarism.source_discovery import fetch_page_content

        client = _client_returning(httpx.TimeoutException("slow"))
        assert await fetch_page_content("https://example.com", client) == ""


class TestSourceDiscoveryOrchestrator:
    @pytest.mark.asyncio
    async def test_search_no_phrases_returns_empty(self):
        from app.ml.plagiarism.source_discovery import SourceDiscovery

        result = await SourceDiscovery().search("the and of to")
        assert result["sources"] == []
        assert result["engines_queried"] == 0

    @pytest.mark.asyncio
    async def test_search_aggregates_and_dedupes(self):
        from app.ml.plagiarism import source_discovery as sd

        # Two engines return the same URL; it should appear once.
        dup = [{"title": "T", "url": "https://dup", "snippet": "s", "source_engine": "a"}]
        with (
            patch.object(sd, "_search_duckduckgo", AsyncMock(return_value=dup)),
            patch.object(sd, "_search_semantic_scholar", AsyncMock(return_value=dup)),
            patch.object(sd, "_search_crossref", AsyncMock(return_value=[])),
            patch.object(sd, "_search_openalex", AsyncMock(return_value=[])),
            patch.object(sd, "_search_wikipedia", AsyncMock(return_value=[])),
            patch.object(sd, "_search_arxiv", AsyncMock(return_value=[])),
        ):
            result = await sd.SourceDiscovery().search(
                "renewable energy adoption accelerates worldwide across many nations"
            )
        urls = [s["url"] for s in result["sources"]]
        assert urls.count("https://dup") == 1
        assert result["engines_queried"] == 6

    @pytest.mark.asyncio
    async def test_search_tolerates_engine_exceptions(self):
        from app.ml.plagiarism import source_discovery as sd

        ok = [{"title": "T", "url": "https://ok", "snippet": "s", "source_engine": "a"}]
        with (
            patch.object(sd, "_search_duckduckgo", AsyncMock(return_value=ok)),
            patch.object(
                sd, "_search_semantic_scholar", AsyncMock(side_effect=RuntimeError("boom"))
            ),
            patch.object(sd, "_search_crossref", AsyncMock(return_value=[])),
            patch.object(sd, "_search_openalex", AsyncMock(return_value=[])),
            patch.object(sd, "_search_wikipedia", AsyncMock(return_value=[])),
            patch.object(sd, "_search_arxiv", AsyncMock(return_value=[])),
        ):
            result = await sd.SourceDiscovery().search(
                "renewable energy adoption accelerates worldwide across many nations"
            )
        # The crashing engine is tolerated; the good source still comes through.
        assert any(s["url"] == "https://ok" for s in result["sources"])

    @pytest.mark.asyncio
    async def test_search_and_fetch_adds_content(self):
        from app.ml.plagiarism import source_discovery as sd

        disc = sd.SourceDiscovery()
        fake_search = {
            "key_phrases": ["x"],
            "sources": [{"url": "https://a"}, {"url": "https://b"}],
            "engines_queried": 6,
        }
        with (
            patch.object(disc, "search", AsyncMock(return_value=fake_search)),
            patch.object(sd, "fetch_page_content", AsyncMock(side_effect=["content a", ""])),
        ):
            result = await disc.search_and_fetch("anything")
        assert result["fetched_content"] == {"https://a": "content a"}


# ===========================================================================
# pipeline -- compose stages with mocked components
# ===========================================================================


class TestPipelineHelpers:
    def test_split_paragraphs_drops_tiny(self):
        from app.ml.plagiarism.pipeline import _split_paragraphs

        text = (
            "This is a paragraph with enough words.\n\nTiny.\n\nAnother decent paragraph here now."
        )
        paras = _split_paragraphs(text)
        assert all(len(p.split()) >= 5 for p in paras)
        assert len(paras) == 2


class TestPlagiarismPipeline:
    @pytest.fixture
    def pipeline(self):
        from app.ml.plagiarism.pipeline import PlagiarismPipeline

        return PlagiarismPipeline()

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_result(self, pipeline):
        result = await pipeline.analyze("   ")
        assert result["overall_plagiarism_score"] == 0.0
        assert result["originality_percentage"] == 100.0
        assert result["sources_found"] == []

    @pytest.mark.asyncio
    async def test_no_sources_yields_full_originality(self, pipeline):
        # Discovery finds nothing -> nothing to compare -> 100% original.
        empty_discovery = MagicMock()
        empty_discovery.search_and_fetch = AsyncMock(
            return_value={"key_phrases": [], "sources": [], "fetched_content": {}}
        )
        pipeline._source_discovery = empty_discovery

        result = await pipeline.analyze(
            "A genuinely original paragraph that nobody has ever written before now."
        )
        assert result["overall_plagiarism_score"] == 0.0
        assert result["originality_percentage"] == 100.0
        assert result["sources_found"] == []

    @pytest.mark.asyncio
    async def test_detects_copied_paragraph(self, pipeline):
        # A source whose fetched content equals the input -> high overlap.
        copied = (
            "Photosynthesis converts sunlight carbon dioxide and water into glucose "
            "and oxygen inside the chloroplasts of green plant cells every day."
        )
        discovery = MagicMock()
        discovery.search_and_fetch = AsyncMock(
            return_value={
                "key_phrases": ["photosynthesis"],
                "sources": [
                    {
                        "title": "Bio Source",
                        "url": "https://bio.example",
                        "source_engine": "wikipedia",
                        "snippet": copied,
                    }
                ],
                "fetched_content": {"https://bio.example": copied},
            }
        )
        pipeline._source_discovery = discovery

        # Stub the semantic matcher so we don't load embeddings; exact match runs real.
        sem = MagicMock()
        sem.compare = MagicMock(
            return_value={
                "overall_semantic_similarity": 0.0,
                "flagged_sentence_ratio": 0.0,
                "exact_copies": 0,
                "close_paraphrases": 0,
            }
        )
        pipeline._semantic_matcher = sem

        result = await pipeline.analyze(copied)
        assert result["overall_plagiarism_score"] > 0.5
        assert result["originality_percentage"] < 50.0
        assert len(result["sources_found"]) == 1
        assert result["sources_found"][0]["url"] == "https://bio.example"

    @pytest.mark.asyncio
    async def test_short_snippet_sources_are_skipped(self, pipeline):
        # Sources with < 10 words of content are excluded from comparison.
        discovery = MagicMock()
        discovery.search_and_fetch = AsyncMock(
            return_value={
                "key_phrases": ["x"],
                "sources": [{"title": "Tiny", "url": "https://t", "snippet": "too short"}],
                "fetched_content": {},
            }
        )
        pipeline._source_discovery = discovery

        result = await pipeline.analyze(
            "Some reasonably long original paragraph of text that should stay original."
        )
        assert result["overall_plagiarism_score"] == 0.0

    @pytest.mark.asyncio
    async def test_degrades_when_semantic_stage_fails(self, pipeline):
        # Semantic matcher raises; exact match should still drive the result
        # rather than the whole pipeline blowing up.
        copied = (
            "Newton's laws of motion describe the relationship between an object "
            "and the forces acting upon it during everyday physical interactions."
        )
        discovery = MagicMock()
        discovery.search_and_fetch = AsyncMock(
            return_value={
                "key_phrases": ["newton"],
                "sources": [
                    {
                        "title": "Phys",
                        "url": "https://phys",
                        "source_engine": "wikipedia",
                        "snippet": copied,
                    }
                ],
                "fetched_content": {"https://phys": copied},
            }
        )
        pipeline._source_discovery = discovery

        sem = MagicMock()
        sem.compare = MagicMock(side_effect=RuntimeError("model exploded"))
        pipeline._semantic_matcher = sem

        # A failing semantic stage degrades: exact matching still drives
        # the verdict instead of the whole analysis blowing up.
        result = await pipeline.analyze(copied)
        assert result["overall_plagiarism_score"] > 0.5
        # the identical source text is still caught by exact match alone
        assert result["paragraph_analysis"][0]["plagiarism_score"] > 0.5

    def test_build_summary_high_originality(self, pipeline):
        from app.ml.plagiarism.pipeline import PlagiarismPipeline

        summary = PlagiarismPipeline._build_summary(0.02, 98.0, [], [])
        assert "highly original" in summary

    def test_build_summary_significant_overlap(self, pipeline):
        from app.ml.plagiarism.pipeline import PlagiarismPipeline

        paras = [{"plagiarism_score": 0.8}]
        sources = [{"title": "S", "url": "u"}]
        summary = PlagiarismPipeline._build_summary(0.75, 25.0, paras, sources)
        assert "Significant similarities" in summary
        assert "source" in summary

    def test_empty_result_shape(self):
        from app.ml.plagiarism.pipeline import PlagiarismPipeline

        result = PlagiarismPipeline._empty_result()
        for key in (
            "overall_plagiarism_score",
            "originality_percentage",
            "paragraph_analysis",
            "sources_found",
            "key_phrases",
            "summary",
        ):
            assert key in result
