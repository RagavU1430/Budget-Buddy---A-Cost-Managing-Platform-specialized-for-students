"""Analytics router — port of ``apps.expenses.views`` analytics APIViews
(`/api/analytics/summary/`, `/trends/`, `/category-trends/`).

Rendering details preserved:

* every money value moves through Django's JSON encoder → Decimal renders as
  a float, but "no rows" aggregates emit the int ``0`` (``Sum`` → ``or 0``);
* ``month`` labels use ``"%B %Y"`` / ``"%b %Y"``;
* ``remaining_days`` counts down only inside the current month;
* ``months`` is clamped to 1..12 (default 6, 3 for category trends) and any
  ``ValueError`` falls back to the default;
* a bad ``month`` query parameter answers ``{"detail": "month must use YYYY-MM."}``.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import bad_request_detail
from app.core.serializers import date_str_for_json, decimal_float
from app.db import models
from app.services.notifications import month_bounds, utc_today

router = APIRouter()


def _summary_month(raw: str | None) -> date:
    """Port of ``_month`` in expenses/views.py."""
    if raw:
        year, month = (int(part) for part in raw.split("-"))
    else:
        today = utc_today()
        year, month = today.year, today.month
    return date(year, month, 1)


async def summary(request: Request, user: CurrentUser, db: DbSession):
    try:
        month = _summary_month(request.query_params.get("month"))
    except (TypeError, ValueError):
        raise bad_request_detail("month must use YYYY-MM.") from None

    month_start, next_month_start = month_bounds(month)
    expense_scope = (
        models.Expense.user_id == user.id,
        models.Expense.date >= month_start,
        models.Expense.date < next_month_start,
    )
    income_scope = (
        models.Income.user_id == user.id,
        models.Income.date >= month_start,
        models.Income.date < next_month_start,
    )

    # Batch all aggregation queries in a single round-trip using asyncio.gather
    import asyncio

    total_expense_task = db.execute(
        select(func.coalesce(func.sum(models.Expense.amount), 0)).where(*expense_scope)
    )
    total_income_task = db.execute(
        select(func.coalesce(func.sum(models.Income.amount), 0)).where(*income_scope)
    )
    budget_rows_task = db.execute(
        select(models.Budget).where(
            models.Budget.user_id == user.id, models.Budget.month == month_start
        )
    )
    category_spent_rows_task = db.execute(
        select(
            models.Expense.category,
            func.coalesce(func.sum(models.Expense.amount), 0),
        )
        .where(*expense_scope)
        .group_by(models.Expense.category)
    )
    top_row_task = db.execute(
        select(models.Expense)
        .where(*expense_scope)
        .order_by(models.Expense.amount.desc())
        .limit(1)
    )
    payment_rows_task = db.execute(
        select(models.Expense.payment_method, func.sum(models.Expense.amount))
        .where(*expense_scope)
        .group_by(models.Expense.payment_method)
        .order_by(models.Expense.payment_method)
    )
    source_rows_task = db.execute(
        select(models.Income.source_type, func.sum(models.Income.amount))
        .where(*income_scope)
        .group_by(models.Income.source_type)
        .order_by(models.Income.source_type)
    )
    recent_rows_task = db.execute(
        select(models.Expense)
        .where(*expense_scope)
        .order_by(models.Expense.date.desc(), models.Expense.created_at.desc())
        .limit(5)
    )

    # Execute all queries concurrently
    results = await asyncio.gather(
        total_expense_task,
        total_income_task,
        budget_rows_task,
        category_spent_rows_task,
        top_row_task,
        payment_rows_task,
        source_rows_task,
        recent_rows_task,
    )

    total_expense = results[0].scalar_one()
    total_income = results[1].scalar_one()
    budget_rows = results[2].scalars().all()
    category_spent_rows = results[3].all()
    top_row = results[4].scalars().first()
    payment_rows = results[5].all()
    source_rows = results[6].all()
    recent_rows = results[7].scalars().all()

    budgets_by_category = {budget.category: budget for budget in budget_rows}
    total_budget = sum((Decimal(b.limit_amount) for b in budget_rows), Decimal("0"))

    days = calendar.monthrange(month.year, month.month)[1]
    today = utc_today()
    remaining_days = (
        max(days - today.day + 1, 1) if month == today.replace(day=1) else days
    )

    category_spent = {category: Decimal(total) for category, total in category_spent_rows}

    by_category: list[dict[str, Any]] = []
    for category in models.EXPENSE_CATEGORIES:
        spent = category_spent.get(category, Decimal("0"))
        budget = budgets_by_category.get(category)
        limit = Decimal(budget.limit_amount) if budget else Decimal("0")
        utilization_pct = (
            round(float(spent / limit * 100), 2) if limit else 0.0
        )
        share_pct = (
            round(float(spent / Decimal(total_expense) * 100), 2)
            if total_expense and spent
            else 0.0
        )
        by_category.append(
            {
                "category": category,
                "spent": decimal_float(spent),
                "budget_limit": decimal_float(limit),
                "utilization_pct": utilization_pct,
                "share_pct": share_pct,
            }
        )

    net = Decimal(total_income) - Decimal(total_expense)
    return {
        "month": month.strftime("%B %Y"),
        "total_income": decimal_float(total_income),
        "total_expense": decimal_float(total_expense),
        "net_balance": decimal_float(net),
        "total_budget_limit": decimal_float(total_budget),
        "budget_utilization_pct": (
            round(float(Decimal(total_expense) / total_budget * 100), 2)
            if total_budget
            else 0.0
        ),
        "safe_daily_spend": decimal_float(
            max(Decimal(total_budget) - Decimal(total_expense), Decimal("0")) / remaining_days
        ),
        "remaining_days": remaining_days,
        "category_breakdown": by_category,
        "payment_method_breakdown": [
            {"payment_method": key, "total": _rows_sum_to_float(value)}
            for key, value in payment_rows
        ],
        "income_source_breakdown": [
            {"source_type": key, "total": _rows_sum_to_float(value)} for key, value in source_rows
        ],
        "top_expense": (
            {
                "title": top_row.title,
                "amount": decimal_float(top_row.amount),
                "category": top_row.category,
                "date": date_str_for_json(top_row.date),
            }
            if top_row
            else None
        ),
        "recent_expenses": [
            {
                "id": row.id,
                "title": row.title,
                "amount": decimal_float(row.amount),
                "category": row.category,
                "date": date_str_for_json(row.date),
                "payment_method": row.payment_method,
            }
            for row in recent_rows
        ],
    }


def _rows_sum_to_float(value: Any) -> float | int:
    """Money values → float; Django's `or 0` turns 0/None into the int 0."""
    if value is None:
        return 0
    as_decimal = Decimal(value)
    return float(as_decimal) if as_decimal else 0


