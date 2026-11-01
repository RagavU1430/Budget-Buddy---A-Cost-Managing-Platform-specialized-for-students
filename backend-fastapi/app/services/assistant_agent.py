"""BudgetBuddy AI reasoning agent — async port of ``apps/assistant/agent.py``.

Every reply string, trigger list and regex is preserved verbatim, including the
quirks that the frontend depends on (``matched_cat.capitalize()`` vs the display
label, the hard-coded ``₹`` sign, ``31 - remaining_days`` in one fallback).

The Django version kept the pending multi-turn action inside
``Profile.financial_preferences["pending_assistant_action"]``; that is preserved,
but because SQLAlchemy does not track in-place JSON mutation, the whole dict is
re-assigned before flushing.
"""

from __future__ import annotations

import calendar
import json
import re
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import models
from app.services.assistant_guardrails import sanitize_output
from app.services.notifications import (
    budget_alert_for_expense,
    check_budget_alerts,
    utc_today,
)

EXPENSE_CATEGORY_OPTIONS = [
    "🍔 Food & Dining",
    "🚌 Travel & Commute",
    "🛍️ Shopping",
    "📚 Education & Books",
    "🎬 Entertainment",
    "📦 Miscellaneous",
]

INCOME_SOURCE_OPTIONS = [
    "💵 Pocket Money / Allowance",
    "💼 Part-time Job / Salary",
    "💻 Freelance",
    "🎓 Scholarship",
    "🎁 Gift",
    "💰 Other",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "food": ["food", "lunch", "dinner", "breakfast", "canteen", "cafe", "snack", "coffee", "tea", "swiggy", "zomato", "groceries", "mess", "dining", "eat"],
    "travel": ["travel", "bus", "metro", "auto", "train", "flight", "cab", "uber", "ola", "petrol", "fuel", "ticket", "commute", "transport"],
    "shopping": ["shopping", "clothes", "shoes", "amazon", "flipkart", "dress", "gadget", "watch", "bought"],
    "education": ["education", "book", "books", "course", "stationery", "exam", "college", "fees", "tuition", "xerox", "print", "study"],
    "entertainment": ["entertainment", "movie", "cinema", "game", "netflix", "party", "outing", "concert", "hotstar"],
    "misc": ["misc", "recharge", "mobile", "wifi", "bill", "laundry", "medical", "medicine", "other"],
}

INCOME_SOURCE_KEYWORDS: dict[str, list[str]] = {
    "pocket_money": ["pocket money", "allowance", "parents", "home", "family", "mom", "dad"],
    "scholarship": ["scholarship", "grant", "fellowship", "stipend grant"],
    "freelance": ["freelance", "project", "gig", "client", "contract", "freelancing"],
    "part_time": ["part-time", "job", "salary", "internship", "stipend", "part time"],
    "gift": ["gift", "birthday", "celebration", "present"],
}

ASSISTANT_NOTE = "Logged via BudgetBuddy AI Assistant"


