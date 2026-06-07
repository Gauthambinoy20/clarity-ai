"""
ClarityAI dashboard analytics API.

GET /dashboard/stats   -- aggregate statistics
GET /dashboard/trends  -- time-series and distribution data
GET /dashboard/top-signals -- most frequently fired detection signals
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DashboardStatsResponse(BaseModel):
    total_analyses: int
    average_ai_score: float
    total_words_analyzed: int
    analyses_today: int
    analyses_this_week: int
    analyses_this_month: int


class TrendPoint(BaseModel):
    date: str
    count: int


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class ClassificationCount(BaseModel):
    classification: str
    count: int


class DashboardTrendsResponse(BaseModel):
    ai_score_histogram: List[HistogramBin]
    analyses_per_day: List[TrendPoint]
    most_common_classifications: List[ClassificationCount]


class SignalStat(BaseModel):
    signal_name: str
    fire_count: int
    average_score: float


class DashboardTopSignalsResponse(BaseModel):
    signals: List[SignalStat]


# ---------------------------------------------------------------------------
# Helper: compute time boundaries
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _start_of_today() -> datetime:
    now = _utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week() -> datetime:
    today = _start_of_today()
    return today - timedelta(days=today.weekday())  # Monday


def _start_of_month() -> datetime:
    today = _start_of_today()
    return today.replace(day=1)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Return aggregate dashboard statistics."""

    # Use raw SQL for aggregate queries on SQLite to avoid ORM quirks
    total_result = await db.execute(text("SELECT COUNT(*) FROM analyses"))
    total_analyses = total_result.scalar() or 0

    # Average AI score
    avg_result = await db.execute(text("SELECT AVG(overall_ai_score) FROM analyses"))
    average_ai_score = avg_result.scalar() or 0.0

    # Total words analyzed
    words_result = await db.execute(text("SELECT COALESCE(SUM(word_count), 0) FROM analyses"))
    total_words = words_result.scalar() or 0

    # Analyses today
    today_start = _start_of_today().isoformat()
    today_result = await db.execute(
        text("SELECT COUNT(*) FROM analyses WHERE created_at >= :ts"),
        {"ts": today_start},
    )
    analyses_today = today_result.scalar() or 0

    # Analyses this week
    week_start = _start_of_week().isoformat()
    week_result = await db.execute(
        text("SELECT COUNT(*) FROM analyses WHERE created_at >= :ts"),
        {"ts": week_start},
    )
    analyses_this_week = week_result.scalar() or 0

    # Analyses this month
    month_start = _start_of_month().isoformat()
    month_result = await db.execute(
        text("SELECT COUNT(*) FROM analyses WHERE created_at >= :ts"),
        {"ts": month_start},
    )
    analyses_this_month = month_result.scalar() or 0

    return DashboardStatsResponse(
        total_analyses=total_analyses,
        average_ai_score=round(float(average_ai_score), 4),
        total_words_analyzed=int(total_words),
        analyses_today=analyses_today,
        analyses_this_week=analyses_this_week,
        analyses_this_month=analyses_this_month,
    )


@router.get("/dashboard/trends", response_model=DashboardTrendsResponse)
async def dashboard_trends(db: AsyncSession = Depends(get_db)):
    """
    Return trend data:
    - AI score distribution histogram (10 bins)
    - Analyses per day (last 30 days)
    - Most common classifications
    """

    # 1. AI score histogram (10 bins: 0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
    histogram: List[HistogramBin] = []
    for i in range(10):
        bin_start = i / 10.0
        bin_end = (i + 1) / 10.0
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM analyses "
                "WHERE overall_ai_score >= :lo AND overall_ai_score < :hi"
            ),
            {"lo": bin_start, "hi": bin_end},
        )
        count = result.scalar() or 0
        histogram.append(
            HistogramBin(
                bin_start=round(bin_start, 1),
                bin_end=round(bin_end, 1),
                count=count,
            )
        )

    # Handle the edge case for score == 1.0 (include in last bin)
    result = await db.execute(text("SELECT COUNT(*) FROM analyses WHERE overall_ai_score = 1.0"))
    extra = result.scalar() or 0
    if histogram:
        histogram[-1].count += extra

    # 2. Analyses per day (last 30 days)
    thirty_days_ago = (_utcnow() - timedelta(days=30)).isoformat()
    daily_result = await db.execute(
        text(
            "SELECT DATE(created_at) as day, COUNT(*) as cnt "
            "FROM analyses "
            "WHERE created_at >= :since "
            "GROUP BY DATE(created_at) "
            "ORDER BY day ASC"
        ),
        {"since": thirty_days_ago},
    )
    analyses_per_day = [
        TrendPoint(date=str(row[0]), count=row[1]) for row in daily_result.fetchall()
    ]

    # 3. Most common classifications
    class_result = await db.execute(
        text(
            "SELECT classification, COUNT(*) as cnt "
            "FROM analyses "
            "GROUP BY classification "
            "ORDER BY cnt DESC "
            "LIMIT 10"
        )
    )
    classifications = [
        ClassificationCount(classification=row[0], count=row[1]) for row in class_result.fetchall()
    ]

    return DashboardTrendsResponse(
        ai_score_histogram=histogram,
        analyses_per_day=analyses_per_day,
        most_common_classifications=classifications,
    )


@router.get("/dashboard/top-signals", response_model=DashboardTopSignalsResponse)
async def dashboard_top_signals(db: AsyncSession = Depends(get_db)):
    """
    Return which detection signals fire most often and their average scores.

    Parses the JSON stored in analyses.signals_json to extract signal data.
    """
    # Fetch all signals_json blobs (limit to recent 1000 for performance)
    rows_result = await db.execute(
        text(
            "SELECT signals_json FROM analyses "
            "WHERE signals_json IS NOT NULL "
            "ORDER BY created_at DESC "
            "LIMIT 1000"
        )
    )
    rows = rows_result.fetchall()

    # Aggregate signal statistics
    signal_counts: Dict[str, int] = {}
    signal_score_sums: Dict[str, float] = {}

    for (signals_json_str,) in rows:
        if not signals_json_str:
            continue
        try:
            signals_data = json.loads(signals_json_str)
        except (json.JSONDecodeError, TypeError):
            continue

        # signals_data may be a list of signal dicts or a dict of signal_name -> result
        signal_list: List[Dict[str, Any]] = []

        if isinstance(signals_data, list):
            signal_list = signals_data
        elif isinstance(signals_data, dict):
            # Could be {signal_name: {ai_probability: ...}} or a single result
            for key, val in signals_data.items():
                if isinstance(val, dict):
                    val["signal"] = val.get("signal", key)
                    signal_list.append(val)

        for sig in signal_list:
            name = sig.get("signal", "unknown")
            ai_prob = sig.get("ai_probability")
            if ai_prob is None:
                continue

            try:
                score = float(ai_prob)
            except (ValueError, TypeError):
                continue

            signal_counts[name] = signal_counts.get(name, 0) + 1
            signal_score_sums[name] = signal_score_sums.get(name, 0.0) + score

    # Build response sorted by fire count
    signals: List[SignalStat] = []
    for name in sorted(signal_counts, key=lambda n: signal_counts[n], reverse=True):
        count = signal_counts[name]
        avg = signal_score_sums[name] / count if count > 0 else 0.0
        signals.append(
            SignalStat(
                signal_name=name,
                fire_count=count,
                average_score=round(avg, 4),
            )
        )

    return DashboardTopSignalsResponse(signals=signals)