@router.get("/analytics/summary/", response_model=None)
async def analytics_summary(request: Request, user: CurrentUser, db: DbSession):
    return await summary(request, user, db)


def _months_param(request: Request, default: int) -> int:
    raw = request.query_params.get("months", default)
    try:
        return min(max(int(raw), 1), 12)
    except (TypeError, ValueError):
        return default


def _month_offsets(count: int) -> list[tuple[int, int]]:
    today = utc_today()
    pairs: list[tuple[int, int]] = [(today.year, today.month)]
    year, month = today.year, today.month
    for _ in range(count - 1):
        month -= 1
        if month <= 0:
            year, month = year - 1, month + 12
        pairs.append((year, month))
    pairs.reverse()
    return pairs


@router.get("/analytics/trends/", response_model=None)
async def analytics_trends(request: Request, user: CurrentUser, db: DbSession):
    count = _months_param(request, 6)

    # Build all month ranges first
    months = _month_offsets(count)
    month_bounds_list = []
    for year, month in months:
        month_start = date(year, month, 1)
        _, next_month_start = month_bounds(month_start)
        month_bounds_list.append((year, month, month_start, next_month_start))

    # Execute all trend row queries concurrently
    import asyncio
    trend_tasks = [
        _trend_row(db, user, year, month, month_start, next_month_start)
        for year, month, month_start, next_month_start in month_bounds_list
    ]

    try:
        rows = await asyncio.gather(*trend_tasks)
    except Exception as exc:
        import logging
        logging.getLogger("budgetbuddy.analytics").warning("Error computing analytics trends: %s", exc)
        rows = []
        for year, month in months:
            first = date(year, month, 1)
            rows.append({
                "month": first.isoformat(),
                "month_label": first.strftime("%b %Y"),
                "income": 0.0,
                "expense": 0.0,
                "net": 0.0,
                "budget": 0.0,
            })
    return rows


async def _trend_row(
    db, user: models.User, year: int, month: int, month_start: date, next_month_start: date
) -> dict[str, Any]:
    def aggregate(model, *scope):
        return db.execute(
            select(func.sum(model.amount)).where(*scope)
        )

    expense = (
        await aggregate(
            models.Expense,
            models.Expense.user_id == user.id,
            models.Expense.date >= month_start,
            models.Expense.date < next_month_start,
        )
    ).scalar_one()
    income = (
        await aggregate(
            models.Income,
            models.Income.user_id == user.id,
            models.Income.date >= month_start,
            models.Income.date < next_month_start,
        )
    ).scalar_one()
    budget = (
        await db.execute(
            select(func.sum(models.Budget.limit_amount)).where(
                models.Budget.user_id == user.id, models.Budget.month == month_start
            )
        )
    ).scalar_one()

    first = date(year, month, 1)
    income_val = Decimal(str(income)) if income is not None else Decimal("0")
    expense_val = Decimal(str(expense)) if expense is not None else Decimal("0")
    budget_val = Decimal(str(budget)) if budget is not None else Decimal("0")
    net_val = income_val - expense_val
    return {
        "month": first.isoformat(),
        "month_label": first.strftime("%b %Y"),
        "income": float(income_val),
        "expense": float(expense_val),
        "net": float(net_val),
        "budget": float(budget_val),
    }


def _or_zero_number(value: Any) -> float | int:
    if value is None:
        return 0
    as_decimal = Decimal(value)
    return float(as_decimal) if as_decimal else 0


@router.get("/analytics/category-trends/", response_model=None)
async def analytics_category_trends(request: Request, user: CurrentUser, db: DbSession):
    count = _months_param(request, 3)
    rows: list[dict[str, Any]] = []
    for year, month in _month_offsets(count):
        month_start = date(year, month, 1)
        _, next_month_start = month_bounds(month_start)
        per_category = (
            await db.execute(
                select(models.Expense.category, func.sum(models.Expense.amount))
                .where(
                    models.Expense.user_id == user.id,
                    models.Expense.date >= month_start,
                    models.Expense.date < next_month_start,
                )
                .group_by(models.Expense.category)
                .order_by(models.Expense.category)
            )
        ).all()
        for category, total in per_category:
            rows.append({"category": category, "total": _rows_sum_to_float(total)})
    return rows
