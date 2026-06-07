from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Singleton lazy-loading registry for ML models.

    Models are downloaded / loaded on first access and then cached for the
    lifetime of the process.  All loading is serialised behind an asyncio.Lock
    so concurrent requests never trigger duplicate downloads.

    Usage::

        tokenizer, model = await ModelRegistry.get_model("gpt2")
        pipe = await ModelRegistry.get_model("roberta-detector-1")
        nlp = await ModelRegistry.get_model("spacy")
        st_model = await ModelRegistry.get_model("sentence-transformers")
    """

    _instance: Optional[ModelRegistry] = None
    _cache: Dict[str, Any] = {}
    _lock: asyncio.Lock = asyncio.Lock()

    # Maps friendly identifiers to Hugging Face model IDs / local names
    _MODEL_MAP: Dict[str, str] = {
        "gpt2": settings.GPT2_MODEL,
        "distilgpt2": settings.DISTILGPT2_MODEL,
        "gpt2-medium": settings.GPT2_MEDIUM_MODEL,
        "roberta-detector-1": settings.ROBERTA_DETECTOR_1,
        "roberta-detector-2": settings.ROBERTA_DETECTOR_2,
        "ai-detector-3": settings.AI_DETECTOR_3,
        "sentence-transformers": settings.SENTENCE_MODEL,
        "spacy": settings.SPACY_MODEL,
    }

    def __new__(cls) -> ModelRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── public API ───────────────────────────────────────────────────────

    @classmethod
    async def get_model(cls, model_id: str) -> Any:
        """Return a cached model (or load it on first call).

        Parameters
        ----------
        model_id:
            A key from ``_MODEL_MAP`` (e.g. ``"gpt2"``, ``"spacy"``).

        Returns
        -------
        The loaded model object.  For causal-LM models this is a
        ``(tokenizer, model)`` tuple; for classifiers a
        ``transformers.pipeline``; for spaCy a ``Language``; for
        sentence-transformers a ``SentenceTransformer``.
        """
        if model_id in cls._cache:
            return cls._cache[model_id]

        async with cls._lock:
            # Double-check after acquiring the lock
            if model_id in cls._cache:
                return cls._cache[model_id]

            hub_id = cls._MODEL_MAP.get(model_id)
            if hub_id is None:
                raise ValueError(
                    f"Unknown model_id {model_id!r}. " f"Available: {list(cls._MODEL_MAP.keys())}"
                )

            logger.info("Loading model %s (%s) ...", model_id, hub_id)
            start = time.perf_counter()

            loop = asyncio.get_running_loop()
            loaded = await loop.run_in_executor(None, cls._load_sync, model_id, hub_id)

            elapsed = time.perf_counter() - start
            logger.info("Model %s loaded in %.2f s", model_id, elapsed)

            cls._cache[model_id] = loaded
            return loaded

    @classmethod
    async def preload(cls, model_ids: list[str] | None = None) -> None:
        """Optionally pre-warm selected models at startup."""
        targets = model_ids or []
        for mid in targets:
            await cls.get_model(mid)

    @classmethod
    async def unload(cls, model_id: str) -> None:
        """Remove a model from the cache to free memory."""
        async with cls._lock:
            obj = cls._cache.pop(model_id, None)
            if obj is not None:
                logger.info("Unloaded model %s", model_id)

    @classmethod
    async def unload_all(cls) -> None:
        """Remove every cached model."""
        async with cls._lock:
            cls._cache.clear()
            logger.info("All models unloaded")

    @classmethod
    def list_available(cls) -> list[str]:
        """Return the list of known model identifiers."""
        return list(cls._MODEL_MAP.keys())

    @classmethod
    def list_loaded(cls) -> list[str]:
        """Return identifiers of currently cached models."""
        return list(cls._cache.keys())

    # ── private synchronous loaders (run in thread pool) ─────────────────

    @classmethod
    def _load_sync(cls, model_id: str, hub_id: str) -> Any:
        """Dispatch to the correct loader based on *model_id*."""
        if model_id in ("gpt2", "distilgpt2", "gpt2-medium"):
            return cls._load_causal_lm(hub_id)
        if model_id in ("roberta-detector-1", "roberta-detector-2", "ai-detector-3"):
            return cls._load_classifier_pipeline(hub_id)
        if model_id == "spacy":
            return cls._load_spacy(hub_id)
        if model_id == "sentence-transformers":
            return cls._load_sentence_transformer(hub_id)
        raise ValueError(f"No loader implemented for {model_id!r}")

    @staticmethod
    def _load_causal_lm(hub_id: str) -> tuple:
        """Load a causal-LM tokenizer + model from Hugging Face."""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(hub_id)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(hub_id)
        model.eval()
        return tokenizer, model

    @staticmethod
    def _load_classifier_pipeline(hub_id: str) -> Any:
        """Load a text-classification pipeline from Hugging Face."""
        from transformers import pipeline as hf_pipeline

        return hf_pipeline("text-classification", model=hub_id, truncation=True)

    @staticmethod
    def _load_spacy(model_name: str) -> Any:
        """Load a spaCy language model, downloading if necessary."""
        import spacy

        try:
            return spacy.load(model_name)
        except OSError:
            logger.warning("spaCy model %s not found, downloading ...", model_name)
            from spacy.cli import download as spacy_download

            spacy_download(model_name)
            return spacy.load(model_name)

    @staticmethod
    def _load_sentence_transformer(hub_id: str) -> Any:
        """Load a SentenceTransformer model."""
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(hub_id)
