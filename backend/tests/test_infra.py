"""
Unit tests for backend infrastructure:

  - app/core/rate_limiter.py  -- token-bucket limiting (time injected, no sleep).
  - app/core/websocket.py     -- connection bookkeeping and targeted sends.
  - app/db/models.py + database.py -- CRUD over all six models on an isolated
    in-memory sqlite engine (NOT the app's global engine), batch-job status
    transitions, and JSON-column round-trips.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload


# ===========================================================================
# Rate limiter -- time is injected via monkeypatch, never slept
# ===========================================================================


def _clock(monkeypatch, start=100.0):
    """Install a controllable monotonic clock on the rate_limiter module.

    Returns a dict whose ``t`` key is the current fake time; bump it to
    advance the clock without sleeping.
    """
    from app.core import rate_limiter

    clock = {"t": start}
    monkeypatch.setattr(rate_limiter.time, "monotonic", lambda: clock["t"])
    return clock


def _store_clock(monkeypatch):
    """Controllable clock anchored to the real monotonic value.

    The store creates TokenBuckets internally, and their last_refill is set
    by the default_factory using the real time.monotonic. Anchoring our fake
    clock to that same real value keeps the elapsed-time maths consistent, so
    advancing clock["t"] later simulates the passage of time without sleeping.
    """
    from app.core import rate_limiter

    # Anchor a little ahead of real time so that the elapsed since a bucket's
    # real-time last_refill is non-negative; the bucket then refills back to
    # its capacity, keeping token counts exact instead of off-by-epsilon.
    clock = {"t": rate_limiter.time.monotonic() + 1000.0}
    monkeypatch.setattr(rate_limiter.time, "monotonic", lambda: clock["t"])
    return clock


def _frozen_bucket(monkeypatch, capacity, refill_rate, clock=None):
    """Build a TokenBucket whose last_refill is pinned to the fake clock.

    TokenBucket.last_refill is filled by a default_factory that captured the
    real time.monotonic, so we overwrite it to align with our fake clock.
    """
    from app.core import rate_limiter

    if clock is None:
        clock = _clock(monkeypatch)
    b = rate_limiter.TokenBucket(capacity=capacity, refill_rate=refill_rate)
    b.last_refill = clock["t"]
    return b


class TestTokenBucket:
    def test_starts_full(self):
        from app.core.rate_limiter import TokenBucket

        b = TokenBucket(capacity=5, refill_rate=1.0)
        assert b.tokens == 5

    def test_consume_under_limit_allows(self, monkeypatch):
        from app.core import rate_limiter

        b = _frozen_bucket(monkeypatch, capacity=3, refill_rate=1.0)
        allowed, retry = b.consume()
        assert allowed is True
        assert retry == 0.0

    def test_consume_at_limit_blocks(self, monkeypatch):
        from app.core import rate_limiter

        # Frozen clock -> no refill happens between consumes.
        b = _frozen_bucket(monkeypatch, capacity=2, refill_rate=1.0)
        assert b.consume()[0] is True
        assert b.consume()[0] is True
        allowed, retry = b.consume()
        assert allowed is False
        assert retry > 0.0

    def test_window_expiry_restores_tokens(self, monkeypatch):
        from app.core import rate_limiter

        clock = _clock(monkeypatch, start=100.0)
        b = _frozen_bucket(monkeypatch, capacity=1, refill_rate=1.0, clock=clock)

        assert b.consume()[0] is True
        assert b.consume()[0] is False  # empty
        # Advance two seconds -> one token refilled (rate is 1/s, cap is 1).
        clock["t"] = 102.0
        assert b.consume()[0] is True

    def test_refill_capped_at_capacity(self, monkeypatch):
        clock = _clock(monkeypatch, start=100.0)
        b = _frozen_bucket(monkeypatch, capacity=2, refill_rate=1.0, clock=clock)
        b.consume()  # one used
        clock["t"] = 1000.0  # huge gap
        # Refill cannot exceed capacity, so only 2 tokens available, not hundreds.
        assert b.consume()[0] is True
        assert b.consume()[0] is True
        assert b.consume()[0] is False

    def test_retry_after_uses_refill_rate(self, monkeypatch):
        b = _frozen_bucket(monkeypatch, capacity=1, refill_rate=0.5)
        b.consume()
        allowed, retry = b.consume()
        assert allowed is False
        # deficit 1 token at 0.5/s -> ~2s.
        assert retry == pytest.approx(2.0)


class TestRateLimiterStore:
    def test_default_config_used_for_unknown_path(self):
        from app.core.rate_limiter import RateLimiterStore

        store = RateLimiterStore(default_capacity=4, default_refill_rate=1.0)
        cfg = store._get_config("/random/path")
        assert cfg.capacity == 4

    def test_most_specific_endpoint_config_wins(self):
        from app.core.rate_limiter import RateLimiterStore

        store = RateLimiterStore()
        store.configure_endpoint("/api", capacity=10, refill_rate=1.0)
        store.configure_endpoint("/api/v1/detect", capacity=3, refill_rate=0.1)
        cfg = store._get_config("/api/v1/detect/now")
        assert cfg.capacity == 3

    def test_under_limit_allows(self, monkeypatch):
        from app.core import rate_limiter

        _store_clock(monkeypatch)
        store = rate_limiter.RateLimiterStore(default_capacity=3, default_refill_rate=1.0)
        allowed, _, remaining = store.check("1.1.1.1", "/x")
        assert allowed is True
        assert remaining == 2

    def test_burst_then_block(self, monkeypatch):
        from app.core import rate_limiter

        _store_clock(monkeypatch)
        store = rate_limiter.RateLimiterStore(default_capacity=3, default_refill_rate=1.0)
        outcomes = [store.check("1.1.1.1", "/x")[0] for _ in range(4)]
        assert outcomes == [True, True, True, False]

    def test_per_client_isolation(self, monkeypatch):
        from app.core import rate_limiter

        _store_clock(monkeypatch)
        store = rate_limiter.RateLimiterStore(default_capacity=1, default_refill_rate=1.0)
        # First client exhausts its bucket; second client is unaffected.
        assert store.check("1.1.1.1", "/x")[0] is True
        assert store.check("1.1.1.1", "/x")[0] is False
        assert store.check("2.2.2.2", "/x")[0] is True

    def test_endpoints_have_separate_buckets(self, monkeypatch):
        from app.core import rate_limiter

        _store_clock(monkeypatch)
        store = rate_limiter.RateLimiterStore(default_capacity=1, default_refill_rate=1.0)
        store.configure_endpoint("/a", capacity=1, refill_rate=1.0)
        store.configure_endpoint("/b", capacity=1, refill_rate=1.0)
        assert store.check("1.1.1.1", "/a")[0] is True
        assert store.check("1.1.1.1", "/a")[0] is False
        # Different endpoint prefix -> fresh bucket.
        assert store.check("1.1.1.1", "/b")[0] is True

    def test_window_expiry_restores(self, monkeypatch):
        from app.core import rate_limiter

        clock = _store_clock(monkeypatch)
        store = rate_limiter.RateLimiterStore(default_capacity=1, default_refill_rate=1.0)
        assert store.check("1.1.1.1", "/x")[0] is True
        assert store.check("1.1.1.1", "/x")[0] is False
        clock["t"] += 2.0
        assert store.check("1.1.1.1", "/x")[0] is True


# ===========================================================================
# WebSocket connection manager -- AsyncMock sockets, no real server
# ===========================================================================


def _fake_ws():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_registers_and_accepts(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws = _fake_ws()
        await m.connect(ws, client_id="c1", channel="room")
        ws.accept.assert_awaited_once()
        assert m.active_connection_count == 1
        assert "room" in m.channels

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws = _fake_ws()
        await m.connect(ws, client_id="c1", channel="room")
        m.disconnect(ws, client_id="c1", channel="room")
        assert m.active_connection_count == 0
        assert m.channels == []

    @pytest.mark.asyncio
    async def test_disconnect_without_channel_removes_from_all(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws = _fake_ws()
        await m.connect(ws, client_id="c1", channel="room")
        m.disconnect(ws)  # no channel arg -> scrub from every channel
        assert m.channels == []
        assert m.active_connection_count == 0

    @pytest.mark.asyncio
    async def test_send_to_client_targets_right_socket(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws1, ws2 = _fake_ws(), _fake_ws()
        await m.connect(ws1, client_id="c1")
        await m.connect(ws2, client_id="c2")

        sent = await m.send_to_client("c2", {"hello": "world"})
        assert sent is True
        ws2.send_json.assert_awaited_once_with({"hello": "world"})
        ws1.send_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_to_missing_client_returns_false(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        assert await m.send_to_client("nobody", {"x": 1}) is False

    @pytest.mark.asyncio
    async def test_send_json_swallows_errors(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws = _fake_ws()
        ws.send_json.side_effect = RuntimeError("socket closed")
        # Should not raise even though the underlying send blows up.
        await m.send_json(ws, {"x": 1})

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws1, ws2 = _fake_ws(), _fake_ws()
        await m.connect(ws1)
        await m.connect(ws2)
        await m.broadcast({"msg": "hi"})
        ws1.send_json.assert_awaited_once_with({"msg": "hi"})
        ws2.send_json.assert_awaited_once_with({"msg": "hi"})

    @pytest.mark.asyncio
    async def test_broadcast_drops_broken_connection(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        good, bad = _fake_ws(), _fake_ws()
        bad.send_json.side_effect = RuntimeError("disconnected mid-send")
        await m.connect(good)
        await m.connect(bad)

        await m.broadcast({"msg": "hi"})
        # Broken socket is pruned; the healthy one still got the message.
        assert m.active_connection_count == 1
        good.send_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_channel_only_hits_members(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        in_room, out_room = _fake_ws(), _fake_ws()
        await m.connect(in_room, channel="r1")
        await m.connect(out_room, channel="r2")

        await m.broadcast_to_channel("r1", {"msg": "scoped"})
        in_room.send_json.assert_awaited_once_with({"msg": "scoped"})
        out_room.send_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_progress_helper_computes_percent(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws = _fake_ws()
        await m.connect(ws, client_id="c1")
        await m.send_progress("c1", current_step=1, total_steps=4, message="step")
        payload = ws.send_json.await_args.args[0]
        assert payload["type"] == "progress"
        assert payload["progress_percent"] == 25.0

    @pytest.mark.asyncio
    async def test_completion_and_error_helpers(self):
        from app.core.websocket import ConnectionManager

        m = ConnectionManager()
        ws = _fake_ws()
        await m.connect(ws, client_id="c1")

        await m.send_completion("c1", "analysis-42", {"done": True})
        assert ws.send_json.await_args.args[0]["type"] == "complete"

        await m.send_error("c1", "bad things")
        assert ws.send_json.await_args.args[0]["type"] == "error"


# ===========================================================================
# Database -- isolated in-memory engine built inside the tests
# ===========================================================================


@pytest_asyncio.fixture
async def session():
    """Yield an AsyncSession bound to a private in-memory sqlite engine.

    We deliberately do NOT use the app's global engine; this keeps the tests
    hermetic and parallel-safe.
    """
    from app.db.database import Base
    import app.db.models  # noqa: F401  -- populate metadata

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess

    await engine.dispose()


class TestAnalysisCrud:
    @pytest.mark.asyncio
    async def test_create_and_read(self, session):
        from app.db.models import Analysis

        a = Analysis(
            input_text="hello world",
            word_count=2,
            overall_ai_score=0.4,
            classification="human_written",
            confidence=0.8,
        )
        session.add(a)
        await session.commit()

        fetched = await session.get(Analysis, a.id)
        assert fetched is not None
        assert fetched.classification == "human_written"
        assert len(fetched.id) == 32  # auto-generated uuid hex
        assert fetched.model_version == "v1"  # default applied

    @pytest.mark.asyncio
    async def test_update(self, session):
        from app.db.models import Analysis

        a = Analysis(
            input_text="t",
            word_count=1,
            overall_ai_score=0.1,
            classification="human_written",
            confidence=0.5,
        )
        session.add(a)
        await session.commit()

        a.classification = "ai_generated"
        a.overall_ai_score = 0.95
        await session.commit()

        fetched = await session.get(Analysis, a.id)
        assert fetched.classification == "ai_generated"
        assert fetched.overall_ai_score == 0.95

    @pytest.mark.asyncio
    async def test_delete(self, session):
        from app.db.models import Analysis

        a = Analysis(
            input_text="t",
            word_count=1,
            overall_ai_score=0.1,
            classification="mixed",
            confidence=0.5,
        )
        session.add(a)
        await session.commit()
        aid = a.id

        await session.delete(a)
        await session.commit()
        assert await session.get(Analysis, aid) is None

    @pytest.mark.asyncio
    async def test_json_columns_round_trip(self, session):
        from app.db.models import Analysis

        signals = {"perplexity": 0.7, "burstiness": [1, 2, 3]}
        a = Analysis(
            input_text="t",
            word_count=1,
            overall_ai_score=0.1,
            classification="mixed",
            confidence=0.5,
            signals_json=json.dumps(signals),
        )
        session.add(a)
        await session.commit()

        fetched = await session.get(Analysis, a.id)
        assert json.loads(fetched.signals_json) == signals


class TestRelationshipsAndCascade:
    @pytest.mark.asyncio
    async def test_plagiarism_and_humanization_children(self, session):
        from app.db.models import Analysis, PlagiarismResult, HumanizationResult

        a = Analysis(
            input_text="parent",
            word_count=1,
            overall_ai_score=0.5,
            classification="mixed",
            confidence=0.5,
        )
        session.add(a)
        await session.commit()

        pr = PlagiarismResult(
            analysis_id=a.id,
            similarity_score=0.9,
            method="exact",
            details_json=json.dumps({"hits": 3}),
        )
        hr = HumanizationResult(
            analysis_id=a.id,
            original_text="orig",
            humanized_text="new",
            original_ai_score=0.9,
            humanized_ai_score=0.1,
            iterations_used=2,
            strategy="hybrid",
        )
        session.add_all([pr, hr])
        await session.commit()

        # Re-query with the relationships eager-loaded during the await so the
        # collections are populated before we touch them synchronously.
        session.expunge_all()
        stmt = (
            select(Analysis)
            .where(Analysis.id == a.id)
            .options(
                selectinload(Analysis.plagiarism_results),
                selectinload(Analysis.humanization_results),
            )
        )
        refreshed = (await session.execute(stmt)).scalar_one()
        assert len(refreshed.plagiarism_results) == 1
        assert len(refreshed.humanization_results) == 1
        assert json.loads(refreshed.plagiarism_results[0].details_json) == {"hits": 3}

    @pytest.mark.asyncio
    async def test_cascade_delete_removes_children(self, session):
        from app.db.models import Analysis, PlagiarismResult

        a = Analysis(
            input_text="parent",
            word_count=1,
            overall_ai_score=0.5,
            classification="mixed",
            confidence=0.5,
        )
        a.plagiarism_results.append(PlagiarismResult(similarity_score=0.7, method="semantic"))
        session.add(a)
        await session.commit()

        await session.delete(a)
        await session.commit()

        rows = (await session.execute(select(PlagiarismResult))).scalars().all()
        assert rows == []


class TestBatchJob:
    @pytest.mark.asyncio
    async def test_defaults_on_create(self, session):
        from app.db.models import BatchJob

        bj = BatchJob(total_files=5)
        session.add(bj)
        await session.commit()

        fetched = await session.get(BatchJob, bj.id)
        assert fetched.status == "pending"
        assert fetched.processed_files == 0
        assert fetched.failed_files == 0

    @pytest.mark.asyncio
    async def test_status_transitions_persist(self, session):
        from app.db.models import BatchJob

        bj = BatchJob(total_files=3)
        session.add(bj)
        await session.commit()

        # pending -> processing
        bj.status = "processing"
        bj.started_at = datetime.now(timezone.utc)
        await session.commit()
        assert (await session.get(BatchJob, bj.id)).status == "processing"

        # processing -> completed, with progress counters
        bj.status = "completed"
        bj.processed_files = 3
        bj.completed_at = datetime.now(timezone.utc)
        bj.results_json = json.dumps([{"file": "a.txt", "score": 0.2}])
        await session.commit()

        fetched = await session.get(BatchJob, bj.id)
        assert fetched.status == "completed"
        assert fetched.processed_files == 3
        assert fetched.completed_at is not None
        assert json.loads(fetched.results_json)[0]["file"] == "a.txt"

    @pytest.mark.asyncio
    async def test_failed_transition_records_error(self, session):
        from app.db.models import BatchJob

        bj = BatchJob(total_files=2)
        session.add(bj)
        await session.commit()

        bj.status = "failed"
        bj.failed_files = 2
        bj.error_message = "disk full"
        await session.commit()

        fetched = await session.get(BatchJob, bj.id)
        assert fetched.status == "failed"
        assert fetched.error_message == "disk full"


class TestAnalyticsResultCrud:
    @pytest.mark.asyncio
    async def test_create_and_query_by_type(self, session):
        from app.db.models import AnalyticsResult

        ar = AnalyticsResult(
            analysis_type="readability",
            input_text="some text",
            results_json=json.dumps({"flesch": 65.0}),
            processing_time_ms=12,
        )
        session.add(ar)
        await session.commit()

        rows = (
            (
                await session.execute(
                    select(AnalyticsResult).where(AnalyticsResult.analysis_type == "readability")
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert json.loads(rows[0].results_json)["flesch"] == 65.0


class TestApiUsageCrud:
    @pytest.mark.asyncio
    async def test_autoincrement_id_and_defaults(self, session):
        from app.db.models import ApiUsage

        u1 = ApiUsage(client_ip="1.2.3.4", endpoint="/api/v1/detect")
        u2 = ApiUsage(client_ip="1.2.3.4", endpoint="/api/v1/detect")
        session.add_all([u1, u2])
        await session.commit()

        assert u1.id is not None
        assert u2.id is not None
        assert u1.id != u2.id
        assert u1.method == "POST"  # default
        assert u1.status_code == 200  # default

    @pytest.mark.asyncio
    async def test_query_by_client_ip(self, session):
        from app.db.models import ApiUsage

        session.add_all(
            [
                ApiUsage(client_ip="9.9.9.9", endpoint="/a"),
                ApiUsage(client_ip="9.9.9.9", endpoint="/b"),
                ApiUsage(client_ip="8.8.8.8", endpoint="/c"),
            ]
        )
        await session.commit()

        rows = (
            (await session.execute(select(ApiUsage).where(ApiUsage.client_ip == "9.9.9.9")))
            .scalars()
            .all()
        )
        assert len(rows) == 2
