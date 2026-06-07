"""
ClarityAI health and history routes — system status and analysis history.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Analysis

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level start time for uptime tracking
_startup_time: float = time.time()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    model_version: str
    uptime_seconds: float
    loaded_models: int
    ollama_available: bool
    database: str
    timestamp: str


class AnalysisSummary(BaseModel):
    analysis_id: str
    classification: str
    overall_ai_score: float
    word_count: int
    processing_time_ms: int
    model_version: str
    created_at: str


class HistoryResponse(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    results: List[AnalysisSummary]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Returns system status including uptime, loaded model count, and Ollama availability."""
    # Count loaded models via the registry (safe even if no models loaded)
    loaded_count = 0
    try:
        from app.ml.models.model_registry import ModelRegistry

        registry = ModelRegistry()
        loaded_count = len(registry._models) + len(registry._tokenizers) + len(registry._pipelines)
    except Exception:
        pass

    # Check Ollama
    ollama_available = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_available = resp.status_code == 200
    except Exception:
        pass

    uptime = time.time() - _startup_time

    return HealthResponse(
        status="healthy",
        model_version=settings.APP_VERSION,
        uptime_seconds=round(uptime, 2),
        loaded_models=loaded_count,
        ollama_available=ollama_available,
        database="sqlite (aiosqlite)",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/history", response_model=HistoryResponse)
async def analysis_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query(
        default="created_at",
        pattern="^(created_at|overall_ai_score|word_count|processing_time_ms)$",
        description="Column to sort by",
    ),
    min_score: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum AI score filter",
    ),
    max_score: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum AI score filter",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of past analyses with optional score filtering."""
    # Base query
    base_filter = select(Analysis)

    if min_score is not None:
        base_filter = base_filter.where(Analysis.overall_ai_score >= min_score)
    if max_score is not None:
        base_filter = base_filter.where(Analysis.overall_ai_score <= max_score)

    # Total count
    count_stmt = select(func.count()).select_from(base_filter.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    total_pages = max(1, (total + limit - 1) // limit)

    if page > total_pages and total > 0:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page} does not exist (total pages: {total_pages})",
        )

    # Sorting
    sort_column_map = {
        "created_at": Analysis.created_at,
        "overall_ai_score": Analysis.overall_ai_score,
        "word_count": Analysis.word_count,
        "processing_time_ms": Analysis.processing_time_ms,
    }
    sort_col = sort_column_map.get(sort_by, Analysis.created_at)

    # Fetch page
    offset = (page - 1) * limit
    data_stmt = base_filter.order_by(desc(sort_col)).offset(offset).limit(limit)
    data_result = await db.execute(data_stmt)
    rows = data_result.scalars().all()

    results = [
        AnalysisSummary(
            analysis_id=row.id,
            classification=row.classification,
            overall_ai_score=row.overall_ai_score,
            word_count=row.word_count,
            processing_time_ms=row.processing_time_ms,
            model_version=row.model_version,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in rows
    ]

    return HistoryResponse(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        results=results,
    )
