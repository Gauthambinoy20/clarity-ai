"""
Detector 14 -- AI Fingerprint / Model Attribution.

Signature buzzwords and phrase patterns for GPT-4, Claude, Gemini, and
Llama.  Scores each model, normalises to probabilities, and returns the
most likely source model.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List


from app.ml.detectors.base import BaseDetector

logger = logging.getLogger(__name__)

# ── per-model signature features ────────────────────────────────────────

MODEL_SIGNATURES: Dict[str, Dict[str, List[str]]] = {
    "gpt4": {
        "buzzwords": [
            "delve",
            "tapestry",
            "multifaceted",
            "nuanced",
            "comprehensive",
            "landscape",
            "paradigm",
            "intricate",
            "pivotal",
            "holistic",
            "robust",
            "streamline",
            "leverage",
            "underscores",
        ],
        "patterns": [
            r"it(?:'s| is) (?:important|worth) (?:to )?not(?:e|ing)",
            r"in today's (?:world|age|era|landscape)",
            r"(?:one|it) cannot (?:be )?overstat(?:ed|e)",
            r"plays a (?:crucial|vital|pivotal) role",
            r"there are (?:several|many|numerous) (?:key )?(?:factors|reasons)",
        ],
    },
    "claude": {
        "buzzwords": [
            "straightforward",
            "certainly",
            "absolutely",
            "happy to help",
            "I'd be glad",
            "great question",
            "fascinating",
            "thoughtful",
            "I appreciate",
            "nuance",
            "context",
            "perspective",
        ],
        "patterns": [
            r"I'd be (?:happy|glad) to (?:help|assist|explain)",
            r"that's (?:a |an )?(?:great|excellent|thoughtful|interesting) question",
            r"let me (?:break|walk) (?:this|that) down",
            r"here's (?:what|how) I (?:think|see|understand)",
            r"I want to (?:be )?(?:upfront|transparent|honest)",
        ],
    },
    "gemini": {
        "buzzwords": [
            "comprehensive",
            "overview",
            "explore",
            "aspects",
            "key takeaways",
            "in-depth",
            "insights",
            "strategies",
            "optimize",
            "enhance",
            "benefits",
            "considerations",
            "implementation",
        ],
        "patterns": [
            r"here (?:is|are) (?:a |an )?(?:comprehensive|in-depth) (?:overview|look|guide)",
            r"key takeaways?:?",
            r"let's (?:explore|dive into|examine)",
            r"(?:here|below) (?:are|is) (?:some|a few) (?:key )?(?:points|considerations)",
            r"(?:in )?(?:summary|conclusion):?\s",
        ],
    },
    "llama": {
        "buzzwords": [
            "I'll",
            "sure thing",
            "let's get started",
            "no problem",
            "gotcha",
            "awesome",
            "cool",
            "stuff",
            "basically",
            "pretty much",
            "kind of",
            "gonna",
        ],
        "patterns": [
            r"(?:sure|no problem|gotcha|awesome)[!,.]?\s",
            r"let's get (?:started|into it|going)",
            r"here(?:'s| is) the (?:deal|thing|scoop)",
            r"(?:basically|pretty much|kind of)\b",
            r"(?:I'll|I'm gonna) (?:break|walk|run) (?:through|down)",
        ],
    },
}


class AIFingerprintDetector(BaseDetector):

    @staticmethod
    def _score_model(text: str, signature: Dict[str, List[str]]) -> float:
        lower = text.lower()
        words = lower.split()
        total = max(len(words), 1)

        bw_hits = sum(lower.count(bw.lower()) for bw in signature["buzzwords"])
        pat_hits = sum(len(re.findall(pat, lower, re.IGNORECASE)) for pat in signature["patterns"])

        return (bw_hits + pat_hits * 2) / total

    async def analyze(self, text: str) -> dict:
        signal = "ai_fingerprint"
        if len(text.split()) < 15:
            return self._empty_result(signal, "text too short (< 15 words)")

        raw_scores: Dict[str, float] = {}
        for model_name, signature in MODEL_SIGNATURES.items():
            raw_scores[model_name] = self._score_model(text, signature)

        total_raw = sum(raw_scores.values())
        if total_raw == 0:
            # No model fingerprints detected at all
            probabilities = {k: 0.25 for k in raw_scores}
            most_likely = "unknown"
            ai_prob = 0.3
        else:
            probabilities = {k: v / total_raw for k, v in raw_scores.items()}
            most_likely = max(probabilities, key=probabilities.get)  # type: ignore[arg-type]
            # Confidence in AI detection scales with total signal strength
            ai_prob = self._clamp(self._sigmoid((total_raw - 0.02) / 0.015))

        max_prob = max(probabilities.values())
        confidence = (
            "high"
            if max_prob > 0.5 and total_raw > 0.04
            else "medium" if max_prob > 0.35 else "low"
        )

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "most_likely_model": most_likely,
            "details": {
                "model_probabilities": {k: round(v, 4) for k, v in probabilities.items()},
                "raw_scores": {k: round(v, 6) for k, v in raw_scores.items()},
                "total_signal_strength": round(total_raw, 6),
            },
        }
