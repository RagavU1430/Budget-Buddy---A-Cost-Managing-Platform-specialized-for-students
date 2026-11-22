"""Async SQLAlchemy engine and request-scoped session dependency.

Two Supabase connection modes matter here:

* **Session pooler** (``:5432``) — a long-lived Postgres session behind
  PgBouncer. Prepared statements work, so the default asyncpg cache is fine.
  Use this for the API *and* for Alembic.
* **Transaction pooler** (``:6543``) — the connection can be handed to another
  client between statements, so server-side prepared statements must be
  disabled (``statement_cache_size=0``).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

TRANSACTION_POOLER_PORT = 6543


def _connect_args(url: str) -> dict[str, Any]:
    """asyncpg options that depend on the Supabase / Neon / remote pooler mode."""
    if not url.startswith("postgresql+asyncpg"):
        return {}
    args: dict[str, Any] = {}
    try:
        parsed = urlsplit(url.replace("postgresql+asyncpg", "postgresql", 1))
        port = parsed.port
        if port == TRANSACTION_POOLER_PORT:
            args["statement_cache_size"] = 0
        # Determine if SSL is required:
        # - Always require SSL for remote hosts (non-localhost)
        # - Also require SSL in serverless environments (Vercel, Lambda) even for localhost tunnels
        is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        hostname = parsed.hostname
        if hostname and (hostname not in ("localhost", "127.0.0.1") or is_serverless):
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            args["ssl"] = ctx
    except Exception:
        pass
    return args


def _build_engine(url: str) -> AsyncEngine:
    is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=not is_serverless,
        pool_size=2 if is_serverless else 5,
        max_overflow=5 if is_serverless else 10,
        pool_recycle=300,
        connect_args=_connect_args(url),
    )


engine: AsyncEngine = _build_engine(settings.DATABASE_URL)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session that rolls back on error."""
    async with SessionLocal() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    await engine.dispose()
