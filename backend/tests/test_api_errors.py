"""
Error-path, validation, and abuse tests for the ClarityAI API routes.

These exercise the failure side of every route group: malformed payloads,
empty bodies, unknown IDs, oversized/undersized text, and a few security
flavours (SQL-injection-looking strings, script tags, forged share tokens).
Heavy ML is never loaded — detectors and analyzers are swapped for tiny
in-memory fakes at the module boundary, the same trick test_detection_wiring
uses, so these tests stay fast and deterministic.
"""

from __future__ import annotations

import json

import pytest

from app.api.routes import advanced, analytics, detection
from app.core.config import settings


# ---------------------------------------------------------------------------
# Tiny fakes so no real models load
# ---------------------------------------------------------------------------


class _FakeDetector:
    """Stands in for a real detector; returns a fixed signal instantly."""

    signal_name = "entropy_analyzer"

    async def analyze(self, text: str) -> dict:
        return {"signal": "entropy_analyzer", "ai_probability": 0.5, "confidence": "low"}


class _FakeAnalyzer:
    """Stands in for an analytics analyzer; echoes a trivial result.

    It deliberately does nothing with the text beyond reporting its length,
    so any injection payload flows through harmlessly.
    """

    def analyze(self, *args, **kwargs) -> dict:
        text = args[0] if args else ""
        return {"ok": True, "chars": len(text)}


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Hand each test a fresh token budget.

    The rate limiter keeps a process-wide bucket store, so without this the
    per-endpoint burst budget leaks between tests and unrelated cases start
    seeing spurious 429s. Clearing the buckets keeps these tests independent.
    """
    from app.core.rate_limiter import get_rate_limiter_store

    get_rate_limiter_store()._buckets.clear()
    yield


@pytest.fixture
def fake_detectors(monkeypatch):
    """Swap the detection roster for a single instant fake detector."""
    monkeypatch.setitem(detection._detectors_cache, "all", [_FakeDetector()])
    monkeypatch.setitem(detection._detectors_cache, "fast", [_FakeDetector()])


@pytest.fixture
def fake_analyzers(monkeypatch):
    """Make every analytics analyzer resolve to the no-op fake."""
    monkeypatch.setattr(analytics, "_get_analyzer", lambda name: _FakeAnalyzer())


def _enough_words(n: int = 60) -> str:
    return " ".join(["word"] * n)


def _no_stack_trace(body) -> None:
    """A 404/4xx body must not leak a stack trace or source path."""
    text = json.dumps(body)
    assert "Traceback" not in text
    assert ".py" not in text
    assert "/home/" not in text


# ---------------------------------------------------------------------------
# /detect — body validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_empty_body_returns_422(client):
    resp = await client.post("/api/v1/detect", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_detect_malformed_json_returns_422(client):
    resp = await client.post(
        "/api/v1/detect",
        content="{not valid json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_detect_below_min_words_returns_422(client):
    # Above pydantic's min_length=1 but below the MIN_WORDS business rule.
    resp = await client.post("/api/v1/detect", json={"text": "only three words here"})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "too short" in str(detail).lower()
    assert str(settings.MIN_WORDS) in str(detail)


@pytest.mark.asyncio
async def test_detect_above_max_words_returns_422(client):
    resp = await client.post("/api/v1/detect", json={"text": _enough_words(settings.MAX_WORDS + 1)})
    assert resp.status_code == 422
    assert "too long" in str(resp.json()["detail"]).lower()


@pytest.mark.asyncio
async def test_detect_unknown_id_returns_404(client):
    resp = await client.get("/api/v1/detect/does-not-exist")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


@pytest.mark.asyncio
async def test_detect_batch_status_unknown_id_returns_404(client):
    resp = await client.get("/api/v1/detect/batch/nope")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


# ---------------------------------------------------------------------------
# /detect — security / abuse inputs (must never 500)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_sql_injection_string_is_handled(client, fake_detectors):
    payload = "Robert'); DROP TABLE analyses;-- " + _enough_words(60)
    resp = await client.post("/api/v1/detect", json={"text": payload, "mode": "fast"})
    assert resp.status_code == 200
    # The table must still be there afterwards.
    follow = await client.get("/api/v1/history")
    assert follow.status_code == 200


@pytest.mark.asyncio
async def test_detect_script_tag_is_handled(client, fake_detectors):
    payload = "<script>alert('xss')</script> " + _enough_words(60)
    resp = await client.post("/api/v1/detect", json={"text": payload, "mode": "fast"})
    assert resp.status_code == 200
    # Whatever is echoed back must not have crashed serialization.
    assert "analysis_id" in resp.json()


# ---------------------------------------------------------------------------
# Analytics — body validation + abuse
# ---------------------------------------------------------------------------

# Every analytics endpoint that takes a single text field.
_TEXT_ANALYTICS = [
    "readability",
    "tone",
    "grammar",
    "statistics",
    "suggestions",
    "citations",
    "full",
    "seo",
    "facts",
    "paraphrase",
]


@pytest.mark.parametrize("endpoint", _TEXT_ANALYTICS)
@pytest.mark.asyncio
async def test_analytics_empty_body_returns_422(client, endpoint):
    resp = await client.post(f"/api/v1/analytics/{endpoint}", json={})
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", _TEXT_ANALYTICS)
@pytest.mark.asyncio
async def test_analytics_malformed_json_returns_422(client, endpoint):
    resp = await client.post(
        f"/api/v1/analytics/{endpoint}",
        content="}{",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analytics_empty_text_returns_422(client):
    resp = await client.post("/api/v1/analytics/readability", json={"text": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analytics_compare_missing_field_returns_422(client):
    resp = await client.post("/api/v1/analytics/compare", json={"text_a": "hello there"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analytics_sql_injection_string_is_handled(client, fake_analyzers):
    payload = "1; DROP TABLE analytics_results; --"
    resp = await client.post("/api/v1/analytics/readability", json={"text": payload})
    assert resp.status_code == 200
    follow = await client.get("/api/v1/history")
    assert follow.status_code == 200


@pytest.mark.asyncio
async def test_analytics_script_tag_is_handled(client, fake_analyzers):
    resp = await client.post(
        "/api/v1/analytics/statistics",
        json={"text": "<script>document.cookie</script>"},
    )
    assert resp.status_code == 200
    assert resp.json()["analysis_type"] == "statistics"


# ---------------------------------------------------------------------------
# Plagiarism — validation + unknown id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plagiarism_empty_body_returns_422(client):
    resp = await client.post("/api/v1/plagiarism", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_plagiarism_malformed_json_returns_422(client):
    resp = await client.post(
        "/api/v1/plagiarism",
        content="not json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_plagiarism_below_min_words_returns_422(client):
    resp = await client.post("/api/v1/plagiarism", json={"text": "too short"})
    assert resp.status_code == 422
    assert "too short" in str(resp.json()["detail"]).lower()


@pytest.mark.asyncio
async def test_plagiarism_unknown_id_returns_404(client):
    resp = await client.get("/api/v1/plagiarism/missing-id")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


# ---------------------------------------------------------------------------
# Humanization — validation + unknown id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_humanize_empty_body_returns_422(client):
    resp = await client.post("/api/v1/humanize", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_humanize_malformed_json_returns_422(client):
    resp = await client.post(
        "/api/v1/humanize",
        content="<<<",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_humanize_below_min_words_returns_422(client):
    # The word-count guard runs before any Ollama call, so no network needed.
    resp = await client.post("/api/v1/humanize", json={"text": "way too short"})
    assert resp.status_code == 422
    assert "too short" in str(resp.json()["detail"]).lower()


@pytest.mark.asyncio
async def test_humanize_bad_target_score_returns_422(client):
    resp = await client.post(
        "/api/v1/humanize",
        json={"text": _enough_words(60), "target_ai_score": 5.0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_humanize_unknown_id_returns_404(client):
    resp = await client.get("/api/v1/humanize/missing-id")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


# ---------------------------------------------------------------------------
# Export — validation, unknown id, forged share token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_pdf_without_data_or_id_returns_422(client):
    resp = await client.post("/api/v1/export/pdf", json={})
    assert resp.status_code == 422
    assert "analysis_id or data" in str(resp.json()["detail"])


@pytest.mark.asyncio
async def test_export_json_without_data_or_id_returns_422(client):
    resp = await client.post("/api/v1/export/json", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_export_pdf_unknown_id_returns_404(client):
    resp = await client.post("/api/v1/export/pdf", json={"analysis_id": "ghost"})
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


@pytest.mark.asyncio
async def test_export_csv_unknown_ids_returns_404(client):
    resp = await client.post("/api/v1/export/csv", json={"analysis_ids": ["ghost"]})
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


@pytest.mark.asyncio
async def test_export_share_unknown_id_returns_404(client):
    # A forged/unknown analysis id on the share-link endpoint must 404, never 500.
    resp = await client.get("/api/v1/export/forged-token/share")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


# ---------------------------------------------------------------------------
# Advanced — validation, unknown ids, forged share token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_advanced_rewrite_empty_body_returns_422(client):
    resp = await client.post("/api/v1/advanced/rewrite-detect", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_advanced_fingerprint_empty_text_returns_422(client):
    resp = await client.post("/api/v1/advanced/fingerprint", json={"text": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_advanced_version_history_unknown_doc_returns_404(client):
    resp = await client.get("/api/v1/advanced/version/no-such-doc")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


@pytest.mark.asyncio
async def test_advanced_batch_unknown_id_returns_404(client):
    resp = await client.get("/api/v1/advanced/batch/no-such-batch")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


@pytest.mark.asyncio
async def test_advanced_fingerprint_verify_unknown_ids_returns_404(client):
    resp = await client.post(
        "/api/v1/advanced/fingerprint/verify",
        json={"fingerprint_id_1": "a", "fingerprint_id_2": "b"},
    )
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


@pytest.mark.asyncio
async def test_advanced_shared_forged_token_returns_404(client):
    # A forged share token must resolve to a clean 404, never a 500.
    resp = await client.get("/api/v1/advanced/share/totally-made-up-token")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


# ---------------------------------------------------------------------------
# Dashboard — read-only aggregates must survive an empty DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_stats_returns_200_with_shape(client):
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_analyses"] >= 0
    assert isinstance(body["average_ai_score"], (int, float))


@pytest.mark.asyncio
async def test_dashboard_trends_returns_200_with_shape(client):
    resp = await client.get("/api/v1/dashboard/trends")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["ai_score_histogram"], list)
    assert isinstance(body["analyses_per_day"], list)


@pytest.mark.asyncio
async def test_dashboard_top_signals_returns_200_with_shape(client):
    resp = await client.get("/api/v1/dashboard/top-signals")
    assert resp.status_code == 200
    assert isinstance(resp.json()["signals"], list)


# ---------------------------------------------------------------------------
# Health / history — error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_page_beyond_range_returns_404_when_data_exists(client, fake_detectors):
    # Create one analysis so the total > 0, then ask for a page that can't exist.
    created = await client.post("/api/v1/detect", json={"text": _enough_words(60), "mode": "fast"})
    assert created.status_code == 200

    resp = await client.get("/api/v1/history?page=99")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())


@pytest.mark.asyncio
async def test_history_invalid_sort_returns_422(client):
    resp = await client.get("/api/v1/history?sort_by=drop_table")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_history_out_of_range_score_returns_422(client):
    resp = await client.get("/api/v1/history?min_score=2.0")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unknown_route_returns_404(client):
    resp = await client.get("/api/v1/this-route-does-not-exist")
    assert resp.status_code == 404
    _no_stack_trace(resp.json())
