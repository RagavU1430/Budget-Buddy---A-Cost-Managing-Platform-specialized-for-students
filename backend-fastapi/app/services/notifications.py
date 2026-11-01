"""Notification side effects — the Django signal handlers, made explicit.

Django fired these from ``post_save`` signals:

* ``apps/notifications/utils.check_budget_alerts`` on every expense write
  (called from the view *and* from the model signal, hence the ``get_or_create``
  de-duplication on ``(user, notification_type, title)``).
* ``apps/goals/signals.goal_completion_notification`` whenever a goal is saved
  and ends up completed.

Both helpers are idempotent: a second call returns the existing row and never
rewrites its message (Django's ``get_or_create`` only uses ``defaults`` on
insert).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models


def utc_today() -> date:
    """Django on the deploy host resolves ``date.today()`` in UTC (``USE_TZ``)."""
    return datetime.now(timezone.utc).date()


def month_bounds(day: date) -> tuple[date, date]:
    """First day of ``day``'s month and the first day of the next month."""
    start = date(day.year, day.month, 1)
    if day.month == 12:
        return start, date(day.year + 1, 1, 1)
    return start, date(day.year, day.month + 1, 1)


async def _get_or_create(
    db: AsyncSession,
    *,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
) -> models.Notification:
    existing = (
        await db.execute(
            select(models.Notification)
            .where(
                models.Notification.user_id == user_id,
                models.Notification.notification_type == notification_type,
                models.Notification.title == title,
            )
            .order_by(models.Notification.id)
            .limit(1)
        )
    ).scalars().first()
    if existing is not None:
        return existing

    notification = models.Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
    )
    db.add(notification)
    await db.flush()
    return notification


async def create_budget_alert(
    db: AsyncSession,
    user: models.User,
    budget: models.Budget,
    spent: Decimal | int | float,
) -> models.Notification | None:
    """Port of ``notifications.utils.create_budget_alert`` (80% / 100% steps)."""
    if not budget.limit_amount:
        return None

    ratio = Decimal(spent) / Decimal(budget.limit_amount)
    if ratio < Decimal("0.8"):
        return None

    threshold = "100%" if ratio >= 1 else "80%"
    return await _get_or_create(
        db,
        user_id=user.id,
        notification_type="budget",
        title=f"Budget alert: {budget.category}",
        message=(
            f"You have used {threshold} of your {budget.category} budget for "
            f"{budget.month:%B %Y}."
        ),
    )


async def budget_alert_for_expense(
    db: AsyncSession, user: models.User, expense: models.Expense
) -> models.Notification | None:
    """Port of ``expenses.signals.budget_alert_hook``.

    The signal looked up the budget for the *expense's* month (not necessarily
    the current month) and re-summed that month's spend for the category.
    """
    month_start, next_month_start = month_bounds(expense.date)
    budget = (
        await db.execute(
            select(models.Budget)
            .where(
                models.Budget.user_id == user.id,
                models.Budget.month == month_start,
                models.Budget.category == expense.category,
            )
            .order_by(models.Budget.id)
            .limit(1)
        )
    ).scalars().first()
    if budget is None:
        return None

    spent = (
        await db.execute(
            select(func.coalesce(func.sum(models.Expense.amount), 0)).where(
                models.Expense.user_id == user.id,
                models.Expense.category == expense.category,
                models.Expense.date >= month_start,
                models.Expense.date < next_month_start,
            )
        )
    ).scalar_one()
    return await create_budget_alert(db, user, budget, spent)


async def check_budget_alerts(db: AsyncSession, user: models.User) -> None:
    """Re-evaluate every budget of the current month after an expense write."""
    today = utc_today()
    month_start, next_month_start = month_bounds(today)

    budgets = (
        await db.execute(
            select(models.Budget).where(
                models.Budget.user_id == user.id,
                models.Budget.month == month_start,
            )
        )
    ).scalars().all()

    for budget in budgets:
        spent = (
            await db.execute(
                select(func.coalesce(func.sum(models.Expense.amount), 0)).where(
                    models.Expense.user_id == user.id,
                    models.Expense.category == budget.category,
                    models.Expense.date >= month_start,
                    models.Expense.date < next_month_start,
                )
            )
        ).scalar_one()
        await create_budget_alert(db, user, budget, spent)


async def create_goal_completed_notification(
    db: AsyncSession, goal: models.SavingsGoal
) -> models.Notification | None:
    """Port of ``goals.signals.goal_completion_notification``."""
    if not goal.is_completed:
        return None
    return await _get_or_create(
        db,
        user_id=goal.user_id,
        notification_type="goal",
        title=f"Goal completed: {goal.title}",
        message=f"You reached your savings goal of {goal.target_amount}.",
    )
