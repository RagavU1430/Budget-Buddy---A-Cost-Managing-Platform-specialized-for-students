"""Response shaping — serializer modules in the Django project, as plain dicts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.db import models


def decimal_str(value: Decimal | int | float | None) -> str | None:
    """DRF DecimalField with COERCE_TO_STRING=True."""
    if value is None:
        return None
    return f"{Decimal(value):.2f}"


def decimal_float(value: Decimal | int | float | None) -> float:
    """DRF JSONEncoder: raw Decimal rendered by analytics endpoints."""
    if value is None:
        return 0.0
    return float(value)


def date_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


date_str_for_json = date_iso


def dt_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Users / profiles
# ---------------------------------------------------------------------------
def profile_dict(profile: models.Profile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {
        "phone": profile.phone,
        "avatar_url": profile.avatar_url,
        "monthly_income": decimal_str(profile.monthly_income),
        "currency": profile.currency,
        "financial_preferences": profile.financial_preferences or {},
        "created_at": dt_iso(profile.created_at),
        "updated_at": dt_iso(profile.updated_at),
    }


def user_dict(user: models.User, profile: models.Profile | None) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_staff": user.is_staff,
        "profile": profile_dict(profile),
        "date_joined": dt_iso(user.date_joined),
    }


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
def expense_dict(expense: models.Expense) -> dict[str, Any]:
    return {
        "id": expense.id,
        "category": expense.category,
        "title": expense.title,
        "amount": decimal_str(expense.amount),
        "date": date_iso(expense.date),
        "payment_method": expense.payment_method,
        "notes": expense.notes,
        "created_at": dt_iso(expense.created_at),
        "updated_at": dt_iso(expense.updated_at),
    }


def income_dict(income: models.Income) -> dict[str, Any]:
    return {
        "id": income.id,
        "source_type": income.source_type,
        "title": income.title,
        "amount": decimal_str(income.amount),
        "date": date_iso(income.date),
        "notes": income.notes,
        "created_at": dt_iso(income.created_at),
        "updated_at": dt_iso(income.updated_at),
    }


def budget_dict(budget: models.Budget) -> dict[str, Any]:
    return {
        "id": budget.id,
        "month": date_iso(budget.month),
        "category": budget.category,
        "limit_amount": decimal_str(budget.limit_amount),
        "created_at": dt_iso(budget.created_at),
        "updated_at": dt_iso(budget.updated_at),
    }


def goal_progress_pct(goal: models.SavingsGoal) -> float:
    if not goal.target_amount:
        return 0.0
    return round(float(goal.current_amount / goal.target_amount) * 100, 2)


def goal_dict(goal: models.SavingsGoal) -> dict[str, Any]:
    pct = goal_progress_pct(goal)
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "target_amount": decimal_str(goal.target_amount),
        "current_amount": decimal_str(goal.current_amount),
        "saved_amount": decimal_str(goal.current_amount),
        "target_date": date_iso(goal.target_date),
        "deadline": date_iso(goal.target_date),
        "priority": goal.priority,
        "is_completed": goal.is_completed,
        "progress_pct": pct,
        "progress_percentage": pct,
        "created_at": dt_iso(goal.created_at),
        "updated_at": dt_iso(goal.updated_at),
    }


def notification_dict(notification: models.Notification) -> dict[str, Any]:
    return {
        "id": notification.id,
        "notification_type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": dt_iso(notification.created_at),
    }


def report_dict(report: models.Report, download_url: str | None) -> dict[str, Any]:
    return {
        "id": report.id,
        "report_type": report.report_type,
        "month": date_iso(report.month),
        "file_format": report.file_format,
        "file": report.file,
        "download_url": download_url,
        "summary": report.summary or {},
        "generated_at": dt_iso(report.generated_at),
    }


def chat_dict(message: models.ChatMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "action_type": message.action_type,
        "action_data": message.action_data or {},
        "created_at": dt_iso(message.created_at),
    }
