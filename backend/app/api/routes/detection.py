"""
ClarityAI detection routes — AI-content detection with 14-signal deep analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db, async_session_factory
from app.db.models import Analysis, BatchJob

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DetectionOptions(BaseModel):
    include_sentence_scores: bool = True
    include_gltr_data: bool = True
    include_watermark_check: bool = True
    include_attribution: bool = True


class DetectionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    mode: str = Field(default="deep", pattern="^(deep|fast)$")
    options: DetectionOptions = Field(default_factory=DetectionOptions)


class FastDetectionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)


class BatchDetectionRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=50)
    mode: str = Field(default="deep", pattern="^(deep|fast)$")


class SignalResult(BaseModel):
    signal: str
    ai_probability: float
    confidence: str
    details: Optional[Dict[str, Any]] = None


class SentenceScore(BaseModel):
    sentence: str
    ai_probability: float
    highlight: str  # "high" | "medium" | "low"


class DetectionResponse(BaseModel):
    analysis_id: str
    overall_score: float
    classification: str
    confidence: str
    signals: List[SignalResult]
    sentence_analysis: Optional[List[SentenceScore]] = None
    gltr_tokens: Optional[List[Dict[str, Any]]] = None
    attribution: Optional[Dict[str, Any]] = None
    word_count: int
    processing_time_ms: int
    model_version: str


class BatchJobResponse(BaseModel):
    batch_id: str
    status: str
    total_texts: int
    message: str


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    results: Optional[List[Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Internal helpers — lazy-loaded ML pipeline
# ---------------------------------------------------------------------------

_detectors_cache: Dict[str, Any] = {}


def _get_detectors():
    """Lazy-load detectors to avoid import-time model loading."""
    if not _detectors_cache:
        try:
            from app.ml.detectors import (  # type: ignore[attr-defined]
                PerplexityDetector,
                ZeroShotDetector,
                GLTRDetector,
                EntropyDetector,
                BurstinessDetector,
                RepetitionDetector,
                VocabularyRichnessDetector,
                SentenceLengthDetector,
                CoherenceDetector,
                PunctuationDetector,
                ReadabilityDetector,
                NamedEntityDetector,
                POSPatternDetector,
                WatermarkDetector,
            )

            _detectors_cache["all"] = [
                PerplexityDetector(),
                ZeroShotDetector(),
                GLTRDetector(),
                EntropyDetector(),
                BurstinessDetector(),
                RepetitionDetector(),
                VocabularyRichnessDetector(),
                SentenceLengthDetector(),
                CoherenceDetector(),
                PunctuationDetector(),
                ReadabilityDetector(),
                NamedEntityDetector(),
                POSPatternDetector(),
                WatermarkDetector(),
            ]
            _detectors_cache["fast"] = [
                _detectors_cache["all"][0],  # perplexity
                _detectors_cache["all"][1],  # zero_shot
                _detectors_cache["all"][2],  # gltr
            ]
        except ImportError:
            logger.warning("ML detectors not yet implemented — using stubs")
            _detectors_cache["all"] = []
            _detectors_cache["fast"] = []
    return _detectors_cache


def _get_ensemble():
    """Lazy-load ensemble meta-learner."""
    try:
        from app.ml.ensemble import MetaLearner  # type: ignore[attr-defined]

        return MetaLearner()
    except ImportError:
        logger.warning("Ensemble meta-learner not yet implemented — using average")
        return None


def _get_sentence_analyzer():
    """Lazy-load sentence-level analyzer."""
    try:
        from app.ml.detectors import SentenceLevelAnalyzer  # type: ignore[attr-defined]

        return SentenceLevelAnalyzer()
    except ImportError:
        logger.warning("Sentence-level analyzer not yet implemented")
        return None


async def _run_detector(detector: Any, text: str) -> dict:
    """Run a single detector in a thread pool (they are CPU-bound)."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, detector.analyze, text)
        return result
    except Exception as exc:
        logger.error("Detector %s failed: %s", type(detector).__name__, exc)
        return {
            "signal": getattr(detector, "signal_name", type(detector).__name__),
            "ai_probability": 0.5,
            "confidence": "low",
            "error": str(exc),
        }


def _classify(score: float) -> str:
    """Classify overall AI score into a human-readable label."""
    if score >= settings.AI_THRESHOLD_HIGH:
        return "ai_generated"
    elif score >= settings.AI_THRESHOLD_MEDIUM:
        return "mixed"
    else:
        return "human_written"


