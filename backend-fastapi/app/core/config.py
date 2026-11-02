"""Environment driven application settings."""

from __future__ import annotations

import os
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

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def parse_database_url(cls, v: Any) -> str:
        url = str(v).strip() if v else "sqlite+aiosqlite:///./budgetbuddy.db"
        # In serverless environments (Vercel/AWS Lambda), the root filesystem is read-only
        if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) and "sqlite" in url and not url.startswith("sqlite+aiosqlite:////tmp/"):
            return "sqlite+aiosqlite:////tmp/budgetbuddy.db"
        return url

    @field_validator("LOCAL_STORAGE_DIR", mode="before")
    @classmethod
    def parse_local_storage_dir(cls, v: Any) -> str:
        # In serverless environments, store files in writable /tmp
        if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            return "/tmp/media"
        return str(v or "./media")

    # JWT lifetimes — DRF SimpleJWT parity.
    ACCESS_TOKEN_MINUTES: int = 60
    REFRESH_TOKEN_DAYS: int = 7

    # DRF PAGE_SIZE parity.
    PAGE_SIZE: int = 20

    # CORS
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://budgetbuddy-student.vercel.app,https://frontend-iota-black-70.vercel.app"
    )
    CORS_ORIGIN_REGEX: str = r"^https://.*\.vercel\.app$"

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
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            try:
                import json
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        items = []
        for item in raw.split(","):
            cleaned = item.strip().strip("[]\"' ")
            if cleaned:
                items.append(cleaned)
        return items

    @property
    def gemini_models(self) -> list[str]:
        return [item.strip() for item in self.GEMINI_MODELS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
