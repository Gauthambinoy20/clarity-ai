from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return uuid.uuid4().hex


class Analysis(Base):
    """Stores the result of a single AI-content detection analysis."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_ai_score: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # "ai_generated", "human_written", "mixed"
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Detailed JSON payloads stored as text (SQLite has no native JSON type)
    signals_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentence_scores_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gltr_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    attribution_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )

    # Relationships
    plagiarism_results: Mapped[list[PlagiarismResult]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    humanization_results: Mapped[list[HumanizationResult]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Analysis id={self.id!r} classification={self.classification!r} "
            f"score={self.overall_ai_score:.2f}>"
        )


class PlagiarismResult(Base):
    """Stores plagiarism-check results linked to an analysis."""

    __tablename__ = "plagiarism_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    matched_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="semantic"
    )  # "semantic", "exact", "fuzzy"
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )

    analysis: Mapped[Analysis] = relationship(back_populates="plagiarism_results")

    def __repr__(self) -> str:
        return f"<PlagiarismResult id={self.id!r} " f"similarity={self.similarity_score:.2f}>"


class HumanizationResult(Base):
    """Stores humanization rewrite results linked to an analysis."""

    __tablename__ = "humanization_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    humanized_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_ai_score: Mapped[float] = mapped_column(Float, nullable=False)
    humanized_ai_score: Mapped[float] = mapped_column(Float, nullable=False)
    iterations_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    strategy: Mapped[str] = mapped_column(
        String(64), nullable=False, default="ollama"
    )  # "ollama", "rule_based", "hybrid"
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )

    analysis: Mapped[Analysis] = relationship(back_populates="humanization_results")

    def __repr__(self) -> str:
        return (
            f"<HumanizationResult id={self.id!r} "
            f"original={self.original_ai_score:.2f} "
            f"humanized={self.humanized_ai_score:.2f}>"
        )


class BatchJob(Base):
    """Tracks batch-processing jobs (multi-file uploads)."""

    __tablename__ = "batch_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # "pending", "processing", "completed", "failed"
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    results_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<BatchJob id={self.id!r} status={self.status!r} "
            f"{self.processed_files}/{self.total_files}>"
        )

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "pending")
        kwargs.setdefault("processed_files", 0)
        kwargs.setdefault("failed_files", 0)
        super().__init__(**kwargs)


class AnalyticsResult(Base):
    """Stores the result of a text analytics analysis (readability, tone, grammar, etc.)."""

    __tablename__ = "analytics_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    analysis_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # "readability", "tone", "grammar", "statistics", "suggestions", "citations", "comparison", "full"
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    results_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )

    def __repr__(self) -> str:
        return f"<AnalyticsResult id={self.id!r} type={self.analysis_type!r}>"


class ApiUsage(Base):
    """Logs per-request API usage for rate limiting and analytics."""

    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(256), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="POST")
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<ApiUsage id={self.id} {self.method} {self.endpoint} " f"status={self.status_code}>"
        )
