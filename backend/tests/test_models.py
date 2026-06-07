"""
Unit tests for Pydantic models / schemas used throughout the ClarityAI backend.

These tests validate model construction, field defaults, validation behaviour,
and repr output — all without starting the server or loading ML models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# DB ORM models (SQLAlchemy mapped classes)
# ---------------------------------------------------------------------------


class TestAnalysisOrmModel:
    """Tests for the Analysis SQLAlchemy model."""

    def test_new_uuid_generates_hex(self):
        from app.db.models import _new_uuid

        result = _new_uuid()
        assert isinstance(result, str)
        assert len(result) == 32  # hex = 32 chars
        # Should be valid hex
        int(result, 16)

    def test_utcnow_returns_aware_datetime(self):
        from app.db.models import _utcnow

        dt = _utcnow()
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None

    def test_analysis_repr(self):
        from app.db.models import Analysis

        a = Analysis(
            id="abc123",
            input_text="Test text.",
            word_count=2,
            overall_ai_score=0.75,
            classification="ai_generated",
            confidence=0.9,
            processing_time_ms=100,
            model_version="v1",
        )
        r = repr(a)
        assert "abc123" in r
        assert "ai_generated" in r

    def test_plagiarism_result_repr(self):
        from app.db.models import PlagiarismResult

        pr = PlagiarismResult(
            id="plag01",
            analysis_id="abc123",
            similarity_score=0.85,
            method="semantic",
        )
        r = repr(pr)
        assert "plag01" in r
        assert "0.85" in r

    def test_humanization_result_repr(self):
        from app.db.models import HumanizationResult

        hr = HumanizationResult(
            id="hum01",
            analysis_id="abc123",
            original_text="Original.",
            humanized_text="Rewritten.",
            original_ai_score=0.9,
            humanized_ai_score=0.05,
            iterations_used=2,
            strategy="ollama",
            processing_time_ms=500,
        )
        r = repr(hr)
        assert "hum01" in r

    def test_batch_job_default_status(self):
        from app.db.models import BatchJob

        bj = BatchJob(id="batch01", total_files=5)
        assert bj.status == "pending"
        assert bj.total_files == 5

    def test_batch_job_repr(self):
        from app.db.models import BatchJob

        bj = BatchJob(id="batch01", total_files=3, processed_files=1)
        assert "batch01" in repr(bj)


# ---------------------------------------------------------------------------
# Detection route Pydantic schemas
# ---------------------------------------------------------------------------


class TestDetectionSchemas:
    """Tests for DetectionRequest, FastDetectionRequest, etc."""

    def test_detection_request_defaults(self):
        from app.api.routes.detection import DetectionRequest

        req = DetectionRequest(text="Sample text for detection analysis here.")
        assert req.mode == "deep"
        assert req.options.include_sentence_scores is True

    def test_detection_request_fast_mode(self):
        from app.api.routes.detection import DetectionRequest

        req = DetectionRequest(text="Some text.", mode="fast")
        assert req.mode == "fast"

    def test_detection_request_invalid_mode(self):
        from app.api.routes.detection import DetectionRequest

        with pytest.raises(ValidationError):
            DetectionRequest(text="Some text.", mode="ultra")

    def test_detection_request_empty_text_fails(self):
        from app.api.routes.detection import DetectionRequest

        with pytest.raises(ValidationError):
            DetectionRequest(text="")

    def test_fast_detection_request_valid(self):
        from app.api.routes.detection import FastDetectionRequest

        req = FastDetectionRequest(text="Quick check text.")
        assert req.text == "Quick check text."

    def test_batch_detection_request_valid(self):
        from app.api.routes.detection import BatchDetectionRequest

        req = BatchDetectionRequest(texts=["Text one.", "Text two."])
        assert len(req.texts) == 2

    def test_batch_detection_empty_list_fails(self):
        from app.api.routes.detection import BatchDetectionRequest

        with pytest.raises(ValidationError):
            BatchDetectionRequest(texts=[])


# ---------------------------------------------------------------------------
# Health route Pydantic schemas
# ---------------------------------------------------------------------------


class TestHealthSchemas:
    """Tests for HealthResponse and HistoryResponse schemas."""

    def test_health_response_construction(self):
        from app.api.routes.health import HealthResponse

        now = datetime.now(timezone.utc).isoformat()
        resp = HealthResponse(
            status="healthy",
            model_version="1.0.0",
            uptime_seconds=42.5,
            loaded_models=3,
            ollama_available=False,
            database="sqlite (aiosqlite)",
            timestamp=now,
        )
        assert resp.status == "healthy"
        assert resp.uptime_seconds == 42.5

    def test_history_response_construction(self):
        from app.api.routes.health import HistoryResponse

        resp = HistoryResponse(
            page=1,
            limit=20,
            total=0,
            total_pages=1,
            results=[],
        )
        assert resp.total == 0
        assert resp.results == []

    def test_analysis_summary_construction(self):
        from app.api.routes.health import AnalysisSummary

        summary = AnalysisSummary(
            analysis_id="abc123",
            classification="human_written",
            overall_ai_score=0.12,
            word_count=150,
            processing_time_ms=320,
            model_version="v1",
            created_at="2025-01-01T00:00:00+00:00",
        )
        assert summary.classification == "human_written"
        assert summary.overall_ai_score == 0.12


# ---------------------------------------------------------------------------
# Settings / config
# ---------------------------------------------------------------------------


class TestSettings:
    """Sanity-check that the Settings object loads without errors."""

    def test_settings_loads(self):
        from app.core.config import settings

        assert settings.APP_NAME == "ClarityAI"
        assert settings.APP_VERSION is not None

    def test_settings_cors_origins_list(self):
        from app.core.config import settings

        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0

    def test_settings_thresholds_in_range(self):
        from app.core.config import settings

        assert 0.0 < settings.AI_THRESHOLD_HIGH <= 1.0
        assert 0.0 < settings.AI_THRESHOLD_MEDIUM < settings.AI_THRESHOLD_HIGH

    def test_settings_min_words_positive(self):
        from app.core.config import settings

        assert settings.MIN_WORDS > 0
        assert settings.MAX_WORDS > settings.MIN_WORDS
