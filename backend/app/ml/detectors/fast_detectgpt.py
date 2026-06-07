"""
Detector 2 -- Fast-DetectGPT.

Probability curvature method: compare actual log-probability against
sampled perturbation log-probabilities.  A high normalized discrepancy
indicates machine-generated text.
"""

from __future__ import annotations

import logging
from typing import List

import torch
import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

NUM_SAMPLES = 100
MAX_LENGTH = 512


class FastDetectGPTDetector(BaseDetector):

    @staticmethod
    @torch.no_grad()
    def _log_probability(text: str, model, tokenizer) -> float:
        device = next(model.parameters()).device
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"]
        if input_ids.size(1) < 2:
            return 0.0
        outputs = model(**enc, labels=input_ids)
        return -outputs.loss.item()

    @staticmethod
    @torch.no_grad()
    def _sample_perturbed_logprobs(
        text: str,
        model,
        tokenizer,
        n_samples: int,
    ) -> List[float]:
        device = next(model.parameters()).device
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"]
        seq_len = input_ids.size(1)
        if seq_len < 4:
            return [0.0] * n_samples

        outputs = model(**enc)
        logits = outputs.logits

        log_probs: List[float] = []
        for _ in range(n_samples):
            perturbed = input_ids.clone()
            mask = torch.rand(seq_len, device=device) < 0.15
            mask[0] = False
            if mask.sum() == 0:
                idx = torch.randint(1, seq_len, (1,), device=device)
                mask[idx] = True
            for pos in mask.nonzero(as_tuple=False).squeeze(-1):
                probs = torch.softmax(logits[0, pos], dim=-1)
                sampled = torch.multinomial(probs, 1)
                perturbed[0, pos] = sampled
            perturbed_out = model(perturbed, labels=perturbed)
            log_probs.append(-perturbed_out.loss.item())
        return log_probs

    async def analyze(self, text: str) -> dict:
        signal = "fast_detectgpt"
        if len(text.split()) < 10:
            return self._empty_result(signal, "text too short (< 10 words)")

        tokenizer, model = await ModelRegistry.get_model("gpt2")

        original_lp = self._log_probability(text, model, tokenizer)
        sampled_lps = self._sample_perturbed_logprobs(
            text,
            model,
            tokenizer,
            NUM_SAMPLES,
        )

        mu = float(np.mean(sampled_lps))
        sigma = max(float(np.std(sampled_lps)), 1e-8)

        discrepancy = (original_lp - mu) / sigma
        ai_prob = self._clamp(self._sigmoid(discrepancy * 1.5))

        sample_cv = sigma / (abs(mu) + 1e-8)
        conf_score = self._clamp(1.0 - sample_cv)
        confidence = "high" if conf_score > 0.7 else "medium" if conf_score > 0.4 else "low"

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "original_log_prob": round(original_lp, 4),
                "perturbation_mean_log_prob": round(mu, 4),
                "perturbation_std": round(sigma, 4),
                "normalized_discrepancy": round(discrepancy, 4),
                "num_samples": NUM_SAMPLES,
            },
        }
