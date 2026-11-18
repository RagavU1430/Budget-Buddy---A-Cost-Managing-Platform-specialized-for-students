"""Database security hardening for Supabase / PostgreSQL.

Enforces Row-Level Security (RLS) on all public tables and revokes
unrestricted PostgREST direct access from `anon` and `authenticated` roles,
resolving Supabase Security Advisor warnings:
1. `rls_disabled_in_public`
2. `sensitive_columns_exposed`
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)


async def apply_database_security_hardening(conn: AsyncConnection) -> dict[str, Any]:
    """Inspects all tables in the `public` schema and enables RLS.

    Also revokes public REST API access from the `anon` and `authenticated` roles
    so sensitive data cannot be accessed directly bypassing the FastAPI backend.
    """
    dialect_name = conn.dialect.name
    if dialect_name != "postgresql":
        return {
            "applied": False,
            "dialect": dialect_name,
            "message": "Security hardening (RLS) is only applicable to PostgreSQL/Supabase databases.",
            "tables": [],
        }

    # 0. Ensure all modern auth and security tables exist before scanning
    ddl_statements = [
        """CREATE TABLE IF NOT EXISTS public.email_change_requests (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
            new_email VARCHAR(254) NOT NULL,
            otp_hash VARCHAR(64) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS public.email_change_history (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            old_email VARCHAR(254) NOT NULL,
            new_email VARCHAR(254) NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS public.refresh_tokens (
            id BIGSERIAL PRIMARY KEY,
            jti VARCHAR(64) NOT NULL UNIQUE,
            user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS ix_email_change_request_user ON public.email_change_requests(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_email_change_request_expires ON public.email_change_requests(expires_at)",
        "CREATE INDEX IF NOT EXISTS ix_email_change_history_user_changed ON public.email_change_history(user_id, changed_at)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_token_jti ON public.refresh_tokens(jti)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_token_user_expires ON public.refresh_tokens(user_id, expires_at)",
    ]
    for stmt in ddl_statements:
        try:
            await conn.execute(text(stmt))
        except Exception as stmt_exc:
            logger.warning(f"[SecurityFix] DDL statement notice: {stmt_exc}")

    # 1. Fetch all tables currently in the public schema
    res = await conn.execute(
        text("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    )
    tables = res.fetchall()

    status_list: list[dict[str, Any]] = []

    for tablename, rowsecurity in tables:
        # Enable and FORCE RLS on each table in public schema
        await conn.execute(text(f'ALTER TABLE public."{tablename}" ENABLE ROW LEVEL SECURITY'))
        await conn.execute(text(f'ALTER TABLE public."{tablename}" FORCE ROW LEVEL SECURITY'))

        # Revoke direct table permissions from anon & authenticated
        try:
            await conn.execute(
                text(f'REVOKE ALL ON TABLE public."{tablename}" FROM anon, authenticated')
            )
        except Exception as e:
            logger.error(f"[SecurityFix] Failed to REVOKE TABLE permissions for {tablename}: {e}")

        status_list.append({
            "table": tablename,
            "rls_enabled": True,
            "was_previously_enabled": bool(rowsecurity),
        })

    # Revoke schema USAGE from anon, authenticated, and PUBLIC
    await conn.execute(
        text('REVOKE USAGE ON SCHEMA public FROM anon, authenticated, PUBLIC')
    )

    # Revoke ALL on tables, sequences, routines from anon and authenticated
    for stmt in [
        "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated",
        "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated",
        "REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON ROUTINES FROM anon, authenticated",
    ]:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logger.error(f"[SecurityFix] Failed to execute: {stmt[:60]}...: {e}")

    return {
        "applied": True,
        "dialect": dialect_name,
        "total_tables": len(tables),
        "tables": status_list,
    }


async def get_database_security_status(conn: AsyncConnection) -> dict[str, Any]:
    """Returns the current RLS status for all tables in the public schema."""
    dialect_name = conn.dialect.name
    if dialect_name != "postgresql":
        return {
            "dialect": dialect_name,
            "is_postgres": False,
            "tables": [],
            "all_rls_enabled": None,  # Not applicable for non-Postgres databases
        }

    res = await conn.execute(
        text("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    )
    rows = res.fetchall()
    tables = [
        {"table": tablename, "rls_enabled": bool(rowsecurity)}
        for tablename, rowsecurity in rows
    ]
    all_enabled = all(t["rls_enabled"] for t in tables) if tables else True

    return {
        "dialect": dialect_name,
        "is_postgres": True,
        "total_tables": len(tables),
        "all_rls_enabled": all_enabled,
        "tables": tables,
    }
