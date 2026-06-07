"""
ClarityAI plagiarism routes — web, academic, and semantic plagiarism analysis.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Analysis, PlagiarismResult

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class PlagiarismOptions(BaseModel):
    search_web: bool = True
    search_academic: bool = True
    search_wikipedia: bool = True
    semantic_matching: bool = True


class PlagiarismRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    options: PlagiarismOptions = Field(default_factory=PlagiarismOptions)


class SourceMatch(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    matched_text: str
    similarity_score: float
    method: str  # "exact" | "fuzzy" | "semantic"


class ParagraphAnalysis(BaseModel):
    paragraph_index: int
    text: str
    plagiarism_score: float
    sources: List[SourceMatch]


class PlagiarismResponse(BaseModel):
    result_id: str
    overall_plagiarism_score: float
    originality_percentage: float
    paragraph_analysis: List[ParagraphAnalysis]
    sources_found: List[SourceMatch]
    total_sources: int
    word_count: int
    processing_time_ms: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_paragraphs(text: str) -> List[str]:
    """Split text into non-empty paragraphs."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _chunk_text(text: str, chunk_size: int = 3) -> List[str]:
    """Split text into overlapping sentence chunks for search queries."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= chunk_size:
        return [text]
    chunks = []
    for i in range(0, len(sentences) - chunk_size + 1, max(1, chunk_size - 1)):
        chunks.append(" ".join(sentences[i : i + chunk_size]))
    return chunks


async def _search_web(query: str) -> List[Dict[str, Any]]:
    """Search the web for matching content.

    In production this would call Google Custom Search, Bing API, etc.
    Returns empty results until a search API key is configured.
    """
    logger.debug("Web search called for: %s", query[:80])
    return []


async def _search_academic(query: str) -> List[Dict[str, Any]]:
    """Search academic databases (Semantic Scholar, CrossRef). Stub."""
    logger.debug("Academic search called for: %s", query[:80])
    return []


async def _search_wikipedia(query: str) -> List[Dict[str, Any]]:
    """Search Wikipedia for matching content. Stub."""
    logger.debug("Wikipedia search called for: %s", query[:80])
    return []


async def _semantic_similarity(text_a: str, text_b: str) -> float:
    """Compute semantic similarity between two texts using sentence embeddings."""
    try:
        from app.ml.models.model_registry import ModelRegistry

        registry = ModelRegistry()
        model = registry.get_sentence_transformer(settings.SENTENCE_MODEL)
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, model.encode, [text_a, text_b])
        import numpy as np

        a, b = embeddings[0], embeddings[1]
        sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))
        return max(0.0, min(1.0, sim))
    except Exception as exc:
        logger.warning("Semantic similarity failed: %s", exc)
        return 0.0


def _exact_match_score(text: str, source_text: str) -> float:
    """Simple exact substring / n-gram overlap ratio."""
    if not source_text:
        return 0.0
    text_lower = text.lower()
    source_lower = source_text.lower()
    # Direct substring check
    if source_lower in text_lower or text_lower in source_lower:
        shorter = min(len(text_lower), len(source_lower))
        longer = max(len(text_lower), len(source_lower))
        return shorter / longer if longer > 0 else 0.0
    # 4-gram word overlap
    n = 4
    text_words = text_lower.split()
    source_words = source_lower.split()
    if len(text_words) < n or len(source_words) < n:
        return 0.0
    text_ngrams = set(tuple(text_words[i : i + n]) for i in range(len(text_words) - n + 1))
    source_ngrams = set(tuple(source_words[i : i + n]) for i in range(len(source_words) - n + 1))
    overlap = len(text_ngrams & source_ngrams)
    total = max(len(text_ngrams), 1)
    return min(1.0, overlap / total)


async def _analyze_paragraph(
    index: int,
    paragraph: str,
    options: PlagiarismOptions,
) -> ParagraphAnalysis:
    """Analyze a single paragraph for plagiarism against multiple sources."""
    sources: List[SourceMatch] = []
    search_tasks: List[Any] = []

    chunks = _chunk_text(paragraph, settings.PLAG_CHUNK_SIZE)

    for chunk in chunks[:5]:  # Limit API calls per paragraph
        if options.search_web:
            search_tasks.append(_search_web(chunk))
        if options.search_academic:
            search_tasks.append(_search_academic(chunk))
        if options.search_wikipedia:
            search_tasks.append(_search_wikipedia(chunk))

    all_results: List[Any] = []
    if search_tasks:
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    for batch in all_results:
        if isinstance(batch, Exception):
            continue
        for hit in batch:
            source_text = hit.get("snippet", hit.get("text", ""))
            url = hit.get("url", "")
            title = hit.get("title", "")

            exact_score = _exact_match_score(paragraph, source_text)
            sem_score = 0.0
            if options.semantic_matching and source_text:
                sem_score = await _semantic_similarity(paragraph, source_text)

            best_score = max(exact_score, sem_score)
            method = "exact" if exact_score >= sem_score else "semantic"

            if best_score >= settings.PLAG_SIMILARITY_THRESHOLD:
                sources.append(
                    SourceMatch(
                        url=url or None,
                        title=title or None,
                        matched_text=source_text[:500],
                        similarity_score=round(best_score, 4),
                        method=method,
                    )
                )

    plag_score = max((s.similarity_score for s in sources), default=0.0)

    return ParagraphAnalysis(
        paragraph_index=index,
        text=paragraph[:1000],
        plagiarism_score=round(plag_score, 4),
        sources=sources,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/plagiarism", response_model=PlagiarismResponse)
async def check_plagiarism(
    request: PlagiarismRequest,
    db: AsyncSession = Depends(get_db),
):
    """Full plagiarism analysis with web, academic, Wikipedia, and semantic checks."""
    start = time.perf_counter()
    word_count = len(request.text.split())

    if word_count < settings.MIN_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Text too short: {word_count} words (minimum {settings.MIN_WORDS})",
        )

    paragraphs = _split_paragraphs(request.text)
    if not paragraphs:
        paragraphs = [request.text]

    # Analyze all paragraphs concurrently
    para_tasks = [_analyze_paragraph(i, p, request.options) for i, p in enumerate(paragraphs)]
    paragraph_results: List[ParagraphAnalysis] = await asyncio.gather(*para_tasks)

    # Deduplicate sources across paragraphs
    seen_keys: set = set()
    all_sources: List[SourceMatch] = []
    for pa in paragraph_results:
        for src in pa.sources:
            key = src.url or hashlib.md5(src.matched_text.encode()).hexdigest()
            if key not in seen_keys:
                seen_keys.add(key)
                all_sources.append(src)

    # Weighted overall score (by paragraph char length)
    total_chars = sum(len(p.text) for p in paragraph_results) or 1
    overall_score = sum(p.plagiarism_score * len(p.text) / total_chars for p in paragraph_results)
    overall_score = round(min(1.0, overall_score), 4)
    originality = round((1.0 - overall_score) * 100, 2)

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # Persist a parent analysis record
    analysis = Analysis(
        id=uuid.uuid4().hex,
        input_text=request.text,
        word_count=word_count,
        overall_ai_score=0.0,
        classification="plagiarism_check",
        confidence=0.0,
        processing_time_ms=elapsed_ms,
        model_version=settings.APP_VERSION,
    )
    db.add(analysis)
    await db.flush()

    # Persist individual plagiarism source matches
    for src in all_sources:
        pr = PlagiarismResult(
            id=uuid.uuid4().hex,
            analysis_id=analysis.id,
            source_url=src.url,
            source_title=src.title,
            matched_text=src.matched_text,
            similarity_score=src.similarity_score,
            method=src.method,
            details_json=json.dumps(
                {
                    "paragraph_count": len(paragraph_results),
                    "overall_plagiarism_score": overall_score,
                }
            ),
        )
        db.add(pr)

    await db.flush()

    return PlagiarismResponse(
        result_id=analysis.id,
        overall_plagiarism_score=overall_score,
        originality_percentage=originality,
        paragraph_analysis=paragraph_results,
        sources_found=all_sources,
        total_sources=len(all_sources),
        word_count=word_count,
        processing_time_ms=elapsed_ms,
    )


@router.get("/plagiarism/{result_id}", response_model=PlagiarismResponse)
async def get_plagiarism_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a previously stored plagiarism result by ID."""
    stmt = select(Analysis).where(Analysis.id == result_id)
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(status_code=404, detail="Plagiarism result not found")

    # Load associated plagiarism match rows
    plag_stmt = select(PlagiarismResult).where(PlagiarismResult.analysis_id == result_id)
    plag_result = await db.execute(plag_stmt)
    plag_rows = plag_result.scalars().all()

    sources = [
        SourceMatch(
            url=pr.source_url,
            title=pr.source_title,
            matched_text=pr.matched_text or "",
            similarity_score=pr.similarity_score,
            method=pr.method,
        )
        for pr in plag_rows
    ]

    # Reconstruct paragraph-level analysis from stored text
    paragraphs = _split_paragraphs(analysis.input_text)
    if not paragraphs:
        paragraphs = [analysis.input_text]

    paragraph_analysis = []
    for i, p in enumerate(paragraphs):
        para_sources = [
            src
            for src in sources
            if src.matched_text
            and (
                src.matched_text[:100].lower() in p.lower()
                or _exact_match_score(p, src.matched_text) > 0.3
            )
        ]
        plag_score = max((s.similarity_score for s in para_sources), default=0.0)
        paragraph_analysis.append(
            ParagraphAnalysis(
                paragraph_index=i,
                text=p[:1000],
                plagiarism_score=round(plag_score, 4),
                sources=para_sources,
            )
        )

    total_chars = sum(len(p.text) for p in paragraph_analysis) or 1
    overall_score = sum(p.plagiarism_score * len(p.text) / total_chars for p in paragraph_analysis)
    overall_score = round(min(1.0, overall_score), 4)

    return PlagiarismResponse(
        result_id=result_id,
        overall_plagiarism_score=overall_score,
        originality_percentage=round((1.0 - overall_score) * 100, 2),
        paragraph_analysis=paragraph_analysis,
        sources_found=sources,
        total_sources=len(sources),
        word_count=analysis.word_count,
        processing_time_ms=analysis.processing_time_ms,
    )
