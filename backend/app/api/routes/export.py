"""
ClarityAI export routes — generate downloadable reports.

POST /export/pdf
POST /export/json
POST /export/csv
GET  /export/{analysis_id}/share
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models import AnalyticsResult

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ExportPDFRequest(BaseModel):
    analysis_id: Optional[str] = Field(None, description="ID of the analytics result to export")
    data: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    title: str = Field(default="ClarityAI Analysis Report")


class ExportJSONRequest(BaseModel):
    analysis_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ExportCSVRequest(BaseModel):
    analysis_ids: Optional[List[str]] = Field(None, min_length=1, max_length=100)
    data: Optional[Dict[str, Any]] = None


class ShareDataRequest(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class ShareLinkResponse(BaseModel):
    analysis_id: str
    share_token: str
    share_url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_analytics_result(db: AsyncSession, analysis_id: str) -> AnalyticsResult:
    """Retrieve an AnalyticsResult or raise 404."""
    stmt = select(AnalyticsResult).where(AnalyticsResult.id == analysis_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return record


def _generate_share_token(analysis_id: str) -> str:
    """Create a deterministic but opaque share token."""
    raw = f"{analysis_id}:{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


# ---------------------------------------------------------------------------
# PDF generation (plain-text fallback if reportlab unavailable)
# ---------------------------------------------------------------------------


def _build_pdf_bytes(title: str, data: Dict[str, Any]) -> bytes:
    """Generate a simple PDF report. Falls back to text if reportlab is missing."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter)
        styles = getSampleStyleSheet()
        story: List[Any] = []

        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 0.3 * inch))

        def _render_dict(d: Dict[str, Any], indent: int = 0) -> None:
            prefix = "&nbsp;" * (indent * 4)
            for key, value in d.items():
                if isinstance(value, dict):
                    story.append(Paragraph(f"{prefix}<b>{key}:</b>", styles["Normal"]))
                    _render_dict(value, indent + 1)
                elif isinstance(value, list):
                    story.append(
                        Paragraph(f"{prefix}<b>{key}:</b> [{len(value)} items]", styles["Normal"])
                    )
                    for i, item in enumerate(value[:10]):
                        if isinstance(item, dict):
                            summary = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:4])
                            story.append(
                                Paragraph(f"{prefix}&nbsp;&nbsp;- {summary}", styles["Normal"])
                            )
                        else:
                            story.append(
                                Paragraph(f"{prefix}&nbsp;&nbsp;- {item}", styles["Normal"])
                            )
                    if len(value) > 10:
                        story.append(
                            Paragraph(
                                f"{prefix}&nbsp;&nbsp;... and {len(value) - 10} more",
                                styles["Normal"],
                            )
                        )
                else:
                    story.append(Paragraph(f"{prefix}<b>{key}:</b> {value}", styles["Normal"]))

        _render_dict(data)
        doc.build(story)
        return buf.getvalue()

    except ImportError:
        # Fallback: generate a plain-text "PDF" (actually text content)
        logger.warning("reportlab not installed — generating plain-text report")
        lines = [title, "=" * len(title), ""]

        def _flatten(d: Dict[str, Any], prefix: str = "") -> None:
            for key, value in d.items():
                if isinstance(value, dict):
                    lines.append(f"{prefix}{key}:")
                    _flatten(value, prefix + "  ")
                elif isinstance(value, list):
                    lines.append(f"{prefix}{key}: [{len(value)} items]")
                    for item in value[:10]:
                        lines.append(f"{prefix}  - {item}")
                else:
                    lines.append(f"{prefix}{key}: {value}")

        _flatten(data)
        return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/export/pdf")
async def export_pdf(
    request: ExportPDFRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a PDF report for a given analysis result."""
    analysis_id = request.analysis_id or "ad-hoc"
    if request.data is not None:
        data = {"input_text": request.text, "results": request.data}
    elif request.analysis_id:
        record = await _fetch_analytics_result(db, request.analysis_id)
        data = json.loads(record.results_json) if record.results_json else {}
    else:
        raise HTTPException(status_code=422, detail="Provide either analysis_id or data")

    pdf_bytes = _build_pdf_bytes(request.title, data)

    content_type = "application/pdf"
    try:
        import reportlab  # noqa: F401
    except ImportError:
        content_type = "text/plain"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="clarityai_report_{analysis_id}.pdf"'
        },
    )


@router.post("/export/json")
async def export_json(
    request: ExportJSONRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export full analysis as formatted JSON."""
    analysis_id = request.analysis_id or "ad-hoc"
    if request.data is not None:
        export = {"analysis_id": analysis_id, "results": request.data}
    elif request.analysis_id:
        record = await _fetch_analytics_result(db, request.analysis_id)
        data = json.loads(record.results_json) if record.results_json else {}
        export = {
            "analysis_id": record.id,
            "analysis_type": record.analysis_type,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "processing_time_ms": record.processing_time_ms,
            "results": data,
        }
    else:
        raise HTTPException(status_code=422, detail="Provide either analysis_id or data")

    formatted = json.dumps(export, indent=2, default=str)

    return StreamingResponse(
        io.BytesIO(formatted.encode("utf-8")),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="clarityai_analysis_{analysis_id}.json"'
        },
    )


@router.post("/export/csv")
async def export_csv(
    request: ExportCSVRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export batch of analysis results as CSV."""
    rows: List[Dict[str, Any]] = []

    if request.data is not None:
        rows.append(
            {
                key: json.dumps(value) if isinstance(value, (dict, list)) else value
                for key, value in request.data.items()
            }
        )

    for aid in request.analysis_ids or []:
        stmt = select(AnalyticsResult).where(AnalyticsResult.id == aid)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            continue

        data = json.loads(record.results_json) if record.results_json else {}

        row: Dict[str, Any] = {
            "analysis_id": record.id,
            "analysis_type": record.analysis_type,
            "processing_time_ms": record.processing_time_ms,
            "created_at": record.created_at.isoformat() if record.created_at else "",
        }

        # Flatten top-level results into columns
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                row[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    if isinstance(sub_val, (str, int, float, bool)):
                        row[f"{key}_{sub_key}"] = sub_val
            # Skip lists/complex for CSV

        rows.append(row)

    if not rows:
        raise HTTPException(status_code=404, detail="No analysis results found for the given IDs")

    # Build CSV
    all_fields = list(dict.fromkeys(k for row in rows for k in row.keys()))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8")

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clarityai_batch_export.csv"'},
    )


@router.post("/export/share")
async def generate_ad_hoc_share_link(request: ShareDataRequest):
    """Generate a lightweight share URL for frontend ad-hoc analysis data."""
    payload = json.dumps(request.data, sort_keys=True, default=str)
    token = _generate_share_token(payload)
    return {"url": f"/api/v1/export/shared/{token}", "share_token": token}


@router.get("/export/{analysis_id}/share", response_model=ShareLinkResponse)
async def generate_share_link(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate a shareable link token for an analysis result."""
    # Verify the analysis exists
    await _fetch_analytics_result(db, analysis_id)

    token = _generate_share_token(analysis_id)
    share_url = f"/api/v1/export/shared/{token}"

    return ShareLinkResponse(
        analysis_id=analysis_id,
        share_token=token,
        share_url=share_url,
    )
