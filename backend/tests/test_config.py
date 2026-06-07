"""
Settings parsing tests — pinned after CORS_ORIGINS from the environment
crashed the container on boot (pydantic-settings JSON-decoded the comma
string before the splitting validator could run).
"""

from __future__ import annotations

from app.core.config import Settings


def test_cors_origins_parses_comma_separated_env(monkeypatch):
    """A plain comma list — exactly what docker-compose passes — must work."""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://example.com")
    settings = Settings(_env_file=None)
    assert settings.CORS_ORIGINS == ["http://localhost:5173", "http://example.com"]


def test_cors_origins_strips_blanks_and_spaces(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " http://a.test , ,http://b.test ")
    settings = Settings(_env_file=None)
    assert settings.CORS_ORIGINS == ["http://a.test", "http://b.test"]


def test_cors_origins_default_list_survives():
    settings = Settings(_env_file=None)
    assert "http://localhost:5173" in settings.CORS_ORIGINS


def test_log_level_is_normalised(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    settings = Settings(_env_file=None)
    assert settings.LOG_LEVEL == "DEBUG"
