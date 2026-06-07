"""
Abstract base class for all ClarityAI detectors.
"""

from __future__ import annotations

import math
import logging
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """Base class that all detection signals inherit from."""

    @abstractmethod
    async def analyze(self, text: str) -> dict:
        """
        Analyze text and return a result dictionary.

        Every implementation MUST return at minimum:
            - signal: str           (name of the detector)
            - ai_probability: float (0.0 = human, 1.0 = AI)
            - confidence: str       ("low" | "medium" | "high")
        """
        ...

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Numerically stable sigmoid."""
        if x >= 0:
            z = math.exp(-x)
            return 1.0 / (1.0 + z)
        else:
            z = math.exp(x)
            return z / (1.0 + z)

    @staticmethod
    def _compute_confidence(scores: List[float]) -> str:
        """
        Derive a confidence label from a list of sub-scores (each 0-1).

        Returns 'high', 'medium', or 'low'.
        """
        if not scores:
            return "low"
        avg = sum(scores) / len(scores)
        spread = max(scores) - min(scores) if len(scores) > 1 else 0.0

        if avg > 0.75 and spread < 0.25:
            return "high"
        elif avg > 0.5 and spread < 0.4:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

    def _empty_result(self, signal_name: str, reason: str = "insufficient text") -> dict:
        """Return a safe default result for edge cases."""
        return {
            "signal": signal_name,
            "ai_probability": 0.5,
            "confidence": "low",
            "error": reason,
        }
