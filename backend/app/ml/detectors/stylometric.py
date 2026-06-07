"""
Detector 7 -- Stylometric Analysis.

27 features across 6 categories using spaCy:
  lexical richness, sentence structure, syntactic complexity,
  punctuation patterns, discourse markers, functional patterns.
Uses sklearn GradientBoostingClassifier with fallback heuristic.
"""

from __future__ import annotations

import logging
import math
import os
import pickle
import re
from collections import Counter
from typing import Dict, List

import numpy as np

from app.ml.detectors.base import BaseDetector
from app.ml.models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

_CLF_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "weights",
    "stylometric_clf.pkl",
)

AI_DISCOURSE_MARKERS = [
    "furthermore",
    "moreover",
    "additionally",
    "consequently",
    "nevertheless",
    "in conclusion",
    "it is important to note",
    "it is worth noting",
    "in summary",
    "overall",
    "specifically",
    "notably",
    "significantly",
    "essentially",
]

HUMAN_DISCOURSE_MARKERS = [
    "honestly",
    "actually",
    "basically",
    "like",
    "you know",
    "i mean",
    "well",
    "anyway",
    "so yeah",
    "kind of",
    "sort of",
    "i think",
    "i guess",
    "pretty much",
]


class StylometricDetector(BaseDetector):

    def __init__(self) -> None:
        self._classifier = self._load_classifier()

    @staticmethod
    def _load_classifier():
        if os.path.exists(_CLF_PATH):
            try:
                with open(_CLF_PATH, "rb") as f:
                    return pickle.load(f)
            except Exception as exc:
                logger.warning("Could not load stylometric classifier: %s", exc)
        return None

    # ── lexical richness ────────────────────────────────────────────────

    @staticmethod
    def _ttr(tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        return len(set(tokens)) / len(tokens)

    @staticmethod
    def _mattr(tokens: List[str], window: int = 50) -> float:
        if len(tokens) < window:
            return StylometricDetector._ttr(tokens)
        ttrs = []
        for i in range(len(tokens) - window + 1):
            w = tokens[i : i + window]
            ttrs.append(len(set(w)) / window)
        return float(np.mean(ttrs))

    @staticmethod
    def _hapax_ratio(tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        freq = Counter(tokens)
        hapax = sum(1 for v in freq.values() if v == 1)
        return hapax / len(tokens)

    @staticmethod
    def _yules_k(tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        freq = Counter(tokens)
        n = len(tokens)
        freq_of_freq = Counter(freq.values())
        m2 = sum(i * i * v for i, v in freq_of_freq.items())
        if n <= 1:
            return 0.0
        return 10000.0 * (m2 - n) / (n * n)

    @staticmethod
    def _simpsons_d(tokens: List[str]) -> float:
        if len(tokens) < 2:
            return 0.0
        freq = Counter(tokens)
        n = len(tokens)
        return 1.0 - sum(f * (f - 1) for f in freq.values()) / (n * (n - 1))

    # ── sentence structure ──────────────────────────────────────────────

    @staticmethod
    def _sentence_features(sent_lengths: List[int]) -> Dict[str, float]:
        if not sent_lengths:
            return {
                "sent_mean": 0.0,
                "sent_std": 0.0,
                "sent_bimodality": 0.0,
                "sent_range": 0.0,
            }
        arr = np.array(sent_lengths, dtype=float)
        from scipy import stats as sp_stats

        skew = float(sp_stats.skew(arr)) if len(arr) >= 3 else 0.0
        kurt = float(sp_stats.kurtosis(arr, fisher=False)) if len(arr) >= 4 else 3.0
        bimod = (skew**2 + 1) / kurt if kurt != 0 else 0.0
        return {
            "sent_mean": float(arr.mean()),
            "sent_std": float(arr.std()),
            "sent_bimodality": bimod,
            "sent_range": float(arr.max() - arr.min()),
        }

    # ── syntactic complexity ────────────────────────────────────────────

    @staticmethod
    def _dep_depth(doc) -> float:
        """Average maximum dependency depth per sentence."""
        depths = []
        for sent in doc.sents:

            def _depth(token, d=0):
                if not list(token.children):
                    return d
                return max(_depth(c, d + 1) for c in token.children)

            depths.append(_depth(sent.root))
        return float(np.mean(depths)) if depths else 0.0

    @staticmethod
    def _subordinate_clause_ratio(doc) -> float:
        total = sum(1 for _ in doc.sents)
        sub = sum(1 for t in doc if t.dep_ in ("advcl", "relcl", "acl", "ccomp", "xcomp"))
        return sub / max(total, 1)

    @staticmethod
    def _passive_voice_ratio(doc) -> float:
        total_verbs = sum(1 for t in doc if t.pos_ == "VERB")
        passive = sum(
            1 for t in doc if t.dep_ in ("nsubjpass", "auxpass") or t.dep_ == "nsubj:pass"
        )
        return passive / max(total_verbs, 1)

    # ── punctuation patterns ────────────────────────────────────────────

    @staticmethod
    def _punctuation_features(text: str, num_tokens: int) -> Dict[str, float]:
        n = max(num_tokens, 1)
        return {
            "punct_density": len(re.findall(r"[^\w\s]", text)) / n,
            "em_dash_count": text.count("\u2014") + text.count("--"),
            "ellipsis_count": text.count("...") + text.count("\u2026"),
        }

    # ── discourse markers ───────────────────────────────────────────────

    @staticmethod
    def _discourse_features(text: str) -> Dict[str, float]:
        lower = text.lower()
        word_count = max(len(text.split()), 1)
        ai_hits = sum(lower.count(m) for m in AI_DISCOURSE_MARKERS)
        human_hits = sum(lower.count(m) for m in HUMAN_DISCOURSE_MARKERS)
        return {
            "ai_marker_density": ai_hits / word_count,
            "human_marker_density": human_hits / word_count,
        }

    # ── functional patterns ─────────────────────────────────────────────

    @staticmethod
    def _functional_features(doc) -> Dict[str, float]:
        func_tags = {"DET", "ADP", "CCONJ", "SCONJ", "PRON", "AUX", "PART"}
        func_count = sum(1 for t in doc if t.pos_ in func_tags)
        content_count = sum(1 for t in doc if t.pos_ not in func_tags)
        ratio = func_count / max(content_count, 1)
        contraction_count = sum(1 for t in doc if "'" in t.text and t.pos_ != "PUNCT")
        return {
            "func_content_ratio": ratio,
            "contraction_density": contraction_count / max(len(doc), 1),
        }

    # ── feature vector ──────────────────────────────────────────────────

    async def _extract_features(self, text: str) -> np.ndarray:
        nlp = await ModelRegistry.get_model("spacy")
        doc = nlp(text)

        tokens = [t.text.lower() for t in doc if t.is_alpha]
        sent_lengths = [len(list(s)) for s in doc.sents]

        feats: List[float] = []

        # lexical (5)
        feats.append(self._ttr(tokens))
        feats.append(self._mattr(tokens))
        feats.append(self._hapax_ratio(tokens))
        feats.append(self._yules_k(tokens))
        feats.append(self._simpsons_d(tokens))

        # sentence structure (4)
        sf = self._sentence_features(sent_lengths)
        feats.extend([sf["sent_mean"], sf["sent_std"], sf["sent_bimodality"], sf["sent_range"]])

        # syntactic complexity (3)
        feats.append(self._dep_depth(doc))
        feats.append(self._subordinate_clause_ratio(doc))
        feats.append(self._passive_voice_ratio(doc))

        # punctuation (3)
        pf = self._punctuation_features(text, len(tokens))
        feats.extend([pf["punct_density"], pf["em_dash_count"], pf["ellipsis_count"]])

        # discourse markers (2)
        df = self._discourse_features(text)
        feats.extend([df["ai_marker_density"], df["human_marker_density"]])

        # functional (2)
        ff = self._functional_features(doc)
        feats.extend([ff["func_content_ratio"], ff["contraction_density"]])

        # POS distribution entropy (1)
        pos_counts = Counter(t.pos_ for t in doc)
        total_pos = sum(pos_counts.values())
        pos_probs = [c / total_pos for c in pos_counts.values()]
        pos_entropy = -sum(p * math.log2(p) for p in pos_probs if p > 0)
        feats.append(pos_entropy)

        # additional richness (7 more to reach 27)
        feats.append(
            float(np.mean([len(t.text) for t in doc if t.is_alpha])) if tokens else 0.0
        )  # avg word len
        feats.append(float(len(set(tokens))) if tokens else 0.0)  # unique words
        feats.append(sum(1 for t in doc if t.is_stop) / max(len(doc), 1))  # stopword ratio
        feats.append(len(sent_lengths))  # num sentences
        feats.append(float(np.median(sent_lengths)) if sent_lengths else 0.0)  # median sent len
        feats.append(
            float(np.percentile(sent_lengths, 90)) if len(sent_lengths) >= 2 else 0.0
        )  # p90 sent len
        feats.append(sum(1 for t in doc if t.pos_ == "ADJ") / max(len(doc), 1))  # adj ratio

        return np.array(feats, dtype=np.float64)  # 27 features

    def _fallback_score(self, features: np.ndarray) -> float:
        ttr = features[0]
        mattr = features[1]
        ai_markers = features[17]
        human_markers = features[18]
        sent_std = features[6]
        contraction = features[20]

        score = (
            0.20 * self._sigmoid(-(ttr - 0.55) / 0.1)
            + 0.15 * self._sigmoid(-(mattr - 0.6) / 0.1)
            + 0.15 * self._sigmoid((ai_markers - 0.01) / 0.005)
            + 0.15 * self._sigmoid(-(human_markers - 0.005) / 0.003)
            + 0.15 * self._sigmoid(-(sent_std - 8) / 3)
            + 0.10 * self._sigmoid(-(contraction - 0.02) / 0.01)
            + 0.10 * 0.5
        )
        return self._clamp(score)

    async def analyze(self, text: str) -> dict:
        signal = "stylometric"
        if len(text.split()) < 20:
            return self._empty_result(signal, "text too short (< 20 words)")

        features = await self._extract_features(text)

        if self._classifier is not None:
            try:
                ai_prob = float(self._classifier.predict_proba(features.reshape(1, -1))[0][1])
                method = "gradient_boosting"
            except Exception as exc:
                logger.warning("Stylometric classifier failed: %s", exc)
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
                "feature_names": [
                    "ttr",
                    "mattr",
                    "hapax_ratio",
                    "yules_k",
                    "simpsons_d",
                    "sent_mean",
                    "sent_std",
                    "sent_bimodality",
                    "sent_range",
                    "dep_depth",
                    "subordinate_clause_ratio",
                    "passive_voice_ratio",
                    "punct_density",
                    "em_dash_count",
                    "ellipsis_count",
                    "ai_marker_density",
                    "human_marker_density",
                    "func_content_ratio",
                    "contraction_density",
                    "pos_entropy",
                    "avg_word_len",
                    "unique_words",
                    "stopword_ratio",
                    "num_sentences",
                    "median_sent_len",
                    "p90_sent_len",
                    "adj_ratio",
                ],
                "feature_values": [round(float(f), 4) for f in features],
            },
        }
