from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the ClarityAI application.

    Values are read from environment variables first, then from a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────────────────────
    APP_NAME: str = "ClarityAI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered content analysis, plagiarism detection and humanization"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production"

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./clarityai.db"
    DB_ECHO: bool = False

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 3600
    RATE_LIMIT_BURST: int = 5

    # ── ML Model identifiers (Hugging Face hub) ─────────────────────────
    GPT2_MODEL: str = "openai-community/gpt2"
    DISTILGPT2_MODEL: str = "distilgpt2"
    GPT2_MEDIUM_MODEL: str = "openai-community/gpt2-medium"
    ROBERTA_DETECTOR_1: str = "Hello-SimpleAI/chatgpt-detector-roberta"
    ROBERTA_DETECTOR_2: str = "openai-community/roberta-large-openai-detector"
    AI_DETECTOR_3: str = "PirateXX/AI-Content-Detector"
    SENTENCE_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    SPACY_MODEL: str = "en_core_web_sm"

    # ── Ollama (local LLM rewriting) ─────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b-instruct"
    OLLAMA_TIMEOUT: int = 120

    # ── Detection thresholds ─────────────────────────────────────────────
    MIN_WORDS: int = 50
    MAX_WORDS: int = 10000
    FAST_MODE_SIGNALS: int = 3
    DEEP_MODE_SIGNALS: int = 14
    AI_THRESHOLD_HIGH: float = 0.85
    AI_THRESHOLD_MEDIUM: float = 0.50

    # ── Humanization ─────────────────────────────────────────────────────
    HUMANIZE_TARGET_AI_SCORE: float = 0.10
    HUMANIZE_TARGET_PLAG_SCORE: float = 0.10
    HUMANIZE_MAX_ITERATIONS: int = 5
    HUMANIZE_TEMPERATURE: float = 0.7

    # ── Plagiarism ───────────────────────────────────────────────────────
    PLAG_SIMILARITY_THRESHOLD: float = 0.80
    PLAG_CHUNK_SIZE: int = 3

    # ── Batch processing ─────────────────────────────────────────────────
    BATCH_MAX_FILES: int = 50
    BATCH_MAX_FILE_SIZE_MB: int = 10

    # ── Paths ────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MODELS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "models"
    UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "uploads"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return upper


settings = Settings()
