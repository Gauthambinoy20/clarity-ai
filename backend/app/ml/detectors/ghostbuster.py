"""
Detector 4 -- Ghostbuster.

Extracts 22 cross-model features from distilgpt2, gpt2, and gpt2-medium,
then classifies with a GradientBoostingClassifier (fallback weighted-score
when no trained model is available).
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Dict, List

import torch
import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

_MODELS = ("distilgpt2", "gpt2", "gpt2-medium")
MAX_LENGTH = 512
_CLF_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "weights",
    "ghostbuster_clf.pkl",
)


class GhostbusterDetector(BaseDetector):

    def __init__(self) -> None:
        self._classifier = self._load_classifier()

    @staticmethod
    def _load_classifier():
        if os.path.exists(_CLF_PATH):
            try:
                with open(_CLF_PATH, "rb") as f:
                    return pickle.load(f)
            except Exception as exc:
                logger.warning("Could not load Ghostbuster classifier: %s", exc)
        return None

    @staticmethod
    @torch.no_grad()
    def _token_features(text: str, model, tokenizer) -> Dict[str, float]:
        device = next(model.parameters()).device
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(device)
        input_ids = enc["input_ids"]
        seq_len = input_ids.size(1)

        if seq_len < 2:
            return {
                k: 0.0
                for k in (
                    "mean_token_prob",
                    "std_token_prob",
                    "mean_rank",
                    "std_rank",
                    "top10_ratio",
                    "top100_ratio",
                    "top1000_ratio",
                    "mean_entropy",
                    "std_entropy",
                )
            }

        logits = model(**enc).logits
        probs = torch.softmax(logits[0, :-1], dim=-1)
        target_ids = input_ids[0, 1:]

        token_probs = probs[torch.arange(len(target_ids)), target_ids].cpu().numpy()

        sorted_idx = probs.argsort(dim=-1, descending=True)
        ranks = np.array(
            [
                (
                    int((sorted_idx[i] == target_ids[i]).nonzero(as_tuple=True)[0].item())
                    if len((sorted_idx[i] == target_ids[i]).nonzero(as_tuple=True)[0]) > 0
                    else probs.size(-1)
                )
                for i in range(len(target_ids))
            ],
            dtype=float,
        )

        log_p = torch.log(probs + 1e-10)
        entropy = -(probs * log_p).sum(dim=-1).cpu().numpy()

        return {
            "mean_token_prob": float(np.mean(token_probs)),
            "std_token_prob": float(np.std(token_probs)),
            "mean_rank": float(np.mean(ranks)),
            "std_rank": float(np.std(ranks)),
            "top10_ratio": float(np.mean(ranks < 10)),
            "top100_ratio": float(np.mean(ranks < 100)),
            "top1000_ratio": float(np.mean(ranks < 1000)),
            "mean_entropy": float(np.mean(entropy)),
            "std_entropy": float(np.std(entropy)),
        }

    async def _extract_features(self, text: str) -> np.ndarray:
        all_feats: List[float] = []
        model_feats_list: List[Dict[str, float]] = []

        for mname in _MODELS:
            tokenizer, model = await ModelRegistry.get_model(mname)
            feats = self._token_features(text, model, tokenizer)
            model_feats_list.append(feats)
            for key in (
                "mean_token_prob",
                "std_token_prob",
                "mean_rank",
                "top10_ratio",
                "top100_ratio",
                "mean_entropy",
            ):
                all_feats.append(feats[key])

        # 3 cross-model prob differences
        for i in range(len(_MODELS)):
            for j in range(i + 1, len(_MODELS)):
                all_feats.append(
                    model_feats_list[i]["mean_token_prob"] - model_feats_list[j]["mean_token_prob"]
                )

        # cross-model entropy ratio
        entropies = [mf["mean_entropy"] for mf in model_feats_list]
        all_feats.append(max(entropies) / (min(entropies) + 1e-8))

        return np.array(all_feats, dtype=np.float64)  # length 22

    @staticmethod
    def _fallback_score(features: np.ndarray) -> float:
        top10_avg = float(np.mean([features[3], features[9], features[15]]))
        prob_avg = float(np.mean([features[0], features[6], features[12]]))
        score = (
            0.5 * top10_avg
            + 0.3 * min(prob_avg * 5, 1.0)
            + 0.2 * (1.0 - min(float(features[21]), 3.0) / 3.0)
        )
        return max(0.0, min(1.0, score))

    async def analyze(self, text: str) -> dict:
        signal = "ghostbuster"
        if len(text.split()) < 10:
            return self._empty_result(signal, "text too short (< 10 words)")

        features = await self._extract_features(text)

        if self._classifier is not None:
            try:
                prob = self._classifier.predict_proba(features.reshape(1, -1))[0][1]
                ai_prob = float(prob)
                method = "gradient_boosting"
            except Exception as exc:
                logger.warning("Ghostbuster classifier failed: %s", exc)
                ai_prob = self._fallback_score(features)
                method = "fallback_heuristic"
        else:
            ai_prob = self._fallback_score(features)
            method = "fallback_heuristic"

        ai_prob = self._clamp(ai_prob)
        confidence = (
            "high" if abs(ai_prob - 0.5) > 0.3 else "medium" if abs(ai_prob - 0.5) > 0.15 else "low"
        )

        return {
            "signal": signal,
            "ai_probability": round(ai_prob, 4),
            "confidence": confidence,
            "details": {
                "method": method,
                "num_features": len(features),
                "feature_vector": [round(float(f), 4) for f in features],
            },
        }
