"""
Sentence-Level Detector.

Runs a fast 3-signal pipeline (perplexity + zero_shot + gltr) per sentence.
Returns per-sentence scores, mixed-content detection, and
ai_sentence_percentage.
"""

from __future__ import annotations

import math
import re
import logging
from typing import Dict, List

import torch
import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

MAX_LENGTH = 512
# Thresholds for per-sentence classification
AI_THRESHOLD = 0.65
HUMAN_THRESHOLD = 0.35


class SentenceLevelDetector(BaseDetector):

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    # ── fast signal: perplexity ─────────────────────────────────────────

    @staticmethod
    @torch.no_grad()
    def _sentence_perplexity_score(sentence: str, model, tokenizer) -> float:
        """Return AI probability based on perplexity (lower ppl -> more AI)."""
        device = next(model.parameters()).device
        enc = tokenizer(
            sentence,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"]
        if input_ids.size(1) < 2:
            return 0.5
        outputs = model(**enc, labels=input_ids)
        ppl = math.exp(outputs.loss.item())
        # Sigmoid mapping: lower ppl -> higher AI score
        x = -(ppl - 60) / 30
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        z = math.exp(x)
        return z / (1.0 + z)

    # ── fast signal: gltr top-10 ratio ──────────────────────────────────

    @staticmethod
    @torch.no_grad()
    def _sentence_gltr_score(sentence: str, model, tokenizer) -> float:
        """Return AI probability based on GLTR top-10 ratio."""
        device = next(model.parameters()).device
        enc = tokenizer(
            sentence,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"]
        seq_len = input_ids.size(1)
        if seq_len < 2:
            return 0.5

        logits = model(**enc).logits
        probs = torch.softmax(logits[0, :-1], dim=-1)
        target_ids = input_ids[0, 1:]

        sorted_idx = probs.argsort(dim=-1, descending=True)
        top10_count = 0
        total = len(target_ids)
        for i in range(total):
            rank_t = (sorted_idx[i] == target_ids[i]).nonzero(as_tuple=True)[0]
            rank = rank_t.item() if len(rank_t) > 0 else probs.size(-1)
            if rank < 10:
                top10_count += 1

        ratio = top10_count / max(total, 1)
        x = (ratio - 0.45) / 0.15
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        z = math.exp(x)
        return z / (1.0 + z)

    # ── fast signal: zero-shot classifier ───────────────────────────────

    _AI_LABELS = {"fake", "ai", "ai-generated", "machine", "chatgpt", "generated", "LABEL_0"}

    async def _sentence_zeroshot_score(self, sentence: str) -> float:
        """Return AI probability from roberta-detector-1 pipeline."""
        try:
            pipe = await ModelRegistry.get_model("roberta-detector-1")
            result = pipe(sentence, truncation=True, max_length=MAX_LENGTH)
            if isinstance(result, list):
                result = result[0]
            label = result.get("label", "").lower().strip()
            score = float(result.get("score", 0.5))
            if label in self._AI_LABELS or any(k in label for k in ("ai", "fake", "machine")):
                return score
            return 1.0 - score
        except Exception as exc:
            logger.warning("Zero-shot sentence scoring failed: %s", exc)
            return 0.5

    # ── main ─────────────────────────────────────────────────────────────

    async def analyze(self, text: str) -> dict:
        signal = "sentence_level"
        sentences = self._sentence_split(text)
        if len(sentences) < 2:
            return self._empty_result(signal, "need >= 2 sentences")

        tokenizer, model = await ModelRegistry.get_model("gpt2")

        per_sentence: List[Dict] = []
        ai_count = 0
        human_count = 0

        for idx, sent in enumerate(sentences):
            ppl_score = self._sentence_perplexity_score(sent, model, tokenizer)
            gltr_score = self._sentence_gltr_score(sent, model, tokenizer)
            zs_score = await self._sentence_zeroshot_score(sent)

            combined = 0.35 * ppl_score + 0.35 * gltr_score + 0.30 * zs_score
            combined = max(0.0, min(1.0, combined))

            if combined >= AI_THRESHOLD:
                label = "ai"
                ai_count += 1
            elif combined <= HUMAN_THRESHOLD:
                label = "human"
                human_count += 1
            else:
                label = "uncertain"

            per_sentence.append(
                {
                    "index": idx,
                    "text": sent[:200],  # truncate for response size
                    "ai_probability": round(combined, 4),
                    "label": label,
                    "sub_scores": {
                        "perplexity": round(ppl_score, 4),
                        "gltr": round(gltr_score, 4),
                        "zero_shot": round(zs_score, 4),
                    },
                }
            )

        total = len(sentences)
        ai_pct = ai_count / total
        human_pct = human_count / total
        uncertain_pct = 1.0 - ai_pct - human_pct

        # Mixed content: both AI and human sentences present
        mixed_content = ai_count > 0 and human_count > 0

        overall_ai = float(np.mean([s["ai_probability"] for s in per_sentence]))

        confidence = (
            "high"
            if abs(overall_ai - 0.5) > 0.3
            else "medium" if abs(overall_ai - 0.5) > 0.15 else "low"
        )

        return {
            "signal": signal,
            "ai_probability": round(overall_ai, 4),
            "confidence": confidence,
            "mixed_content_detected": mixed_content,
            "per_sentence": per_sentence,
            "details": {
                "total_sentences": total,
                "ai_sentence_count": ai_count,
                "human_sentence_count": human_count,
                "uncertain_sentence_count": total - ai_count - human_count,
                "ai_sentence_percentage": round(ai_pct * 100, 1),
                "human_sentence_percentage": round(human_pct * 100, 1),
                "uncertain_sentence_percentage": round(uncertain_pct * 100, 1),
                "thresholds": {
                    "ai": AI_THRESHOLD,
                    "human": HUMAN_THRESHOLD,
                },
            },
        }