def _overall_confidence(signals: List[dict]) -> str:
    """Aggregate confidence across signals."""
    if not signals:
        return "low"
    conf_map = {"high": 3, "medium": 2, "low": 1}
    avg = sum(conf_map.get(s.get("confidence", "low"), 1) for s in signals) / len(signals)
    if avg >= 2.5:
        return "high"
    elif avg >= 1.5:
        return "medium"
    return "low"


def _combine_scores(signals: List[dict], ensemble: Any) -> float:
    """Combine signal scores via ensemble or simple weighted average."""
    if not signals:
        return 0.5
    probs = [s["ai_probability"] for s in signals]
    if ensemble is not None:
        try:
            return ensemble.predict(signals)
        except Exception:
            pass
    # Fallback: weighted average (perplexity & zero-shot get 2x weight)
    weights = []
    for s in signals:
        name = s.get("signal", "").lower()
        if name in ("perplexity", "zero_shot", "gltr"):
            weights.append(2.0)
        else:
            weights.append(1.0)
    total_w = sum(weights)
    return sum(p * w for p, w in zip(probs, weights)) / total_w if total_w else 0.5


async def _run_full_detection(
    text: str,
    mode: str,
    options: DetectionOptions,
) -> Dict[str, Any]:
    """Core detection pipeline shared by /detect and /detect/fast."""
    start = time.perf_counter()
    word_count = len(text.split())

    if word_count < settings.MIN_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Text too short: {word_count} words (minimum {settings.MIN_WORDS})",
        )
    if word_count > settings.MAX_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Text too long: {word_count} words (maximum {settings.MAX_WORDS})",
        )

    detectors_map = _get_detectors()
    ensemble = _get_ensemble()

    detector_list = detectors_map.get("fast" if mode == "fast" else "all", [])

    # Run all detectors in parallel
    if detector_list:
        signal_results = await asyncio.gather(*[_run_detector(d, text) for d in detector_list])
    else:
        # Stub results when detectors are not yet implemented
        signal_results = [
            {"signal": "perplexity", "ai_probability": 0.5, "confidence": "low"},
            {"signal": "zero_shot", "ai_probability": 0.5, "confidence": "low"},
            {"signal": "gltr", "ai_probability": 0.5, "confidence": "low"},
        ]

    overall_score = _combine_scores(signal_results, ensemble)
    classification = _classify(overall_score)
    confidence = _overall_confidence(signal_results)

    # Sentence-level analysis
    sentence_analysis = None
    if options.include_sentence_scores:
        analyzer = _get_sentence_analyzer()
        if analyzer is not None:
            loop = asyncio.get_running_loop()
            try:
                raw = await loop.run_in_executor(None, analyzer.analyze, text)
                sentence_analysis = [
                    {
                        "sentence": s["sentence"],
                        "ai_probability": s["ai_probability"],
                        "highlight": (
                            "high"
                            if s["ai_probability"] >= 0.75
                            else "medium" if s["ai_probability"] >= 0.4 else "low"
                        ),
                    }
                    for s in raw
                ]
            except Exception as exc:
                logger.error("Sentence analysis failed: %s", exc)

    # GLTR token data
    gltr_tokens = None
    if options.include_gltr_data:
        for sr in signal_results:
            if sr.get("signal") == "gltr" and "tokens" in sr:
                gltr_tokens = sr["tokens"]
                break

    # Attribution
    attribution = None
    if options.include_attribution:
        for sr in signal_results:
            if sr.get("signal") == "zero_shot" and "model_scores" in sr:
                best = max(sr["model_scores"], key=lambda m: m.get("score", 0))
                attribution = {
                    "likely_model": best.get("model", "unknown"),
                    "model_confidence": best.get("score", 0.0),
                    "all_model_scores": sr["model_scores"],
                }
                break

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return {
        "overall_score": round(overall_score, 4),
        "classification": classification,
        "confidence": confidence,
        "signals": signal_results,
        "sentence_analysis": sentence_analysis,
        "gltr_tokens": gltr_tokens,
        "attribution": attribution,
        "word_count": word_count,
        "processing_time_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/detect", response_model=DetectionResponse)
