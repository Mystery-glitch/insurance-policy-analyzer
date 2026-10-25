"""Application configuration and settings."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    All application settings, loaded from environment variables or a .env file.

    Set GEMINI_API_KEY in your environment or .env file before running.
    """

    # ── Paths ──────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "uploads"

    # ── Upload constraints ─────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 20
    ALLOWED_CONTENT_TYPES: set[str] = {"application/pdf"}

    # ── OCR settings ───────────────────────────────────────────────────
    OCR_DPI: int = 300
    OCR_LANGUAGE: str = "eng"

    # ── Gemini AI settings ─────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    EMBEDDING_MODEL: str = "gemini-embedding-001"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton — import this from anywhere
settings = Settings()

# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Convenience aliases (so existing imports don't break) ──────────────
BASE_DIR = settings.BASE_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
MAX_FILE_SIZE_MB = settings.MAX_FILE_SIZE_MB
MAX_FILE_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_CONTENT_TYPES = settings.ALLOWED_CONTENT_TYPES
OCR_DPI = settings.OCR_DPI
OCR_LANGUAGE = settings.OCR_LANGUAGE

