"""
ClarityAI humanization routes — rewrite AI-generated text to sound more human.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Analysis, HumanizationResult

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    style: str = Field(
        default="natural",
        description="Rewriting style: natural, academic, casual, professional",
    )
    target_ai_score: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Target AI-detection score to reach (lower = more human)",
    )
    target_plagiarism_score: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Target plagiarism score to stay below",
    )
    max_iterations: int = Field(default=5, ge=1, le=20)
    model: Optional[str] = Field(
        default=None,
        description="Ollama model to use (defaults to server config)",
    )
    preserve_citations: bool = Field(
        default=True,
        description="Keep inline citations and references intact",
    )
    minimal_changes: bool = Field(
        default=False,
        description="Make the fewest changes needed to pass detection",
    )


class IterationSnapshot(BaseModel):
    iteration: int
    ai_score: float
    plagiarism_score: float
    text_preview: str


class QualityMetrics(BaseModel):
    readability_score: float
    vocabulary_diversity: float
    sentence_variety: float
    meaning_preservation: float


class HumanizeResponse(BaseModel):
    result_id: str
    original_text: str
    humanized_text: str
    original_ai_score: float
    final_ai_score: float
    original_plagiarism_score: float
    final_plagiarism_score: float
    iterations_used: int
    timeline: List[IterationSnapshot]
    quality: QualityMetrics
    model_used: str
    processing_time_ms: int


class OllamaModel(BaseModel):
    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None
    digest: Optional[str] = None


class ModelsResponse(BaseModel):
    models: List[OllamaModel]
    ollama_available: bool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _ollama_available() -> bool:
    """Check if the local Ollama server is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def _ollama_generate(prompt: str, model: str) -> str:
    """Call Ollama /api/generate and return the full response text."""
    async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": settings.HUMANIZE_TEMPERATURE,
                    "num_predict": 4096,
                },
            },
            timeout=settings.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()


def _build_humanize_prompt(
    text: str,
    style: str,
    preserve_citations: bool,
    minimal_changes: bool,
    iteration: int,
) -> str:
    """Build the LLM prompt for humanization rewriting."""
    style_instructions = {
        "natural": "Use a natural, conversational human writing style with varied sentence structures.",
        "academic": "Maintain an academic tone while making the writing feel authentically human-authored.",
        "casual": "Rewrite in a casual, informal tone as if written by a real person in everyday language.",
        "professional": "Keep a professional tone but add the subtle imperfections typical of human writing.",
    }
    style_note = style_instructions.get(style, style_instructions["natural"])

    citation_note = ""
    if preserve_citations:
        citation_note = (
            "\n- Preserve all inline citations, references, and quotations exactly as they appear."
        )

    change_note = ""
    if minimal_changes:
        change_note = (
            "\n- Make the MINIMUM changes necessary. Keep as much original phrasing as possible."
        )

    return f"""Rewrite the following text so it reads as authentically human-written.

Rules:
- {style_note}
- Vary sentence lengths and structures naturally.
- Introduce minor stylistic imperfections humans naturally make.
- Preserve the original meaning, facts, and key terminology.
- Do NOT add disclaimers, meta-commentary, or notes about the rewriting.{citation_note}{change_note}
- Return ONLY the rewritten text with no preamble.

{"This is iteration " + str(iteration) + ". Make additional variations from the previous attempt." if iteration > 1 else ""}

Text to rewrite:
{text}"""


async def _quick_ai_score(text: str) -> float:
    """Run a fast AI-detection score for iteration feedback.

    Tries to use the fast detection pipeline; falls back to a heuristic.
    """
    try:
        from app.api.routes.detection import _run_full_detection, DetectionOptions

        options = DetectionOptions(
            include_sentence_scores=False,
            include_gltr_data=False,
            include_watermark_check=False,
            include_attribution=False,
        )
        result = await _run_full_detection(text, "fast", options)
        return result["overall_score"]
    except Exception as exc:
        logger.warning("Quick AI score failed, using heuristic: %s", exc)
        # Simple heuristic fallback
        words = text.split()
        if not words:
            return 0.5
        avg_word_len = sum(len(w) for w in words) / len(words)
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        score = 0.5
        if avg_word_len > 5.5:
            score += 0.1
        if unique_ratio < 0.5:
            score += 0.1
        return min(1.0, max(0.0, score))