async def detect(
    request: DetectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Full 14-signal AI content detection (or fast 3-signal if mode='fast')."""
    result = await _run_full_detection(request.text, request.mode, request.options)

    # Persist to database
    analysis = Analysis(
        id=uuid.uuid4().hex,
        input_text=request.text,
        word_count=result["word_count"],
        overall_ai_score=result["overall_score"],
        classification=result["classification"],
        confidence=(
            0.95
            if result["confidence"] == "high"
            else 0.7 if result["confidence"] == "medium" else 0.4
        ),
        signals_json=json.dumps(result["signals"]),
        sentence_scores_json=(
            json.dumps(result["sentence_analysis"]) if result["sentence_analysis"] else None
        ),
        gltr_data_json=json.dumps(result["gltr_tokens"]) if result["gltr_tokens"] else None,
        attribution_model=result["attribution"]["likely_model"] if result["attribution"] else None,
        processing_time_ms=result["processing_time_ms"],
        model_version=settings.APP_VERSION,
    )
    db.add(analysis)
    await db.flush()

    return DetectionResponse(
        analysis_id=analysis.id,
        overall_score=result["overall_score"],
        classification=result["classification"],
        confidence=result["confidence"],
        signals=[
            SignalResult(
                signal=s.get("signal", "unknown"),
                ai_probability=s.get("ai_probability", 0.5),
                confidence=s.get("confidence", "low"),
                details={
                    k: v
                    for k, v in s.items()
                    if k not in ("signal", "ai_probability", "confidence")
                },
            )
            for s in result["signals"]
        ],
        sentence_analysis=(
            [SentenceScore(**s) for s in result["sentence_analysis"]]
            if result["sentence_analysis"]
            else None
        ),
        gltr_tokens=result["gltr_tokens"],
        attribution=result["attribution"],
        word_count=result["word_count"],
        processing_time_ms=result["processing_time_ms"],
        model_version=settings.APP_VERSION,
    )


@router.post("/detect/fast", response_model=DetectionResponse)
async def detect_fast(
    request: FastDetectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Quick 3-signal detection (perplexity + zero_shot + gltr)."""
    options = DetectionOptions(
        include_sentence_scores=False,
        include_gltr_data=True,
        include_watermark_check=False,
        include_attribution=False,
    )
    result = await _run_full_detection(request.text, "fast", options)

    analysis = Analysis(
        id=uuid.uuid4().hex,
        input_text=request.text,
        word_count=result["word_count"],
        overall_ai_score=result["overall_score"],
        classification=result["classification"],
        confidence=(
            0.95
            if result["confidence"] == "high"
            else 0.7 if result["confidence"] == "medium" else 0.4
        ),
        signals_json=json.dumps(result["signals"]),
        gltr_data_json=json.dumps(result["gltr_tokens"]) if result["gltr_tokens"] else None,
        processing_time_ms=result["processing_time_ms"],
        model_version=settings.APP_VERSION,
    )
    db.add(analysis)
    await db.flush()

    return DetectionResponse(
        analysis_id=analysis.id,
        overall_score=result["overall_score"],
        classification=result["classification"],
        confidence=result["confidence"],
        signals=[
            SignalResult(
                signal=s.get("signal", "unknown"),
                ai_probability=s.get("ai_probability", 0.5),
                confidence=s.get("confidence", "low"),
                details={
                    k: v
                    for k, v in s.items()
                    if k not in ("signal", "ai_probability", "confidence")
                },
            )
            for s in result["signals"]
        ],
        sentence_analysis=None,
        gltr_tokens=result["gltr_tokens"],
        attribution=None,
        word_count=result["word_count"],
        processing_time_ms=result["processing_time_ms"],
        model_version=settings.APP_VERSION,
    )


@router.get("/detect/{analysis_id}", response_model=DetectionResponse)
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a previously stored analysis by ID."""
    stmt = select(Analysis).where(Analysis.id == analysis_id)
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    signals_raw: List[dict] = json.loads(analysis.signals_json) if analysis.signals_json else []
    sentence_scores = (
        json.loads(analysis.sentence_scores_json) if analysis.sentence_scores_json else None
    )
    gltr_tokens = json.loads(analysis.gltr_data_json) if analysis.gltr_data_json else None

    attribution = None
    if analysis.attribution_model:
        attribution = {
            "likely_model": analysis.attribution_model,
            "model_confidence": None,
            "all_model_scores": [],
        }

    confidence_label = (
        "high" if analysis.confidence >= 0.85 else "medium" if analysis.confidence >= 0.5 else "low"
    )

    return DetectionResponse(
        analysis_id=analysis.id,
        overall_score=analysis.overall_ai_score,
        classification=analysis.classification,
        confidence=confidence_label,
        signals=[
            SignalResult(
                signal=s.get("signal", "unknown"),
                ai_probability=s.get("ai_probability", 0.5),
                confidence=s.get("confidence", "low"),
                details={
                    k: v
                    for k, v in s.items()
                    if k not in ("signal", "ai_probability", "confidence")
                },
            )
            for s in signals_raw
        ],
        sentence_analysis=(
            [SentenceScore(**s) for s in sentence_scores] if sentence_scores else None
        ),
        gltr_tokens=gltr_tokens,
        attribution=attribution,
        word_count=analysis.word_count,
        processing_time_ms=analysis.processing_time_ms,
        model_version=analysis.model_version,
    )


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


async def _process_batch(batch_id: str, texts: List[str], mode: str):
    """Background task that processes each text and updates the batch job row."""
    options = (
        DetectionOptions()
        if mode == "deep"
        else DetectionOptions(
            include_sentence_scores=False,
            include_watermark_check=False,
            include_attribution=False,
        )
    )
    results: List[Dict[str, Any]] = []
    processed = 0
    failed = 0

    async with async_session_factory() as db:
        # Mark as processing
        stmt = select(BatchJob).where(BatchJob.id == batch_id)
        row = (await db.execute(stmt)).scalar_one()
        row.status = "processing"
        row.started_at = datetime.now(timezone.utc)
        await db.commit()

        for text in texts:
            try:
                det = await _run_full_detection(text, mode, options)

                analysis = Analysis(
                    id=uuid.uuid4().hex,
                    input_text=text,
                    word_count=det["word_count"],
                    overall_ai_score=det["overall_score"],
                    classification=det["classification"],
                    confidence=(
                        0.95
                        if det["confidence"] == "high"
                        else 0.7 if det["confidence"] == "medium" else 0.4
                    ),
                    signals_json=json.dumps(det["signals"]),
                    sentence_scores_json=(
                        json.dumps(det["sentence_analysis"]) if det["sentence_analysis"] else None
                    ),
                    gltr_data_json=json.dumps(det["gltr_tokens"]) if det["gltr_tokens"] else None,
                    processing_time_ms=det["processing_time_ms"],
                    model_version=settings.APP_VERSION,
                )
                db.add(analysis)
                await db.flush()

                results.append(
                    {
                        "analysis_id": analysis.id,
                        "overall_score": det["overall_score"],
                        "classification": det["classification"],
                        "word_count": det["word_count"],
                        "processing_time_ms": det["processing_time_ms"],
                    }
                )
                processed += 1
            except Exception as exc:
                logger.error("Batch item failed: %s", exc)
                results.append({"error": str(exc)})
                failed += 1

        # Finalize batch
        row = (await db.execute(stmt)).scalar_one()
        row.status = "completed" if failed == 0 else "completed"
        row.processed_files = processed
        row.failed_files = failed
        row.results_json = json.dumps(results)
        row.completed_at = datetime.now(timezone.utc)
        if failed > 0 and processed == 0:
            row.status = "failed"
            row.error_message = "All items failed"
        await db.commit()


@router.post("/detect/batch", response_model=BatchJobResponse)
async def detect_batch(
    request: BatchDetectionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit a batch of texts for processing. Returns immediately with a batch job ID."""
    if len(request.texts) > settings.BATCH_MAX_FILES:
        raise HTTPException(
            status_code=422,
            detail=f"Too many texts: {len(request.texts)} (max {settings.BATCH_MAX_FILES})",
        )

    batch = BatchJob(
        id=uuid.uuid4().hex,
        status="pending",
        total_files=len(request.texts),
        processed_files=0,
        failed_files=0,
    )
    db.add(batch)
    await db.flush()
    batch_id = batch.id

    background_tasks.add_task(_process_batch, batch_id, request.texts, request.mode)

    return BatchJobResponse(
        batch_id=batch_id,
        status="pending",
        total_texts=len(request.texts),
        message="Batch job created. Poll GET /detect/batch/{batch_id} for status.",
    )


@router.get("/detect/batch/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check the status of a batch detection job."""
    stmt = select(BatchJob).where(BatchJob.id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()

    if batch is None:
        raise HTTPException(status_code=404, detail="Batch job not found")

    return BatchStatusResponse(
        batch_id=batch.id,
        status=batch.status,
        total_files=batch.total_files,
        processed_files=batch.processed_files,
        failed_files=batch.failed_files,
        results=json.loads(batch.results_json) if batch.results_json else None,
    )
