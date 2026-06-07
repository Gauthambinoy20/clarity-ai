from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle hook."""

    # -- Startup ----------------------------------------------------------
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Initialise the database (create tables if they don't exist)
    from app.db.database import init_db

    await init_db()
    logger.info("Database ready")

    # Ensure required NLTK data is available
    _download_nltk_data()

    # Create upload directory if needed
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    yield

    # -- Shutdown ---------------------------------------------------------
    from app.db.database import dispose_engine
    from app.ml.models.model_registry import ModelRegistry

    await ModelRegistry.unload_all()
    await dispose_engine()
    logger.info("%s shut down cleanly", settings.APP_NAME)


def _download_nltk_data() -> None:
    """Download NLTK resources used by detection/humanization pipelines."""
    import nltk

    packages = ["punkt", "punkt_tab", "averaged_perceptron_tagger", "stopwords"]
    for pkg in packages:
        try:
            nltk.data.find(
                f"tokenizers/{pkg}"
                if "punkt" in pkg
                else f"corpora/{pkg}" if pkg == "stopwords" else f"taggers/{pkg}"
            )
        except LookupError:
            logger.info("Downloading NLTK resource: %s", pkg)
            nltk.download(pkg, quiet=True)


# ── Application factory ──────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    # -- CORS -------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # -- Rate Limiting ----------------------------------------------------
    from app.core.rate_limiter import add_rate_limiting

    add_rate_limiting(app)

    # -- Routers ----------------------------------------------------------
    _include_routers(app)

    return app


def _include_routers(app: FastAPI) -> None:
    """Import and mount all API routers under /api/v1."""
    from app.api.routes import (
        advanced,
        analytics,
        dashboard,
        detection,
        export,
        health,
        humanization,
        plagiarism,
        realtime,
    )

    prefix = "/api/v1"

    app.include_router(
        health.router,
        prefix=prefix,
        tags=["health"],
    )
    app.include_router(
        detection.router,
        prefix=prefix,
        tags=["detection"],
    )
    app.include_router(
        plagiarism.router,
        prefix=prefix,
        tags=["plagiarism"],
    )
    app.include_router(
        humanization.router,
        prefix=prefix,
        tags=["humanization"],
    )
    app.include_router(
        analytics.router,
        prefix=prefix,
        tags=["analytics"],
    )
    app.include_router(
        export.router,
        prefix=prefix,
        tags=["export"],
    )
    app.include_router(
        dashboard.router,
        prefix=prefix,
        tags=["dashboard"],
    )
    app.include_router(
        advanced.router,
        prefix=prefix,
        tags=["advanced"],
    )
    # WebSocket routes (mounted at root, no prefix — /ws/detect)
    app.include_router(
        realtime.router,
        tags=["realtime"],
    )


# Expose the ASGI app for `uvicorn app.main:app`
app = create_app()