async def _quick_plagiarism_score(original: str, rewritten: str) -> float:
    """Estimate plagiarism risk by comparing rewrite to original via n-gram overlap."""
    orig_words = original.lower().split()
    new_words = rewritten.lower().split()
    if len(orig_words) < 4 or len(new_words) < 4:
        return 0.0

    n = 4
    orig_ngrams = set(tuple(orig_words[i : i + n]) for i in range(len(orig_words) - n + 1))
    new_ngrams = set(tuple(new_words[i : i + n]) for i in range(len(new_words) - n + 1))
    if not new_ngrams:
        return 0.0
    overlap = len(orig_ngrams & new_ngrams)
    return overlap / len(new_ngrams)


def _compute_quality_metrics(original: str, rewritten: str) -> QualityMetrics:
    """Compute quality metrics comparing original to rewritten text."""
    import re

    # Readability (Flesch-like approximation)
    sentences = re.split(r"[.!?]+", rewritten)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = rewritten.split()
    syllable_count = (
        sum(max(1, len(re.findall(r"[aeiouy]+", w.lower()))) for w in words) if words else 1
    )

    num_sentences = max(len(sentences), 1)
    num_words = max(len(words), 1)
    avg_sentence_len = num_words / num_sentences
    avg_syllables = syllable_count / num_words
    readability = max(
        0.0, min(1.0, (206.835 - 1.015 * avg_sentence_len - 84.6 * avg_syllables) / 100)
    )

    # Vocabulary diversity
    unique_words = set(w.lower() for w in words)
    vocab_diversity = len(unique_words) / num_words if num_words > 0 else 0.0

    # Sentence variety (std dev of sentence lengths / mean)
    sent_lengths = [len(s.split()) for s in sentences]
    if len(sent_lengths) > 1:
        mean_len = sum(sent_lengths) / len(sent_lengths)
        variance = sum((x - mean_len) ** 2 for x in sent_lengths) / len(sent_lengths)
        std_dev = variance**0.5
        sentence_variety = min(1.0, std_dev / max(mean_len, 1))
    else:
        sentence_variety = 0.0

    # Meaning preservation (word overlap between original and rewrite)
    orig_words_set = set(original.lower().split())
    new_words_set = set(w.lower() for w in words)
    if orig_words_set:
        meaning_preservation = len(orig_words_set & new_words_set) / len(orig_words_set)
    else:
        meaning_preservation = 1.0

    return QualityMetrics(
        readability_score=round(readability, 4),
        vocabulary_diversity=round(vocab_diversity, 4),
        sentence_variety=round(sentence_variety, 4),
        meaning_preservation=round(meaning_preservation, 4),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/humanize", response_model=HumanizeResponse)
async def humanize_text(
    request: HumanizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Iteratively rewrite text using a local Ollama model until it passes AI detection."""
    start = time.perf_counter()
    word_count = len(request.text.split())

    if word_count < settings.MIN_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Text too short: {word_count} words (minimum {settings.MIN_WORDS})",
        )

    model = request.model or settings.OLLAMA_MODEL

    # Verify Ollama is available
    if not await _ollama_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama server is not available. Please ensure it is running at "
            f"{settings.OLLAMA_BASE_URL}",
        )

    # Get initial AI score
    original_ai_score = await _quick_ai_score(request.text)
    original_plag_score = 0.0  # Original text is the baseline

    timeline: List[IterationSnapshot] = []
    current_text = request.text
    current_ai_score = original_ai_score
    current_plag_score = 0.0
    iterations_used = 0

    for iteration in range(1, request.max_iterations + 1):
        iterations_used = iteration

        # Check if we already meet targets
        if (
            current_ai_score <= request.target_ai_score
            and current_plag_score <= request.target_plagiarism_score
        ):
            if iteration > 1:  # Don't skip on first iteration
                break

        prompt = _build_humanize_prompt(
            text=current_text,
            style=request.style,
            preserve_citations=request.preserve_citations,
            minimal_changes=request.minimal_changes,
            iteration=iteration,
        )

        try:
            rewritten = await _ollama_generate(prompt, model)
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama returned error: {exc.response.status_code}",
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Ollama request timed out",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama generation failed: {exc}",
            )

        if not rewritten or len(rewritten.split()) < 10:
            logger.warning("Ollama returned empty/short response on iteration %d", iteration)
            continue

        current_text = rewritten
        current_ai_score = await _quick_ai_score(current_text)
        current_plag_score = await _quick_plagiarism_score(request.text, current_text)

        timeline.append(
            IterationSnapshot(
                iteration=iteration,
                ai_score=round(current_ai_score, 4),
                plagiarism_score=round(current_plag_score, 4),
                text_preview=current_text[:200],
            )
        )

        # Stop early if targets met
        if (
            current_ai_score <= request.target_ai_score
            and current_plag_score <= request.target_plagiarism_score
        ):
            break

    quality = _compute_quality_metrics(request.text, current_text)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # Persist parent analysis record
    analysis = Analysis(
        id=uuid.uuid4().hex,
        input_text=request.text,
        word_count=word_count,
        overall_ai_score=original_ai_score,
        classification="humanization",
        confidence=0.0,
        processing_time_ms=elapsed_ms,
        model_version=settings.APP_VERSION,
    )
    db.add(analysis)
    await db.flush()

    # Persist humanization result
    hresult = HumanizationResult(
        id=uuid.uuid4().hex,
        analysis_id=analysis.id,
        original_text=request.text,
        humanized_text=current_text,
        original_ai_score=original_ai_score,
        humanized_ai_score=current_ai_score,
        iterations_used=iterations_used,
        strategy="ollama",
        processing_time_ms=elapsed_ms,
    )
    db.add(hresult)
    await db.flush()

    return HumanizeResponse(
        result_id=hresult.id,
        original_text=request.text,
        humanized_text=current_text,
        original_ai_score=round(original_ai_score, 4),
        final_ai_score=round(current_ai_score, 4),
        original_plagiarism_score=round(original_plag_score, 4),
        final_plagiarism_score=round(current_plag_score, 4),
        iterations_used=iterations_used,
        timeline=timeline,
        quality=quality,
        model_used=model,
        processing_time_ms=elapsed_ms,
    )


@router.get("/humanize/{result_id}", response_model=HumanizeResponse)
async def get_humanization_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a previously stored humanization result by ID."""
    stmt = select(HumanizationResult).where(HumanizationResult.id == result_id)
    result = await db.execute(stmt)
    hresult = result.scalar_one_or_none()

    if hresult is None:
        raise HTTPException(status_code=404, detail="Humanization result not found")

    # Reconstruct quality metrics from stored texts
    quality = _compute_quality_metrics(hresult.original_text, hresult.humanized_text)

    # Estimate plagiarism score from stored texts
    plag_score = await _quick_plagiarism_score(hresult.original_text, hresult.humanized_text)

    return HumanizeResponse(
        result_id=hresult.id,
        original_text=hresult.original_text,
        humanized_text=hresult.humanized_text,
        original_ai_score=round(hresult.original_ai_score, 4),
        final_ai_score=round(hresult.humanized_ai_score, 4),
        original_plagiarism_score=0.0,
        final_plagiarism_score=round(plag_score, 4),
        iterations_used=hresult.iterations_used,
        timeline=[],  # Timeline is not persisted; empty on retrieval
        quality=quality,
        model_used=hresult.strategy,
        processing_time_ms=hresult.processing_time_ms,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_ollama_models():
    """List available models from the local Ollama server."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("models", []):
            models.append(
                OllamaModel(
                    name=m.get("name", "unknown"),
                    size=m.get("size"),
                    modified_at=m.get("modified_at"),
                    digest=m.get("digest"),
                )
            )

        return ModelsResponse(models=models, ollama_available=True)

    except Exception as exc:
        logger.warning("Failed to fetch Ollama models: %s", exc)
        return ModelsResponse(models=[], ollama_available=False)
