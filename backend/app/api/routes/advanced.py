"""
ClarityAI Advanced Routes -- Rewrite detection, document fingerprinting,
version tracking, writing coach, batch processing, and shareable links.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/advanced")


# ── In-memory stores (persist for process lifetime) ─────────────────────

_fingerprint_store: Dict[str, Dict[str, Any]] = {}
_batch_store: Dict[str, Dict[str, Any]] = {}
_share_store: Dict[str, Dict[str, Any]] = {}


# ── Pydantic schemas ────────────────────────────────────────────────────


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)


class FingerprintVerifyRequest(BaseModel):
    fingerprint_id_1: str
    fingerprint_id_2: str


class VersionRequest(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=128)
    text: str = Field(..., min_length=1, max_length=100_000)


class BatchRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=100)
    filenames: Optional[List[str]] = None


class ShareRequest(BaseModel):
    analysis_data: Dict[str, Any] = Field(...)
    title: Optional[str] = None


# ── Response schemas ─────────────────────────────────────────────────────


class RewriteDetectionResponse(BaseModel):
    signal: str
    ai_probability: float
    confidence: str
    rewrite_detected: bool
    rewrite_confidence: float
    residual_ai_patterns: List[str]
    naturalness_score: float
    details: Dict[str, Any]


class FingerprintResponse(BaseModel):
    fingerprint_id: str
    text_hash: str
    content_hash: str
    structure_hash: str
    created_at: str
    word_count: int


class FingerprintVerifyResponse(BaseModel):
    exact_match: bool
    content_match: bool
    structure_match: bool
    content_similarity: float
    fp1_id: Optional[str] = None
    fp2_id: Optional[str] = None


class VersionResponse(BaseModel):
    document_id: str
    version_number: int
    previous_score: Optional[float] = None
    current_score: float
    score_change: float
    diff_summary: Dict[str, int]
    score_trajectory: List[Dict[str, Any]]
    total_versions: int


class VersionHistoryResponse(BaseModel):
    document_id: str
    total_versions: int
    latest_version: int
    latest_score: Optional[float] = None
    score_trajectory: List[Dict[str, Any]]
    versions: List[Dict[str, Any]]


class CoachSuggestion(BaseModel):
    category: str
    message: str
    original: Optional[str] = None
    fix: Optional[str] = None
    impact: str
    position: Optional[int] = None


class CoachResponse(BaseModel):
    human_score: int
    suggestions: List[CoachSuggestion]
    quick_fixes: List[Dict[str, Any]]
    total_suggestions: int
    high_impact_count: int
    medium_impact_count: int
    low_impact_count: int


class BatchResultItem(BaseModel):
    index: int
    filename: str
    word_count: int
    ai_score: float
    classification: str
    top_signal: str


class BatchResponse(BaseModel):
    batch_id: str
    total_files: int
    avg_score: float
    score_distribution: List[Dict[str, Any]]
    flagged_count: int
    results: List[BatchResultItem]
    processing_time_ms: int


class ShareResponse(BaseModel):
    share_url: str
    share_token: str
    qr_code_data: str


# ── Helper: lazy loaders ────────────────────────────────────────────────


def _get_rewrite_detector():
    from app.ml.detectors.rewrite_detector import RewriteDetector

    return RewriteDetector()


def _get_fingerprinter():
    from app.ml.analyzers.document_fingerprint import DocumentFingerprinter

    return DocumentFingerprinter()


def _get_version_tracker():
    from app.ml.analyzers.version_tracker import VersionTracker

    return VersionTracker()


def _get_writing_coach():
    from app.ml.analyzers.writing_coach import WritingCoach

    return WritingCoach()


def _get_batch_processor():
    from app.ml.analyzers.batch_processor import BatchProcessor

    return BatchProcessor()


# ── SVG QR code generator (no external dependency) ──────────────────────


def _generate_qr_svg_base64(data: str) -> str:
    """
    Generate a simple QR-code-like SVG as base64.

    This creates a deterministic grid pattern derived from the data hash.
    For production use, replace with a proper QR library (qrcode).
    """
    h = hashlib.sha256(data.encode()).hexdigest()
    size = 21  # QR version 1 is 21x21
    cell = 10
    total = size * cell

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{total}" viewBox="0 0 {total} {total}">',
        f'<rect width="{total}" height="{total}" fill="white"/>',
    ]

    # Generate a deterministic pattern from the hash
    bits = bin(int(h, 16))[2:].zfill(256)
    bit_idx = 0

    # Fixed finder patterns (top-left, top-right, bottom-left)
    finder_positions = [(0, 0), (size - 7, 0), (0, size - 7)]
    finder_cells = set()
    for fx, fy in finder_positions:
        for dx in range(7):
            for dy in range(7):
                # Outer border, inner border, center
                is_border = dx == 0 or dx == 6 or dy == 0 or dy == 6
                is_inner = 2 <= dx <= 4 and 2 <= dy <= 4
                if is_border or is_inner:
                    x = (fx + dx) * cell
                    y = (fy + dy) * cell
                    svg_parts.append(
                        f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="black"/>'
                    )
                    finder_cells.add((fx + dx, fy + dy))

    # Fill remaining cells with data-derived pattern
    for row in range(size):
        for col in range(size):
            if (col, row) in finder_cells:
                continue
            if bit_idx < len(bits) and bits[bit_idx] == "1":
                x = col * cell
                y = row * cell
                svg_parts.append(
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="black"/>'
                )
            bit_idx = (bit_idx + 1) % len(bits)

    svg_parts.append("</svg>")
    svg_str = "\n".join(svg_parts)
    return base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")


# ── Routes ───────────────────────────────────────────────────────────────


# 1. Rewrite Detection
@router.post("/rewrite-detect", response_model=RewriteDetectionResponse)
async def rewrite_detect(request: TextRequest):
    """Run rewrite/paraphrase detection on text to find humanized AI content."""
    detector = _get_rewrite_detector()
    result = await detector.analyze(request.text)
    return RewriteDetectionResponse(**result)


# 2. Document Fingerprint
@router.post("/fingerprint", response_model=FingerprintResponse)
async def generate_fingerprint(request: TextRequest):
    """Generate a tamper-proof document fingerprint."""
    fp = _get_fingerprinter()
    result = fp.generate_fingerprint(request.text)

    # Store fingerprint (including internal ngrams for later verification)
    _fingerprint_store[result["fingerprint_id"]] = result

    # Return public fields only
    return FingerprintResponse(
        fingerprint_id=result["fingerprint_id"],
        text_hash=result["text_hash"],
        content_hash=result["content_hash"],
        structure_hash=result["structure_hash"],
        created_at=result["created_at"],
        word_count=result["word_count"],
    )


# 3. Verify Fingerprints
@router.post("/fingerprint/verify", response_model=FingerprintVerifyResponse)
async def verify_fingerprints(request: FingerprintVerifyRequest):
    """Verify whether two document fingerprints match."""
    fp1 = _fingerprint_store.get(request.fingerprint_id_1)
    fp2 = _fingerprint_store.get(request.fingerprint_id_2)

    if fp1 is None:
        raise HTTPException(
            status_code=404, detail=f"Fingerprint {request.fingerprint_id_1} not found"
        )
    if fp2 is None:
        raise HTTPException(
            status_code=404, detail=f"Fingerprint {request.fingerprint_id_2} not found"
        )

    fingerprinter = _get_fingerprinter()
    result = fingerprinter.verify_fingerprints(fp1, fp2)
    return FingerprintVerifyResponse(**result)


# 4. Submit new version
@router.post("/version", response_model=VersionResponse)
async def submit_version(request: VersionRequest):
    """Submit a new version of a document and track score changes."""
    tracker = _get_version_tracker()
    result = tracker.add_version(request.document_id, request.text)
    return VersionResponse(**result)


# 5. Get version history
@router.get("/version/{document_id}", response_model=VersionHistoryResponse)
async def get_version_history(document_id: str):
    """Get the full version history for a document."""
    tracker = _get_version_tracker()
    result = tracker.get_history(document_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    return VersionHistoryResponse(**result)


# 6. Writing Coach
@router.post("/coach", response_model=CoachResponse)
async def writing_coach(request: TextRequest):
    """Get AI writing coach suggestions to make text sound more human."""
    coach = _get_writing_coach()
    result = coach.analyze(request.text)

    return CoachResponse(
        human_score=result["human_score"],
        suggestions=[
            CoachSuggestion(
                category=s.get("category", "general"),
                message=s.get("message", ""),
                original=s.get("original"),
                fix=s.get("fix"),
                impact=s.get("impact", "low"),
                position=s.get("position"),
            )
            for s in result["suggestions"]
        ],
        quick_fixes=result["quick_fixes"],
        total_suggestions=result["total_suggestions"],
        high_impact_count=result["high_impact_count"],
        medium_impact_count=result["medium_impact_count"],
        low_impact_count=result["low_impact_count"],
    )


# 7. Batch processing
@router.post("/batch", response_model=BatchResponse)
async def batch_process(request: BatchRequest):
    """Batch process multiple texts through fast detection."""
    processor = _get_batch_processor()
    result = processor.process_batch(request.texts, request.filenames)

    # Store batch results for later retrieval
    _batch_store[result["batch_id"]] = result

    return BatchResponse(
        batch_id=result["batch_id"],
        total_files=result["total_files"],
        avg_score=result["avg_score"],
        score_distribution=result["score_distribution"],
        flagged_count=result["flagged_count"],
        results=[BatchResultItem(**r) for r in result["results"]],
        processing_time_ms=result["processing_time_ms"],
    )


# 8. Get batch results
@router.get("/batch/{batch_id}", response_model=BatchResponse)
async def get_batch_results(batch_id: str):
    """Retrieve results of a previously submitted batch job."""
    result = _batch_store.get(batch_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    return BatchResponse(
        batch_id=result["batch_id"],
        total_files=result["total_files"],
        avg_score=result["avg_score"],
        score_distribution=result["score_distribution"],
        flagged_count=result["flagged_count"],
        results=[BatchResultItem(**r) for r in result["results"]],
        processing_time_ms=result["processing_time_ms"],
    )


# 9. Shareable analysis link
@router.post("/share", response_model=ShareResponse)
async def create_share_link(request: ShareRequest):
    """Generate a shareable analysis link with QR code."""
    share_token = secrets.token_urlsafe(32)
    share_id = uuid.uuid4().hex

    # Store the analysis data
    _share_store[share_token] = {
        "id": share_id,
        "title": request.title or "ClarityAI Analysis",
        "analysis_data": request.analysis_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    share_url = f"/shared/{share_token}"
    qr_code_data = _generate_qr_svg_base64(share_url)

    return ShareResponse(
        share_url=share_url,
        share_token=share_token,
        qr_code_data=qr_code_data,
    )


@router.get("/share/{share_token}")
async def get_shared_analysis(share_token: str):
    """Retrieve a shared analysis by token."""
    data = _share_store.get(share_token)
    if data is None:
        raise HTTPException(status_code=404, detail="Shared analysis not found or expired")
    return data
