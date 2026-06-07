"""
WebSocket endpoint for real-time AI detection.

Streams each signal result as JSON as it completes, providing
progress updates and a final aggregated score.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Signal definitions (names + order)
# ---------------------------------------------------------------------------

SIGNAL_NAMES = [
    "perplexity",
    "zero_shot",
    "gltr",
    "entropy",
    "burstiness",
    "repetition",
    "vocabulary_richness",
    "sentence_length",
    "coherence",
    "punctuation",
    "readability",
    "named_entity",
    "pos_patterns",
    "watermark",
]

TOTAL_SIGNALS = len(SIGNAL_NAMES)


# ---------------------------------------------------------------------------
# Lazy detector loader
# ---------------------------------------------------------------------------

_detectors_cache: Dict[str, Any] = {}


def _get_all_detectors() -> List[Any]:
    """Lazy-load all 14 detectors."""
    if "all" not in _detectors_cache:
        try:
            from app.ml.detectors import (
                PerplexityBurstinessDetector,
                ZeroShotEnsembleDetector,
                GLTRDetector,
                EntropyAnalyzerDetector,
                RepetitionDetector,
                VocabularyRichnessDetector,
                SentenceLevelDetector,
                CoherenceDetector,
                POSPatternsDetector,
                WatermarkDetector,
                StylometricDetector,
                AIFingerprintDetector,
            )

            _detectors_cache["all"] = [
                ("perplexity", PerplexityBurstinessDetector()),
                ("zero_shot", ZeroShotEnsembleDetector()),
                ("gltr", GLTRDetector()),
                ("entropy", EntropyAnalyzerDetector()),
                ("burstiness", PerplexityBurstinessDetector()),
                ("repetition", RepetitionDetector()),
                ("vocabulary_richness", VocabularyRichnessDetector()),
                ("sentence_length", SentenceLevelDetector()),
                ("coherence", CoherenceDetector()),
                ("stylometric", StylometricDetector()),
                ("pos_patterns", POSPatternsDetector()),
                ("ai_fingerprint", AIFingerprintDetector()),
                ("watermark", WatermarkDetector()),
            ]
        except ImportError as e:
            logger.warning("Some ML detectors not available: %s — using stubs", e)
            _detectors_cache["all"] = []
    return _detectors_cache["all"]


async def _run_single_detector(name: str, detector: Any, text: str) -> Dict[str, Any]:
    """Run a single detector, returning its result dict."""
    try:
        result = await detector.analyze(text)
        return {
            "signal": name,
            "status": "completed",
            "result": result,
        }
    except Exception as exc:
        logger.error("Detector %s failed: %s", name, exc)
        return {
            "signal": name,
            "status": "error",
            "result": {
                "signal": name,
                "ai_probability": 0.5,
                "confidence": "low",
                "error": str(exc),
            },
        }


# ---------------------------------------------------------------------------
# WebSocket route
# ---------------------------------------------------------------------------


@router.websocket("/ws/detect")
async def ws_detect(websocket: WebSocket):
    """
    Real-time AI detection over WebSocket.

    Client sends: {"text": "..."}
    Server streams:
      - Progress:  {"progress": N, "total": 14, "current_signal": "..."}
      - Result:    {"signal": "perplexity", "status": "completed", "result": {...}}
      - Final:     {"status": "complete", "overall_score": 0.87, "classification": "...", ...}
    """
    await websocket.accept()

    try:
        while True:
            # Wait for client to send text
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "status": "error",
                        "message": 'Invalid JSON. Send {"text": "..."}',
                    }
                )
                continue

            text = payload.get("text", "").strip()
            if not text:
                await websocket.send_json(
                    {
                        "status": "error",
                        "message": "No text provided.",
                    }
                )
                continue

            word_count = len(text.split())
            if word_count < settings.MIN_WORDS:
                await websocket.send_json(
                    {
                        "status": "error",
                        "message": f"Text too short: {word_count} words (minimum {settings.MIN_WORDS}).",
                    }
                )
                continue

            start_time = time.perf_counter()

            # Send initial acknowledgement
            await websocket.send_json(
                {
                    "status": "started",
                    "total_signals": TOTAL_SIGNALS,
                    "word_count": word_count,
                }
            )

            detectors = _get_all_detectors()
            signal_results: List[Dict] = []
            completed = 0

            if detectors:
                # Run detectors one by one, streaming results
                for name, detector in detectors:
                    # Progress update
                    await websocket.send_json(
                        {
                            "progress": completed,
                            "total": len(detectors),
                            "current_signal": name,
                        }
                    )

                    result_msg = await _run_single_detector(name, detector, text)
                    signal_results.append(result_msg["result"])
                    completed += 1

                    # Send signal result
                    await websocket.send_json(result_msg)
            else:
                # Stub mode: generate fake signal results with slight delays
                for i, sig_name in enumerate(SIGNAL_NAMES):
                    await websocket.send_json(
                        {
                            "progress": i,
                            "total": TOTAL_SIGNALS,
                            "current_signal": sig_name,
                        }
                    )

                    await asyncio.sleep(0.1)  # simulate processing

                    stub_result = {
                        "signal": sig_name,
                        "ai_probability": 0.5,
                        "confidence": "low",
                    }
                    signal_results.append(stub_result)
                    completed += 1

                    await websocket.send_json(
                        {
                            "signal": sig_name,
                            "status": "completed",
                            "result": stub_result,
                        }
                    )

            # Compute overall score
            if signal_results:
                probs = [r.get("ai_probability", 0.5) for r in signal_results]
                # Weighted average (perplexity, zero_shot, gltr get 2x)
                weights = []
                for r in signal_results:
                    name = r.get("signal", "").lower()
                    if name in ("perplexity", "zero_shot", "gltr"):
                        weights.append(2.0)
                    else:
                        weights.append(1.0)
                total_w = sum(weights)
                overall_score = (
                    sum(p * w for p, w in zip(probs, weights)) / total_w if total_w else 0.5
                )
            else:
                overall_score = 0.5

            # Classification
            if overall_score >= settings.AI_THRESHOLD_HIGH:
                classification = "ai_generated"
            elif overall_score >= settings.AI_THRESHOLD_MEDIUM:
                classification = "mixed"
            else:
                classification = "human_written"

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            # Send final message
            await websocket.send_json(
                {
                    "status": "complete",
                    "overall_score": round(overall_score, 4),
                    "classification": classification,
                    "total_signals": completed,
                    "processing_time_ms": elapsed_ms,
                    "word_count": word_count,
                }
            )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        try:
            await websocket.send_json(
                {
                    "status": "error",
                    "message": f"Internal server error: {str(exc)}",
                }
            )
        except Exception:
            pass
