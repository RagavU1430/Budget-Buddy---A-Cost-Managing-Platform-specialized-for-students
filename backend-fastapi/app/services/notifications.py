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
from app.services.email import (
    notify_expense_created,
    notify_income_created,
    notify_goal_created,
    notify_goal_deposit,
)


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


async def record_expense_notification(
    db: AsyncSession, user: models.User, expense: models.Expense
) -> None:
    """Record in-app notification and dispatch email to user's login Gmail."""
    date_str = expense.date.strftime("%d %b %Y") if hasattr(expense.date, "strftime") else str(expense.date)
    user_name = user.first_name or user.username or "Student"
    cat_label = models.CATEGORY_LABELS.get(expense.category, expense.category.capitalize())

    # 1. In-app notification
    notification = models.Notification(
        user_id=user.id,
        notification_type="expense",
        title=f"Spent ₹{expense.amount:,.2f} on {cat_label}",
        message=f"Expense '{expense.title}' of ₹{expense.amount:,.2f} was recorded on {date_str}.",
    )
    db.add(notification)

    # 2. Asynchronous email alert to login Gmail
    if user.email:
        notify_expense_created(
            user_email=user.email,
            user_name=user_name,
            title=expense.title,
            amount=expense.amount,
            category=expense.category,
            date_str=date_str,
            payment_method=getattr(expense, "payment_method", "cash"),
        )


async def record_income_notification(
    db: AsyncSession, user: models.User, income: models.Income
) -> None:
    """Record in-app notification and dispatch email to user's login Gmail."""
    date_str = income.date.strftime("%d %b %Y") if hasattr(income.date, "strftime") else str(income.date)
    user_name = user.first_name or user.username or "Student"
    source_label = models.SOURCE_LABELS.get(income.source_type, income.source_type.replace("_", " ").title())

    # 1. In-app notification
    notification = models.Notification(
        user_id=user.id,
        notification_type="income",
        title=f"Received ₹{income.amount:,.2f} ({source_label})",
        message=f"Income '{income.title}' of ₹{income.amount:,.2f} was added on {date_str}.",
    )
    db.add(notification)

    # 2. Asynchronous email alert to login Gmail
    if user.email:
        notify_income_created(
            user_email=user.email,
            user_name=user_name,
            title=income.title,
            amount=income.amount,
            source_type=income.source_type,
            date_str=date_str,
        )


async def record_goal_created_notification(
    db: AsyncSession, user: models.User, goal: models.SavingsGoal
) -> None:
    """Record in-app notification and dispatch email when a new goal is set."""
    user_name = user.first_name or user.username or "Student"
    deadline_str = goal.target_date.strftime("%d %b %Y") if goal.target_date else None

    # 1. In-app notification
    notification = models.Notification(
        user_id=user.id,
        notification_type="goal",
        title=f"New Goal: {goal.title}",
        message=f"Target: ₹{goal.target_amount:,.2f}. Target date: {deadline_str or 'No deadline'}.",
    )
    db.add(notification)

    # 2. Email alert
    if user.email:
        notify_goal_created(
            user_email=user.email,
            user_name=user_name,
            title=goal.title,
            target_amount=goal.target_amount,
            priority=goal.priority,
            target_date_str=deadline_str,
        )


async def record_goal_deposit_notification(
    db: AsyncSession, user: models.User, goal: models.SavingsGoal, deposit_amount: Any
) -> None:
    """Record in-app notification and dispatch email when deposit is added to a goal."""
    user_name = user.first_name or user.username or "Student"

    # 1. In-app notification
    notification = models.Notification(
        user_id=user.id,
        notification_type="goal",
        title=f"Deposited ₹{float(deposit_amount):,.2f} into {goal.title}",
        message=f"Current saved: ₹{goal.current_amount:,.2f} / ₹{goal.target_amount:,.2f}.",
    )
    db.add(notification)

    # 2. Email alert
    if user.email:
        notify_goal_deposit(
            user_email=user.email,
            user_name=user_name,
            title=goal.title,
            deposit_amount=deposit_amount,
            current_amount=goal.current_amount,
            target_amount=goal.target_amount,
            is_completed=goal.is_completed,
        )

