"""
Regression tests for the plagiarism route's semantic similarity helper.

The original code called ModelRegistry.get_sentence_transformer(), a method
that never existed; the broad except swallowed the AttributeError and the
helper returned 0.0 for every pair of texts — semantic scoring through this
route was dead. These tests pin the real registry call and the failure path.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.api.routes import plagiarism
from app.ml.models.model_registry import ModelRegistry


class _FakeSentenceModel:
    """Returns fixed unit vectors so cosine similarity is predictable."""

    def __init__(self, vec_a, vec_b):
        self._vecs = np.array([vec_a, vec_b], dtype=float)

    def encode(self, texts):
        assert len(texts) == 2
        return self._vecs


@pytest.mark.asyncio
async def test_identical_direction_vectors_score_one(monkeypatch):
    fake = _FakeSentenceModel([1.0, 0.0], [1.0, 0.0])

    async def _get_model(model_id):
        assert model_id == "sentence-transformers"  # the real registry key
        return fake

    monkeypatch.setattr(ModelRegistry, "get_model", staticmethod(_get_model))
    sim = await plagiarism._semantic_similarity("a", "b")
    assert sim == pytest.approx(1.0, abs=1e-6)


@pytest.mark.asyncio
async def test_orthogonal_vectors_score_zero(monkeypatch):
    fake = _FakeSentenceModel([1.0, 0.0], [0.0, 1.0])

    async def _get_model(model_id):
        return fake

    monkeypatch.setattr(ModelRegistry, "get_model", staticmethod(_get_model))
    sim = await plagiarism._semantic_similarity("a", "b")
    assert sim == pytest.approx(0.0, abs=1e-6)


@pytest.mark.asyncio
async def test_registry_failure_degrades_to_zero(monkeypatch):
    async def _get_model(model_id):
        raise RuntimeError("model backend unavailable")

    monkeypatch.setattr(ModelRegistry, "get_model", staticmethod(_get_model))
    sim = await plagiarism._semantic_similarity("a", "b")
    assert sim == 0.0
