"""Environment driven application settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    APP_NAME: str = "budgetbuddy-api"
    DEBUG: bool = True
    SECRET_KEY: str = "django-insecure-dev-only-change-me"
    JWT_ALGORITHM: str = "HS256"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            clean = v.strip().lower()
            return clean in ("true", "1", "t", "yes", "y", "debug", "development")
        return bool(v)

    # Database (SQLAlchemy async URL)
    DATABASE_URL: str = "sqlite+aiosqlite:///./budgetbuddy.db"
    # Optional direct (non-pooled) URL for Alembic. Falls back to DATABASE_URL.
    DIRECT_DATABASE_URL: str | None = None

    # JWT lifetimes — DRF SimpleJWT parity.
    ACCESS_TOKEN_MINUTES: int = 60
    REFRESH_TOKEN_DAYS: int = 7

    # DRF PAGE_SIZE parity.
    PAGE_SIZE: int = 20

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Assistant
    GEMINI_API_KEY: str = ""
    GEMINI_MODELS: str = "models/gemini-2.5-flash,models/gemini-2.0-flash"
    GEMINI_TIMEOUT_SECONDS: float = 10.0

    # Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "./media"
    SUPABASE_S3_ENDPOINT: str = ""
    SUPABASE_S3_REGION: str = "ap-south-1"
    SUPABASE_S3_ACCESS_KEY_ID: str = ""
    SUPABASE_S3_SECRET_ACCESS_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "reports"
    SUPABASE_SIGNED_URL_TTL: int = 300

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def gemini_models(self) -> list[str]:
        return [item.strip() for item in self.GEMINI_MODELS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
