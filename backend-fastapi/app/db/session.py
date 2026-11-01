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
    """asyncpg options that depend on the Supabase pooler mode."""
    if not url.startswith("postgresql+asyncpg"):
        return {}
    try:
        port = urlsplit(url.replace("postgresql+asyncpg", "postgresql", 1)).port
    except ValueError:  # pragma: no cover - malformed URL
        return {}
    if port == TRANSACTION_POOLER_PORT:
        return {"statement_cache_size": 0}
    return {}


def _build_engine(url: str) -> AsyncEngine:
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
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
