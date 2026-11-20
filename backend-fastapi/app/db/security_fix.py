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

# RLS Policies - each policy allows users to access only their own data via auth.uid()
# Tables must have a `user_id` column referencing `public.users(id)`
RLS_POLICIES = {
    "users": "CREATE POLICY users_own_data ON public.users FOR ALL USING (id = auth.uid())",
    "profiles": "CREATE POLICY profiles_own_data ON public.profiles FOR ALL USING (user_id = auth.uid())",
    "incomes": "CREATE POLICY incomes_own_data ON public.incomes FOR ALL USING (user_id = auth.uid())",
    "expenses": "CREATE POLICY expenses_own_data ON public.expenses FOR ALL USING (user_id = auth.uid())",
    "budgets": "CREATE POLICY budgets_own_data ON public.budgets FOR ALL USING (user_id = auth.uid())",
    "savings_goals": "CREATE POLICY savings_goals_own_data ON public.savings_goals FOR ALL USING (user_id = auth.uid())",
    "notifications": "CREATE POLICY notifications_own_data ON public.notifications FOR ALL USING (user_id = auth.uid())",
    "chat_messages": "CREATE POLICY chat_messages_own_data ON public.chat_messages FOR ALL USING (user_id = auth.uid())",
    "reports": "CREATE POLICY reports_own_data ON public.reports FOR ALL USING (user_id = auth.uid())",
    "email_change_requests": "CREATE POLICY email_change_requests_own_data ON public.email_change_requests FOR ALL USING (user_id = auth.uid())",
    "email_change_history": "CREATE POLICY email_change_history_own_data ON public.email_change_history FOR ALL USING (user_id = auth.uid())",
    "refresh_tokens": "CREATE POLICY refresh_tokens_own_data ON public.refresh_tokens FOR ALL USING (user_id = auth.uid())",
}


async def _create_rls_policies(conn: AsyncConnection) -> list[dict[str, Any]]:
    """Create RLS policies for all user-scoped tables."""
    results = []
    for table, policy_sql in RLS_POLICIES.items():
        try:
            # Check if table exists first
            check = await conn.execute(
                text("SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = :t"),
                {"t": table}
            )
            if not check.scalar_one_or_none():
                results.append({"table": table, "policy_created": False, "reason": "table_not_found"})
                continue

            # Drop existing policy if any (idempotent)
            await conn.execute(text(f'DROP POLICY IF EXISTS {table}_own_data ON public."{table}"'))
            # Create new policy
            await conn.execute(text(policy_sql))
            await conn.commit()
            results.append({"table": table, "policy_created": True})
            logger.info(f"[SecurityFix] Created RLS policy for {table}")
        except Exception as e:
            try:
                await conn.rollback()
            except Exception:
                pass
            logger.error(f"[SecurityFix] Failed to create RLS policy for {table}: {e}")
            results.append({"table": table, "policy_created": False, "error": str(e)})
    return results


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
            "policies": [],
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
        # Upgrade monetary amount precision across all tables to NUMERIC(16, 2)
        "ALTER TABLE public.incomes ALTER COLUMN amount TYPE NUMERIC(16, 2)",
        "ALTER TABLE public.expenses ALTER COLUMN amount TYPE NUMERIC(16, 2)",
        "ALTER TABLE public.budgets ALTER COLUMN limit_amount TYPE NUMERIC(16, 2)",
        "ALTER TABLE public.savings_goals ALTER COLUMN target_amount TYPE NUMERIC(16, 2)",
        "ALTER TABLE public.savings_goals ALTER COLUMN current_amount TYPE NUMERIC(16, 2)",
        "ALTER TABLE public.profiles ALTER COLUMN monthly_income TYPE NUMERIC(16, 2)",
    ]
    for stmt in ddl_statements:
        try:
            await conn.execute(text(stmt))
            await conn.commit()
        except Exception as stmt_exc:
            try:
                await conn.rollback()
            except Exception:
                pass
            logger.warning(f"[SecurityFix] DDL statement notice: {stmt_exc}")

    # 1. Fetch all tables currently in the public schema
    res = await conn.execute(
        text("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    )
    tables = res.fetchall()

    status_list: list[dict[str, Any]] = []

    for tablename, rowsecurity in tables:
        try:
            # Enable and FORCE RLS on each table in public schema
            await conn.execute(text(f'ALTER TABLE public."{tablename}" ENABLE ROW LEVEL SECURITY'))
            await conn.execute(text(f'ALTER TABLE public."{tablename}" FORCE ROW LEVEL SECURITY'))
            # Revoke direct table permissions from anon & authenticated
            await conn.execute(
                text(f'REVOKE ALL ON TABLE public."{tablename}" FROM anon, authenticated')
            )
            await conn.commit()
        except Exception as e:
            try:
                await conn.rollback()
            except Exception:
                pass
            logger.error(f"[SecurityFix] Table security update notice for {tablename}: {e}")

        status_list.append({
            "table": tablename,
            "rls_enabled": True,
            "was_previously_enabled": bool(rowsecurity),
        })

    # 2. Create RLS policies for user-scoped tables
    policy_results = await _create_rls_policies(conn)

    # Revoke schema USAGE from anon, authenticated, and PUBLIC
    try:
        await conn.execute(
            text('REVOKE USAGE ON SCHEMA public FROM anon, authenticated, PUBLIC')
        )
        await conn.commit()
    except Exception as e:
        try:
            await conn.rollback()
        except Exception:
            pass

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
            await conn.commit()
        except Exception as e:
            try:
                await conn.rollback()
            except Exception:
                pass
            logger.error(f"[SecurityFix] Failed to execute: {stmt[:60]}...: {e}")

    return {
        "applied": True,
        "dialect": dialect_name,
        "total_tables": len(tables),
        "tables": status_list,
        "policies": policy_results,
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
            "policies": [],
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

    # Check policy status
    policy_status = []
    for table in RLS_POLICIES.keys():
        try:
            check = await conn.execute(
                text("""
                    SELECT polname FROM pg_policy
                    WHERE polrelid = (SELECT oid FROM pg_class WHERE relname = :t AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public'))
                    AND polname = :p
                """),
                {"t": table, "p": f"{table}_own_data"}
            )
            policy_status.append({"table": table, "policy_exists": check.scalar_one_or_none() is not None})
        except Exception:
            policy_status.append({"table": table, "policy_exists": False})

    return {
        "dialect": dialect_name,
        "is_postgres": True,
        "total_tables": len(tables),
        "all_rls_enabled": all_enabled,
        "tables": tables,
        "policies": policy_status,
    }