# ---------------------------------------------------------------------------
# Pending multi-turn actions
# ---------------------------------------------------------------------------
async def get_pending_action(db: AsyncSession, user: models.User) -> dict[str, Any] | None:
    """Retrieve any active multi-turn pending action for the user."""
    profile = user.profile
    if profile is not None and isinstance(profile.financial_preferences, dict):
        pending = profile.financial_preferences.get("pending_assistant_action")
        if pending:
            return pending

    last_bot_message = (
        await db.execute(
            select(models.ChatMessage)
            .where(
                models.ChatMessage.user_id == user.id,
                models.ChatMessage.role == "assistant",
            )
            .order_by(models.ChatMessage.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if last_bot_message is not None and last_bot_message.action_type == "pending_category_clarification":
        return last_bot_message.action_data
    return None


async def set_pending_action(
    db: AsyncSession, user: models.User, data: dict[str, Any]
) -> None:
    """Store a pending multi-turn action in the user's preferences."""
    profile = user.profile
    if profile is None:
        return
    preferences = (
        dict(profile.financial_preferences)
        if isinstance(profile.financial_preferences, dict)
        else {}
    )
    preferences["pending_assistant_action"] = data
    profile.financial_preferences = preferences
    await db.flush()


async def clear_pending_action(db: AsyncSession, user: models.User) -> None:
    """Remove any pending multi-turn action."""
    profile = user.profile
    if profile is None:
        return
    if not isinstance(profile.financial_preferences, dict):
        return
    if "pending_assistant_action" not in profile.financial_preferences:
        return
    preferences = dict(profile.financial_preferences)
    del preferences["pending_assistant_action"]
    profile.financial_preferences = preferences
    await db.flush()


def strip_markdown_stars(text: str) -> str:
    """Remove ``**bold**`` markers so the drawer renders plain text."""
    cleaned = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
    cleaned = cleaned.replace("**", "")
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Financial context
# ---------------------------------------------------------------------------
async def build_user_finance_context(
    db: AsyncSession, user: models.User
) -> dict[str, Any]:
    """Compile the financial snapshot used by the prompt and the fallbacks."""
    now = utc_today()
    month_start = date(now.year, now.month, 1)

    if now.month == 12:
        next_month_start = date(now.year + 1, 1, 1)
        days_in_month = 31
    else:
        next_month_start = date(now.year, now.month + 1, 1)
        days_in_month = (next_month_start - month_start).days

    remaining_days = max(1, days_in_month - now.day + 1)

    profile = user.profile
    monthly_income_cap = (
        float(profile.monthly_income) if profile is not None and profile.monthly_income else 0.0
    )
    currency = profile.currency if profile is not None and profile.currency else "INR"
    curr_sym = "₹" if currency == "INR" else f"{currency} "

    month_expense_filter = (
        models.Expense.user_id == user.id,
        models.Expense.date >= month_start,
        models.Expense.date < next_month_start,
    )

    total_expense_raw = (
        await db.execute(
            select(func.coalesce(func.sum(models.Expense.amount), 0)).where(*month_expense_filter)
        )
    ).scalar_one()
    total_expense = float(total_expense_raw or 0.0)

    # Django looped over every choice; one grouped query is equivalent and keeps
    # the dict in ``Expense.Category.values`` order with zero-filled categories.
    category_rows = (
        await db.execute(
            select(models.Expense.category, func.sum(models.Expense.amount))
            .where(*month_expense_filter)
            .group_by(models.Expense.category)
        )
    ).all()
    grouped = {row[0]: float(row[1] or 0.0) for row in category_rows}
    category_spent: dict[str, float] = {
        choice: grouped.get(choice, 0.0) for choice in models.EXPENSE_CATEGORIES
    }

    total_income_raw = (
        await db.execute(
            select(func.coalesce(func.sum(models.Income.amount), 0)).where(
                models.Income.user_id == user.id,
                models.Income.date >= month_start,
                models.Income.date < next_month_start,
            )
        )
    ).scalar_one()
    total_income = float(total_income_raw or 0.0)

    active_budgets = (
        await db.execute(
            select(models.Budget)
            .where(models.Budget.user_id == user.id, models.Budget.month == month_start)
            .order_by(models.Budget.category)
        )
    ).scalars().all()

    total_budget_limit = float(
        sum((Decimal(budget.limit_amount) for budget in active_budgets), Decimal("0"))
    )

    budgets_detail = []
    overbudget_categories = []
    for budget in active_budgets:
        spent = category_spent.get(budget.category, 0.0)
        limit = float(budget.limit_amount)
        utilization = (spent / limit * 100) if limit > 0 else 0
        remaining = limit - spent
        if remaining < 0:
            overbudget_categories.append(budget.category)
        budgets_detail.append(
            {
                "category": budget.category,
                "limit": limit,
                "spent": spent,
                "remaining": remaining,
                "utilization": round(utilization, 1),
            }
        )

    net_balance = total_income - total_expense
    remaining_budget = total_budget_limit - total_expense
    safe_daily_spend = (
        max(0.0, remaining_budget / remaining_days) if total_budget_limit > 0 else 0.0
    )

    sorted_categories = sorted(category_spent.items(), key=lambda item: item[1], reverse=True)
    top_category = (
        sorted_categories[0]
        if sorted_categories and sorted_categories[0][1] > 0
        else None
    )

    recent_rows = (
        await db.execute(
            select(models.Expense)
            .where(models.Expense.user_id == user.id)
            .order_by(models.Expense.date.desc(), models.Expense.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    recent = [
        {
            "title": expense.title,
            "amount": expense.amount,
            "category": expense.category,
            "date": expense.date,
        }
        for expense in recent_rows
    ]

    return {
        "user_name": user.first_name or user.username,
        "role": user.role,
        "currency": currency,
        "curr_sym": curr_sym,
        "monthly_income_cap": monthly_income_cap,
        "current_month": now.strftime("%B %Y"),
        "today_str": now.strftime("%d %b %Y"),
        "remaining_days": remaining_days,
        "total_expense": total_expense,
        "total_income": total_income,
        "net_balance": net_balance,
        "total_budget_limit": total_budget_limit,
        "remaining_budget": remaining_budget,
        "safe_daily_spend": round(safe_daily_spend, 2),
        "category_spent": category_spent,
        "budgets_detail": budgets_detail,
        "overbudget_categories": overbudget_categories,
        "top_category": top_category,
        "recent_expenses": recent,
    }


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION_TEMPLATE = (
    "You are BudgetBuddy AI, a friendly, intelligent personal finance assistant specialized for college students.\n"
    "You have direct access to the student's real financial data for the current month.\n\n"
    "STRICT SECURITY & PRIVACY GUARDRAILS:\n"
    "1. Never disclose passwords, password hashes, JWT tokens, session IDs, internal database IDs, or secrets.\n"
    "2. If the user asks for credentials or session keys, politely decline stating that security guardrails protect them.\n"
    "3. Only answer questions related to the student's budget, income, expenses, savings strategies, and website features.\n\n"
    "MANDATORY FORMATTING INSTRUCTION:\n"
    "- NEVER use double asterisks (**) or single asterisks for bolding. The user hates double asterisks.\n"
    "- Format your answer with clean line breaks, emojis for section titles, and clean bullet points using '•' or dashes.\n"
    "- Keep responses concise, clear, and easy to read on mobile and desktop.\n\n"
    "USER LIVE DATA CONTEXT:\n"
)


def _system_instruction(context: dict[str, Any]) -> str:
    overbudget = (
        ", ".join(context["overbudget_categories"])
        if context["overbudget_categories"]
        else "None"
    )
    return (
        SYSTEM_INSTRUCTION_TEMPLATE
        + f"• Student Name: {context['user_name']}\n"
        + f"• Current Month: {context['current_month']}\n"
        + f"• Currency: {context['curr_sym']}\n"
        + f"• Monthly Income / Allowance: {context['curr_sym']}{context['monthly_income_cap']:,.2f}\n"
        + f"• Total Income Recorded this month: {context['curr_sym']}{context['total_income']:,.2f}\n"
        + f"• Total Expenses this month: {context['curr_sym']}{context['total_expense']:,.2f}\n"
        + f"• Net Balance (Income - Expense): {context['curr_sym']}{context['net_balance']:,.2f}\n"
        + f"• Total Budget Limit Set: {context['curr_sym']}{context['total_budget_limit']:,.2f}\n"
        + f"• Remaining Budget: {context['curr_sym']}{context['remaining_budget']:,.2f}\n"
        + f"• Safe Daily Spending for remaining {context['remaining_days']} days: "
        + f"{context['curr_sym']}{context['safe_daily_spend']:,.2f} per day\n"
        + f"• Category Spending: {json.dumps(context['category_spent'])}\n"
        + f"• Active Budgets: {json.dumps(context['budgets_detail'])}\n"
        + f"• Overbudget Categories: {overbudget}\n"
    )


async def call_gemini_api(
    user: models.User, query: str, context: dict[str, Any]
) -> str | None:
    """Query Gemini with the user's grounded data; ``None`` means "unavailable"."""
    key = settings.GEMINI_API_KEY
    if not key:
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _system_instruction(context)},
                    {
                        "text": (
                            f"User question: {query}\n\nRemember: Do not use ** for bolding. "
                            "Reply cleanly with bullet points and emojis."
                        )
                    },
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
        for model in settings.gemini_models:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"{model}:generateContent?key={key}"
            )
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                res_data = response.json()
                candidates = res_data.get("candidates", [])
                if (
                    candidates
                    and "content" in candidates[0]
                    and "parts" in candidates[0]["content"]
                ):
                    text = candidates[0]["content"]["parts"][0].get("text", "")
                    if text:
                        return strip_markdown_stars(text)
            except Exception:
                continue

    return None


# ---------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------
_AMOUNT_RE = r"(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)"


def _extract_amount(text: str) -> Decimal | None:
    match = re.search(_AMOUNT_RE, text)
    if not match:
        return None
    return Decimal(match.group(1).replace(",", ""))


def _match_category(text: str) -> str | None:
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return None


def _match_income_source(text: str) -> str | None:
    for source, keywords in INCOME_SOURCE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return source
    return None


async def _create_expense(
    db: AsyncSession,
    user: models.User,
    *,
    title: str,
    amount: Decimal,
    category: str,
    day: date,
) -> models.Expense:
    expense = models.Expense(
        user_id=user.id,
        title=title[:100],
        amount=amount,
        category=category,
        date=day,
        payment_method="upi",
        notes=ASSISTANT_NOTE,
    )
    db.add(expense)
    await db.flush()
    await budget_alert_for_expense(db, user, expense)
    await check_budget_alerts(db, user)
    return expense


async def _create_income(
    db: AsyncSession,
    user: models.User,
    *,
    title: str,
    amount: Decimal,
    source_type: str,
    day: date,
) -> models.Income:
    income = models.Income(
        user_id=user.id,
        title=title[:120],
        amount=amount,
        source_type=source_type,
        date=day,
        notes=ASSISTANT_NOTE,
    )
    db.add(income)
    await db.flush()
    return income


def _expense_reply(expense: models.Expense) -> str:
    return (
        "✅ Expense Logged Successfully!\n\n"
        f"• Title: {expense.title}\n"
        f"• Amount: ₹{expense.amount:,.2f}\n"
        f"• Category: {models.CATEGORY_LABELS[expense.category]}\n"
        f"• Date: {expense.date.strftime('%d %b %Y')}\n\n"
        "Your monthly totals and budget gauges have been updated automatically."
    )


def _income_reply(income: models.Income) -> str:
    return (
        "💰 Income Recorded!\n\n"
        f"• Source: {models.SOURCE_LABELS[income.source_type]}\n"
        f"• Amount: ₹{income.amount:,.2f}\n"
        f"• Date: {income.date.strftime('%d %b %Y')}\n\n"
        "Your net balance has been updated."
    )


# ---------------------------------------------------------------------------
# Pending-action resolution
# ---------------------------------------------------------------------------
async def handle_pending_action(
    db: AsyncSession,
    user: models.User,
    query: str,
    pending: dict[str, Any],
) -> tuple[str, str, dict[str, Any]] | None:
    """Resolve a pending multi-turn clarification (category or income source)."""
    q = query.strip()
    q_lower = q.lower()
    cleaned_q = re.sub(r"[^\w\s]", " ", q_lower)

    if any(
        q_lower.startswith(word)
        for word in [
            "cancel",
            "stop",
            "nevermind",
            "forget it",
            "no thanks",
            "abort",
            "exit",
        ]
    ):
        await clear_pending_action(db, user)
        return (
            "pending_cancelled",
            "❌ Action Cancelled. I did not log that transaction. How else can I help you?",
            {},
        )

    if any(
        q_lower.startswith(word)
        for word in [
            "how",
            "what",
            "can you",
            "is there",
            "show",
            "check",
            "set budget",
            "set a budget",
        ]
    ) or "?" in q:
        await clear_pending_action(db, user)
        return None

    curr_date = utc_today()
    flow = pending.get("flow")

    if flow == "expense":
        matched_cat = _match_category(cleaned_q)

        if not matched_cat:
            if "food" in cleaned_q or "dining" in cleaned_q:
                matched_cat = "food"
            elif "travel" in cleaned_q or "commute" in cleaned_q:
                matched_cat = "travel"
            elif "shopping" in cleaned_q:
                matched_cat = "shopping"
            elif "education" in cleaned_q or "book" in cleaned_q or "study" in cleaned_q:
                matched_cat = "education"
            elif "entertainment" in cleaned_q or "movie" in cleaned_q:
                matched_cat = "entertainment"
            elif "misc" in cleaned_q or "other" in cleaned_q:
                matched_cat = "misc"

        amount: Decimal | None
        if pending.get("amount"):
            amount = Decimal(str(pending["amount"]))
        else:
            amount = _extract_amount(q_lower)

        if not matched_cat and not amount:
            return None

        if matched_cat and not amount:
            pending["category"] = matched_cat
            await set_pending_action(db, user, pending)
            return (
                "pending_category_clarification",
                f"Got it, {matched_cat.capitalize()}! How much was spent? (e.g. '150')",
                {"flow": "expense", "amount": None, "category": matched_cat},
            )

        if not matched_cat and amount:
            pending["amount"] = str(amount)
            await set_pending_action(db, user, pending)
            return (
                "pending_category_clarification",
                f"Under what category does this spend of ₹{amount:,.2f} come?\n\n"
                "• 🍔 Food & Dining\n• 🚌 Travel & Commute\n• 🛍️ Shopping\n"
                "• 📚 Education & Books\n• 🎬 Entertainment\n• 📦 Miscellaneous",
                {"flow": "expense", "amount": str(amount), "options": EXPENSE_CATEGORY_OPTIONS},
            )

        if not matched_cat:
            matched_cat = "misc"

        title = pending.get("title") or f"{matched_cat.capitalize()} Expense"
        if title in ["Spend", "Expense"]:
            title = f"{matched_cat.capitalize()} Expense"

        expense = await _create_expense(
            db, user, title=title, amount=amount, category=matched_cat, day=curr_date
        )
        await clear_pending_action(db, user)
        return (
            "expense_created",
            _expense_reply(expense),
            {"id": expense.id, "amount": str(expense.amount), "category": expense.category},
        )

    if flow == "income":
        matched_source = _match_income_source(cleaned_q)

        if not matched_source:
            if "pocket" in cleaned_q or "allowance" in cleaned_q:
                matched_source = "pocket_money"
            elif (
                "part" in cleaned_q
                or "job" in cleaned_q
                or "salary" in cleaned_q
                or "stipend" in cleaned_q
            ):
                matched_source = "part_time"
            elif "freelance" in cleaned_q or "gig" in cleaned_q:
                matched_source = "freelance"
            elif "scholarship" in cleaned_q or "grant" in cleaned_q:
                matched_source = "scholarship"
            elif "gift" in cleaned_q or "birthday" in cleaned_q:
                matched_source = "gift"
            elif "other" in cleaned_q:
                matched_source = "other"

        amount = None
        if pending.get("amount"):
            amount = Decimal(str(pending["amount"]))
        else:
            amount = _extract_amount(q_lower)

        if not matched_source and not amount:
            return None

        if matched_source and not amount:
            pending["source_type"] = matched_source
            await set_pending_action(db, user, pending)
            return (
                "pending_category_clarification",
                f"Great! How much {matched_source.replace('_', ' ').capitalize()} income did you receive?",
                {"flow": "income", "amount": None, "source_type": matched_source},
            )

        if not matched_source and amount:
            pending["amount"] = str(amount)
            await set_pending_action(db, user, pending)
            return (
                "pending_category_clarification",
                f"Awesome! Under what category or source does this new money of ₹{amount:,.2f} come?\n\n"
                "• 💵 Pocket Money / Allowance\n• 💼 Part-time Job / Salary\n• 💻 Freelance\n"
                "• 🎓 Scholarship\n• 🎁 Gift\n• 💰 Other",
                {"flow": "income", "amount": str(amount), "options": INCOME_SOURCE_OPTIONS},
            )

        if not matched_source:
            matched_source = "other"

        title = pending.get("title") or f"{matched_source.replace('_', ' ').capitalize()}"
        if title in ["Income", "New Money"]:
            title = f"{matched_source.replace('_', ' ').capitalize()}"

        income = await _create_income(
            db, user, title=title, amount=amount, source_type=matched_source, day=curr_date
        )
        await clear_pending_action(db, user)
        return (
            "income_created",
            _income_reply(income),
            {
                "id": income.id,
                "amount": str(income.amount),
                "source_type": income.source_type,
            },
        )

    return None


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------
async def try_action_dispatch(
    db: AsyncSession, user: models.User, query: str
) -> tuple[str, str, dict[str, Any]] | None:
    """Parse actionable commands (log expense, set budget, record income)."""
    q = query.strip()
    q_lower = q.lower()
    curr_date = utc_today()
    month_first = date(curr_date.year, curr_date.month, 1)

    # 1. Action: log an expense
    expense_triggers = [
        "log expense",
        "add expense",
        "spent",
        "paid",
        "bought",
        "spend",
        "purchase",
        "cost",
    ]
    is_expense_action = any(trigger in q_lower for trigger in expense_triggers)

    if is_expense_action and not (
        "how much" in q_lower
        or "what did i" in q_lower
        or "budget" in q_lower
        and "set" in q_lower
        or "?" in q_lower
    ):
        amount = _extract_amount(q_lower)
        matched_cat = _match_category(q_lower)

        if matched_cat and amount:
            title = q
            for prefix in ["log expense", "add expense", "spent", "paid"]:
                if q_lower.startswith(prefix):
                    title = q[len(prefix):].strip()
                    break
            title = re.sub(
                r"^(of|for|on|rs\.?|₹|\d+(\.\d{1,2})?|\s)+", "", title, flags=re.IGNORECASE
            ).strip()
            if not title:
                title = f"{matched_cat.capitalize()} Expense"

            expense = await _create_expense(
                db, user, title=title, amount=amount, category=matched_cat, day=curr_date
            )
            await clear_pending_action(db, user)
            return (
                "expense_created",
                _expense_reply(expense),
                {"id": expense.id, "amount": str(expense.amount), "category": expense.category},
            )

        if amount:
            await set_pending_action(
                db,
                user,
                {
                    "flow": "expense",
                    "amount": str(amount),
                    "title": "Expense",
                    "options": EXPENSE_CATEGORY_OPTIONS,
                },
            )
            res = (
                f"Got it! Under what category does this spend of ₹{amount:,.2f} come?\n\n"
                "Please choose one of the categories below:\n"
                "• 🍔 Food & Dining (canteen, mess, groceries)\n"
                "• 🚌 Travel & Commute (bus, metro, cab, fuel)\n"
                "• 🛍️ Shopping (clothes, gadgets, essentials)\n"
                "• 📚 Education & Books (notes, courses, stationery)\n"
                "• 🎬 Entertainment (movies, games, outings)\n"
                "• 📦 Miscellaneous (recharge, bills, other)"
            )
            return (
                "pending_category_clarification",
                res,
                {
                    "flow": "expense",
                    "amount": str(amount),
                    "options": EXPENSE_CATEGORY_OPTIONS,
                },
            )

        await set_pending_action(
            db,
            user,
            {
                "flow": "expense",
                "amount": None,
                "title": "Expense",
                "options": EXPENSE_CATEGORY_OPTIONS,
            },
        )
        res = (
            "Sure! How much did you spend, and under what category does this spend come?\n\n"
            "• 🍔 Food & Dining\n"
            "• 🚌 Travel & Commute\n"
            "• 🛍️ Shopping\n"
            "• 📚 Education & Books\n"
            "• 🎬 Entertainment\n"
            "• 📦 Miscellaneous"
        )
        return (
            "pending_category_clarification",
            res,
            {
                "flow": "expense",
                "amount": None,
                "options": EXPENSE_CATEGORY_OPTIONS,
            },
        )

    # 2. Action: set a budget limit
    is_budget_question = (
        any(
            q_lower.startswith(word)
            for word in [
                "how",
                "what",
                "is there",
                "is it",
                "can i",
                "can you",
                "show",
                "check",
                "do i",
                "should i",
                "am i",
            ]
        )
        or "?" in q_lower
        or "how much" in q_lower
        or "what is" in q_lower
        or "what's" in q_lower
        or "how is" in q_lower
        or "can i afford" in q_lower
    )

    is_budget_action = not is_budget_question and (
        bool(re.search(r"\b(set|create|allocate|update|change|make|put|add|fix)\b.*?\b(budget|limit)\b", q_lower))
        or bool(re.search(r"\b(budget|limit)\b.*?\b(of|to|is|=|for|as|at|should be)\b", q_lower))
        or bool(re.search(r"\b(daily|monthly)\s+(budget|limit)\b", q_lower))
        or bool(re.search(r"\b(budget|limit)\s*[:=]?\s*(?:₹|rs\.?|inr)?\s*\d+", q_lower))
    )

    if is_budget_action:
        amount_match = (
            re.search(r"(?:₹|rs\.?|inr)\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)", q_lower)
            or re.search(
                r"(?:of|to|is|=|limit|budget)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)",
                q_lower,
            )
            or re.search(
                r"(\d+(?:,\d+)*(?:\.\d{1,2})?)\s*(?:per day|daily|/day|per month|monthly|/month|rupees|rs)",
                q_lower,
            )
            or re.search(r"\b(\d+(?:,\d+)*(?:\.\d{1,2})?)\b", q_lower)
        )
        if amount_match:
            raw_amount = Decimal(amount_match.group(1).replace(",", ""))
            is_daily = any(
                term in q_lower
                for term in [
                    "per day",
                    "daily",
                    "a day",
                    "each day",
                    "/day",
                    "/ day",
                    "perday",
                ]
            )

            days_in_month = calendar.monthrange(curr_date.year, curr_date.month)[1]

            if is_daily:
                daily_limit = raw_amount
                monthly_limit = raw_amount * Decimal(days_in_month)
            else:
                monthly_limit = raw_amount
                daily_limit = round(raw_amount / Decimal(days_in_month), 2)

            matched_cat = "misc"
            for category, keywords in CATEGORY_KEYWORDS.items():
                if any(keyword in q_lower for keyword in keywords):
                    matched_cat = category
                    break

            budget = (
                await db.execute(
                    select(models.Budget).where(
                        models.Budget.user_id == user.id,
                        models.Budget.month == month_first,
                        models.Budget.category == matched_cat,
                    )
                )
            ).scalars().first()

            created = budget is None
            if budget is None:
                budget = models.Budget(
                    user_id=user.id,
                    month=month_first,
                    category=matched_cat,
                    limit_amount=monthly_limit,
                )
                db.add(budget)
            else:
                budget.limit_amount = monthly_limit
            await db.flush()

            profile = user.profile
            if profile is not None:
                preferences = (
                    dict(profile.financial_preferences)
                    if isinstance(profile.financial_preferences, dict)
                    else {}
                )
                preferences["daily_budget_limit"] = float(daily_limit)
                preferences["monthly_budget_target"] = float(monthly_limit)
                profile.financial_preferences = preferences
                if not profile.monthly_income or profile.monthly_income == Decimal("0"):
                    profile.monthly_income = monthly_limit
                await db.flush()

            verb = "created" if created else "updated"
            daily_info = (
                f"\n• Daily Rate: ₹{daily_limit:,.2f} / day "
                f"({days_in_month} days in {month_first.strftime('%B')})"
                if is_daily
                else ""
            )
            res = (
                f"🎯 Monthly Budget {verb.capitalize()} Successfully!\n\n"
                f"• Category: {models.CATEGORY_LABELS[budget.category]}\n"
                f"• Monthly Spending Limit: ₹{budget.limit_amount:,.2f}{daily_info}\n"
                f"• Active Month: {month_first.strftime('%B %Y')}\n\n"
                "✅ Updated your live dashboard budget gauge and runway."
            )
            return (
                "budget_created",
                res,
                {
                    "category": budget.category,
                    "limit": str(budget.limit_amount),
                    "daily_limit": str(daily_limit),
                    "is_daily": is_daily,
                },
            )

    # 3. Action: record income / new money
    income_triggers = [
        "income",
        "received",
        "got money",
        "new money",
        "add money",
        "add income",
        "record income",
        "got cash",
        "cash received",
    ]
    is_income_action = any(t in q_lower for t in income_triggers) or (
        ("got" in q_lower or "received" in q_lower)
        and any(
            k in q_lower
            for k in ["money", "cash", "stipend", "allowance", "rupees", "rs", "₹", "inr"]
        )
    )

    if is_income_action and not (
        "how much" in q_lower or "what did i" in q_lower or "?" in q_lower
    ):
        amount = _extract_amount(q_lower)
        matched_source = _match_income_source(q_lower)

        if matched_source and amount:
            income = await _create_income(
                db,
                user,
                title=f"{matched_source.replace('_', ' ').capitalize()}",
                amount=amount,
                source_type=matched_source,
                day=curr_date,
            )
            await clear_pending_action(db, user)
            return (
                "income_created",
                _income_reply(income),
                {
                    "id": income.id,
                    "amount": str(income.amount),
                    "source_type": income.source_type,
                },
            )

        if amount:
            await set_pending_action(
                db,
                user,
                {
                    "flow": "income",
                    "amount": str(amount),
                    "title": "Income",
                    "options": INCOME_SOURCE_OPTIONS,
                },
            )
            res = (
                f"Awesome! Under what category or source does this new money of ₹{amount:,.2f} come?\n\n"
                "Please choose one of the options below:\n"
                "• 💵 Pocket Money / Allowance (from parents or family)\n"
                "• 💼 Part-time Job / Salary / Stipend\n"
                "• 💻 Freelance / Project Gigs\n"
                "• 🎓 Scholarship / Grant\n"
                "• 🎁 Gift (birthday, celebration)\n"
                "• 💰 Other Sources"
            )
            return (
                "pending_category_clarification",
                res,
                {
                    "flow": "income",
                    "amount": str(amount),
                    "options": INCOME_SOURCE_OPTIONS,
                },
            )

        await set_pending_action(
            db,
            user,
            {
                "flow": "income",
                "amount": None,
                "title": "Income",
                "options": INCOME_SOURCE_OPTIONS,
            },
        )
        res = (
            "Great! How much new money or income did you receive, and under what category or source does it come?\n\n"
            "• 💵 Pocket Money / Allowance\n"
            "• 💼 Part-time Job / Salary\n"
            "• 💻 Freelance\n"
            "• 🎓 Scholarship\n"
            "• 🎁 Gift\n"
            "• 💰 Other Sources"
        )
        return (
            "pending_category_clarification",
            res,
            {
                "flow": "income",
                "amount": None,
                "options": INCOME_SOURCE_OPTIONS,
            },
        )

    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def generate_assistant_response(
    db: AsyncSession, user: models.User, query: str
) -> tuple[str, str, dict[str, Any]]:
    """Generate a reply, with clean formatting and output sanitisation."""
    pending = await get_pending_action(db, user)
    if pending:
        handled = await handle_pending_action(db, user, query, pending)
        if handled:
            action_type, response, data = handled
            return (sanitize_output(strip_markdown_stars(response)), action_type, data)

    context = await build_user_finance_context(db, user)
    sym = context["curr_sym"]

    action = await try_action_dispatch(db, user, query)
    if action:
        action_type, response, data = action
        return (sanitize_output(strip_markdown_stars(response)), action_type, data)

    gemini_reply = await call_gemini_api(user, query, context)
    if gemini_reply:
        cleaned_reply = strip_markdown_stars(gemini_reply)
        return (sanitize_output(cleaned_reply), "gemini_response", {})

    # Deterministic fallback when Gemini is unavailable.
    q = query.strip().lower()

    if any(k in q for k in ["safe", "daily", "per day", "burn rate", "how much can i spend"]):
        if context["total_budget_limit"] > 0:
            response = (
                f"📊 Daily Spending Recommendation for {context['current_month']}:\n\n"
                f"• Remaining Total Budget: {sym}{context['remaining_budget']:,.2f}\n"
                f"• Remaining Days in Month: {context['remaining_days']} days\n"
                f"• Safe Daily Allowance: {sym}{context['safe_daily_spend']:,.2f} / day\n\n"
                f"💡 Student Pro-Tip: Staying below {sym}{context['safe_daily_spend']:,.2f} per day "
                f"ensures you finish {context['current_month']} within your budget."
            )
        else:
            response = (
                f"You haven't set any monthly budget limits yet for {context['current_month']}.\n\n"
                f"• Total spent so far: {sym}{context['total_expense']:,.2f} over "
                f"{31 - context['remaining_days']} days.\n\n"
                "You can set a limit by typing: 'Set budget 4000 for food' or on the Budgets page."
            )
        return (sanitize_output(strip_markdown_stars(response)), "query_daily_safe", {})

    if any(
        k in q
        for k in [
            "total spend",
            "how much have i spent",
            "my expenses",
            "spending summary",
            "spent this month",
        ]
    ):
        top_text = (
            f"Your highest expenditure is on {context['top_category'][0].capitalize()} "
            f"({sym}{context['top_category'][1]:,.2f})."
            if context["top_category"]
            else "No expenses recorded this month."
        )
        response = (
            f"📈 Your Spending Snapshot for {context['current_month']}:\n\n"
            f"• Total Spent: {sym}{context['total_expense']:,.2f}\n"
            f"• Total Income Recorded: {sym}{context['total_income']:,.2f}\n"
            f"• Net Balance: {sym}{context['net_balance']:,.2f}\n\n"
            f"{top_text}"
        )
        return (sanitize_output(strip_markdown_stars(response)), "query_expenses", {})

    response = (
        f"Hello {context['user_name']}! Here is your quick budget overview for "
        f"{context['current_month']}:\n\n"
        f"• Total Spent: {sym}{context['total_expense']:,.2f}\n"
        f"• Remaining Budget: {sym}{context['remaining_budget']:,.2f}\n"
        f"• Safe Daily Rate: {sym}{context['safe_daily_spend']:,.2f} / day\n\n"
        "You can ask me questions about your spending, daily allowances, or type "
        "'Spent 150 on food' to log a transaction."
    )
    return (sanitize_output(strip_markdown_stars(response)), "fallback", {})


__all__ = [
    "build_user_finance_context",
    "call_gemini_api",
    "clear_pending_action",
    "generate_assistant_response",
    "get_pending_action",
    "set_pending_action",
    "strip_markdown_stars",
    "try_action_dispatch",
]
