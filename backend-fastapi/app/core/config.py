"""Environment driven application settings."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRET_KEY = "django-insecure-dev-only-change-me"


def _normalize_database_url(url: str) -> str:
    """Normalize database URL for asyncpg: strip SSL params, fix driver, validate."""
    url = str(url).strip()

    if not url:
        raise ValueError(
            "DATABASE_URL is required. Supabase PostgreSQL is mandatory. "
            "Set DATABASE_URL=postgresql+asyncpg://postgres:password@host:5432/dbname"
        )

    # Parse URL to manipulate query parameters cleanly
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)

    # Strip all SSL-related query parameters (asyncpg uses connect_args for SSL)
    ssl_params = {"sslmode", "sslcert", "sslkey", "sslrootcert", "sslcrl", "ssl_min_protocol_version"}
    filtered_params = {k: v for k, v in query_params.items() if k not in ssl_params}

    # Reconstruct URL without SSL params
    new_query = urlencode(filtered_params, doseq=True)
    parsed = parsed._replace(query=new_query)
    url = urlunparse(parsed)

    # Normalize postgres driver to asyncpg for SQLAlchemy async engine
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    APP_NAME: str = "budgetbuddy-api"
    DEBUG: bool = False
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ADMIN_API_KEY: str = ""

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            clean = v.strip().lower()
            return clean in ("true", "1", "t", "yes", "y", "debug", "development")
        return bool(v)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure production uses a strong secret key, not the default."""
        if v == DEFAULT_SECRET_KEY:
            # Check if we're in production (not DEBUG, not localhost DB)
            is_production = (
                not os.getenv("DEBUG", "").lower() in ("true", "1", "t", "yes", "y", "debug", "development")
                and "localhost" not in os.getenv("DATABASE_URL", "")
                and "127.0.0.1" not in os.getenv("DATABASE_URL", "")
            )
            if is_production:
                raise ValueError(
                    "SECRET_KEY must be changed from default in production. "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_production(cls, v: bool, info) -> bool:
        """Warn/block DEBUG=True in production-like environments."""
        # Allow DEBUG locally, but check if production env vars are set
        if v:
            db_url = os.getenv("DATABASE_URL", "")
            if db_url and "localhost" not in db_url and "127.0.0.1" not in db_url:
                import warnings
                warnings.warn(
                    "DEBUG=True with remote database — ensure this is intentional for production!",
                    RuntimeWarning,
                    stacklevel=2,
                )
        return v

    # Database (SQLAlchemy async URL) - Supabase PostgreSQL is mandatory
    DATABASE_URL: str = ""
    # Optional direct (non-pooled) URL for Alembic. Falls back to DATABASE_URL.
    DIRECT_DATABASE_URL: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def parse_database_url(cls, v: Any) -> str:
        raw = (
            v
            or os.getenv("DATABASE_URL")
            or os.getenv("POSTGRES_URL")
            or os.getenv("POSTGRES_PRISMA_URL")
            or ""
        )
        return _normalize_database_url(raw)

    @field_validator("DIRECT_DATABASE_URL", mode="before")
    @classmethod
    def parse_direct_database_url(cls, v: Any) -> str | None:
        if v is None or v == "":
            return None
        return _normalize_database_url(v)

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

    # CORS - Restricted to known domains only (no wildcard regex)
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://budgetbuddy-student.vercel.app,https://frontend-iota-black-70.vercel.app,"
        "https://budgetbuddy-app-six.vercel.app"
    )
    # CORS_ORIGIN_REGEX removed — use explicit CORS_ORIGINS list for security

    # Assistant
    GEMINI_API_KEY: str = ""
    GEMINI_MODELS: str = "models/gemini-2.5-flash,models/gemini-2.0-flash"
    GEMINI_TIMEOUT_SECONDS: float = 10.0

    # Email verification
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

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
