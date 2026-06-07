"""
Integration tests for key ClarityAI API endpoints.

These tests use a lightweight async HTTP client backed by the FastAPI app
directly (no real server needed).  Heavy ML models are intentionally not
loaded during the test run — tests focus on routing, schema validation, and
error-handling behaviour.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# /api/v1/health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """Health endpoint must return HTTP 200 with a 'healthy' status."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_response_schema(client):
    """Health response must include all required fields."""
    resp = await client.get("/api/v1/health")
    body = resp.json()
    required_fields = {
        "status",
        "model_version",
        "uptime_seconds",
        "loaded_models",
        "ollama_available",
        "database",
        "timestamp",
    }
    assert required_fields.issubset(body.keys())


@pytest.mark.asyncio
async def test_health_status_value(client):
    """Health endpoint status field must be 'healthy'."""
    resp = await client.get("/api/v1/health")
    assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# /api/v1/history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_returns_200(client):
    """History endpoint returns 200 even when the database is empty."""
    resp = await client.get("/api/v1/history")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_history_response_schema(client):
    """History response must contain pagination fields."""
    resp = await client.get("/api/v1/history")
    body = resp.json()
    assert "page" in body
    assert "limit" in body
    assert "total" in body
    assert "results" in body
    assert isinstance(body["results"], list)


@pytest.mark.asyncio
async def test_history_default_pagination(client):
    """History endpoint default page is 1."""
    resp = await client.get("/api/v1/history")
    assert resp.json()["page"] == 1


@pytest.mark.asyncio
async def test_history_invalid_page_raises_422(client):
    """Passing page=0 (below minimum) must return 422 Unprocessable Entity."""
    resp = await client.get("/api/v1/history?page=0")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/detect — validation only (no ML model required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_empty_text_returns_422(client):
    """Sending an empty text string must return 422."""
    resp = await client.post("/api/v1/detect", json={"text": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_detect_invalid_mode_returns_422(client):
    """Sending an invalid mode must return 422."""
    resp = await client.post(
        "/api/v1/detect",
        json={"text": "Some valid text here.", "mode": "invalid_mode"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_detect_missing_text_returns_422(client):
    """Sending a request with no text field must return 422."""
    resp = await client.post("/api/v1/detect", json={"mode": "fast"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# OpenAPI schema sanity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_schema_accessible(client):
    """OpenAPI JSON schema endpoint must be reachable."""
    resp = await client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    assert "paths" in resp.json()
