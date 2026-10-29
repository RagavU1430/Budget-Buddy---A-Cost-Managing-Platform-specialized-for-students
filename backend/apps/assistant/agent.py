"""BudgetBuddy AI Reasoning Agent with Google Gemini Integration.

Aggregates authenticated user financial context, calls Gemini API to answer queries
with live context, executes automated expense/budget actions, and produces clean formatting
without double asterisks (**).
"""

import json
import os
import re
import urllib.request
import urllib.error
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from django.db.models import Sum
from django.utils import timezone

from apps.budgets.models import Budget
from apps.expenses.models import Expense, Income
from .guardrails import sanitize_output

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

CATEGORY_KEYWORDS = {
    Expense.Category.FOOD: ["food", "lunch", "dinner", "breakfast", "canteen", "cafe", "snack", "coffee", "tea", "swiggy", "zomato", "groceries", "mess"],
    Expense.Category.TRAVEL: ["travel", "bus", "metro", "auto", "train", "flight", "cab", "uber", "ola", "petrol", "fuel", "ticket"],
    Expense.Category.SHOPPING: ["shopping", "clothes", "shoes", "amazon", "flipkart", "dress", "gadget", "watch"],
    Expense.Category.EDUCATION: ["education", "book", "books", "course", "stationery", "exam", "college", "fees", "tuition", "xerox", "print"],
    Expense.Category.ENTERTAINMENT: ["entertainment", "movie", "cinema", "game", "netflix", "party", "outing", "concert", "hotstar"],
    Expense.Category.MISC: ["misc", "recharge", "mobile", "wifi", "bill", "laundry", "medical", "medicine"],
}

INCOME_SOURCE_KEYWORDS = {
    Income.SourceType.POCKET_MONEY: ["pocket money", "allowance", "parents", "home"],
    Income.SourceType.SCHOLARSHIP: ["scholarship", "grant", "fellowship"],
    Income.SourceType.FREELANCE: ["freelance", "project", "gig", "client"],
    Income.SourceType.PART_TIME: ["part-time", "job", "salary", "internship", "stipend"],
    Income.SourceType.GIFT: ["gift", "birthday"],
}


def strip_markdown_stars(text: str) -> str:
    """Removes double asterisks (**) and single asterisks for bolding to ensure clean text formatting."""
    # Replace **text** with text
    cleaned = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
    # Remove any stray double asterisks
    cleaned = cleaned.replace("**", "")
    return cleaned.strip()


def build_user_finance_context(user) -> Dict[str, Any]:
    """Compiles real financial snapshot strictly for the authenticated user."""
    now = timezone.now().date()
    month_start = date(now.year, now.month, 1)

    if now.month == 12:
        next_month_start = date(now.year + 1, 1, 1)
        days_in_month = 31
    else:
        next_month_start = date(now.year, now.month + 1, 1)
        days_in_month = (next_month_start - month_start).days

    remaining_days = max(1, days_in_month - now.day + 1)

    profile = getattr(user, "profile", None)
    monthly_income_cap = float(profile.monthly_income) if profile and profile.monthly_income else 0.0
    currency = profile.currency if profile and profile.currency else "INR"
    curr_sym = "₹" if currency == "INR" else f"{currency} "

    # Month expenses
    month_expenses = Expense.objects.filter(user=user, date__gte=month_start, date__lt=next_month_start)
    total_expense = float(month_expenses.aggregate(total=Sum("amount"))["total"] or 0.0)

    category_spent: Dict[str, float] = {}
    for cat_choice in Expense.Category.values:
        cat_total = float(
            month_expenses.filter(category=cat_choice).aggregate(total=Sum("amount"))["total"] or 0.0
        )
        category_spent[cat_choice] = cat_total

    month_incomes = Income.objects.filter(user=user, date__gte=month_start, date__lt=next_month_start)
    total_income = float(month_incomes.aggregate(total=Sum("amount"))["total"] or 0.0)

    active_budgets = Budget.objects.filter(user=user, month=month_start)
    total_budget_limit = float(active_budgets.aggregate(total=Sum("limit_amount"))["total"] or 0.0)

    budgets_detail = []
    overbudget_categories = []
    for b in active_budgets:
        spent = category_spent.get(b.category, 0.0)
        limit = float(b.limit_amount)
        util = (spent / limit * 100) if limit > 0 else 0
        rem = limit - spent
        if rem < 0:
            overbudget_categories.append(b.category)
        budgets_detail.append({
            "category": b.category,
            "limit": limit,
            "spent": spent,
            "remaining": rem,
            "utilization": round(util, 1),
        })

    net_balance = total_income - total_expense
    remaining_budget = total_budget_limit - total_expense
    safe_daily_spend = max(0.0, remaining_budget / remaining_days) if total_budget_limit > 0 else 0.0

    sorted_categories = sorted(category_spent.items(), key=lambda x: x[1], reverse=True)
    top_category = sorted_categories[0] if sorted_categories and sorted_categories[0][1] > 0 else None

    recent = list(
        Expense.objects.filter(user=user).order_by("-date", "-created_at")[:5].values(
            "title", "amount", "category", "date"
        )
    )

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


def call_gemini_api(user, query: str, context: Dict[str, Any]) -> Optional[str]:
    """Queries Gemini API with the user's grounded financial data and formatting rules."""
    key = GEMINI_API_KEY
    if not key:
        return None

    system_instruction = (
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
        f"• Student Name: {context['user_name']}\n"
        f"• Current Month: {context['current_month']}\n"
        f"• Currency: {context['curr_sym']}\n"
        f"• Monthly Income / Allowance: {context['curr_sym']}{context['monthly_income_cap']:,.2f}\n"
        f"• Total Income Recorded this month: {context['curr_sym']}{context['total_income']:,.2f}\n"
        f"• Total Expenses this month: {context['curr_sym']}{context['total_expense']:,.2f}\n"
        f"• Net Balance (Income - Expense): {context['curr_sym']}{context['net_balance']:,.2f}\n"
        f"• Total Budget Limit Set: {context['curr_sym']}{context['total_budget_limit']:,.2f}\n"
        f"• Remaining Budget: {context['curr_sym']}{context['remaining_budget']:,.2f}\n"
        f"• Safe Daily Spending for remaining {context['remaining_days']} days: {context['curr_sym']}{context['safe_daily_spend']:,.2f} per day\n"
        f"• Category Spending: {json.dumps(context['category_spent'])}\n"
        f"• Active Budgets: {json.dumps(context['budgets_detail'])}\n"
        f"• Overbudget Categories: {', '.join(context['overbudget_categories']) if context['overbudget_categories'] else 'None'}\n"
    )

    models_to_try = ["models/gemini-3-flash-preview", "models/gemini-3.5-flash"]

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": system_instruction},
                    {"text": f"User question: {query}\n\nRemember: Do not use ** for bolding. Reply cleanly with bullet points and emojis."},
                ]
            }
        ]
    }

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                    text = candidates[0]["content"]["parts"][0].get("text", "")
                    if text:
                        return strip_markdown_stars(text)
        except Exception:
            continue

    return None


def try_action_dispatch(user, query: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """Parses actionable commands (logging an expense, setting a budget, recording income)."""
    q = query.strip()
    q_lower = q.lower()
    curr_date = timezone.now().date()
    month_first = date(curr_date.year, curr_date.month, 1)

    # 1. Action: Log Expense
    expense_triggers = ["log expense", "add expense", "spent", "paid", "bought", "spend"]
    is_expense_action = any(trigger in q_lower for trigger in expense_triggers)

    if is_expense_action and not ("how much" in q_lower or "what did i" in q_lower or "budget" in q_lower and "set" in q_lower):
        amount_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)", q_lower)
        if amount_match:
            amount = Decimal(amount_match.group(1))
            matched_cat = Expense.Category.MISC
            for cat, keywords in CATEGORY_KEYWORDS.items():
                if any(kw in q_lower for kw in keywords):
                    matched_cat = cat
                    break

            title = q
            for prefix in ["log expense", "add expense", "spent", "paid"]:
                if q_lower.startswith(prefix):
                    title = q[len(prefix):].strip()
                    break
            title = re.sub(r"^(of|for|on|rs\.?|₹|\d+(\.\d{1,2})?|\s)+", "", title, flags=re.IGNORECASE).strip()
            if not title:
                title = f"{matched_cat.capitalize()} Expense"

            expense = Expense.objects.create(
                user=user,
                title=title[:100],
                amount=amount,
                category=matched_cat,
                date=curr_date,
                payment_method=Expense.PaymentMethod.UPI,
                notes="Logged via BudgetBuddy AI Assistant",
            )

            res = (
                f"✅ Expense Logged Successfully!\n\n"
                f"• Title: {expense.title}\n"
                f"• Amount: ₹{expense.amount:,.2f}\n"
                f"• Category: {expense.get_category_display()}\n"
                f"• Date: {expense.date.strftime('%d %b %Y')}\n\n"
                f"Your monthly totals and budget gauges have been updated automatically."
            )
            return ("expense_created", res, {"id": expense.id, "amount": str(expense.amount), "category": expense.category})

    # 2. Action: Set Budget Limit
    is_budget_question = (
        any(q_lower.startswith(w) for w in ["how", "what", "is there", "is it", "can i", "can you", "show", "check", "do i", "should i", "am i"])
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
            or re.search(r"(?:of|to|is|=|limit|budget)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)", q_lower)
            or re.search(r"(\d+(?:,\d+)*(?:\.\d{1,2})?)\s*(?:per day|daily|/day|per month|monthly|/month|rupees|rs)", q_lower)
            or re.search(r"\b(\d+(?:,\d+)*(?:\.\d{1,2})?)\b", q_lower)
        )
        if amount_match:
            raw_amount = Decimal(amount_match.group(1).replace(",", ""))
            is_daily = any(term in q_lower for term in ["per day", "daily", "a day", "each day", "/day", "/ day", "perday"])

            import calendar
            days_in_month = calendar.monthrange(curr_date.year, curr_date.month)[1]

            if is_daily:
                daily_limit = raw_amount
                monthly_limit = raw_amount * Decimal(days_in_month)
            else:
                monthly_limit = raw_amount
                daily_limit = round(raw_amount / Decimal(days_in_month), 2)

            matched_cat = Expense.Category.MISC
            for cat, keywords in CATEGORY_KEYWORDS.items():
                if any(kw in q_lower for kw in keywords):
                    matched_cat = cat
                    break

            budget_obj, created = Budget.objects.update_or_create(
                user=user,
                month=month_first,
                category=matched_cat,
                defaults={"limit_amount": monthly_limit},
            )

            # Persist preferences and target allowance on Profile
            profile = getattr(user, "profile", None)
            if profile:
                if not isinstance(profile.financial_preferences, dict):
                    profile.financial_preferences = {}
                profile.financial_preferences["daily_budget_limit"] = float(daily_limit)
                profile.financial_preferences["monthly_budget_target"] = float(monthly_limit)
                if not profile.monthly_income or profile.monthly_income == Decimal("0"):
                    profile.monthly_income = monthly_limit
                profile.save()

            verb = "created" if created else "updated"
            daily_info = f"\n• Daily Rate: ₹{daily_limit:,.2f} / day ({days_in_month} days in {month_first.strftime('%B')})" if is_daily else ""
            res = (
                f"🎯 Monthly Budget {verb.capitalize()} Successfully!\n\n"
                f"• Category: {budget_obj.get_category_display()}\n"
                f"• Monthly Spending Limit: ₹{budget_obj.limit_amount:,.2f}{daily_info}\n"
                f"• Active Month: {month_first.strftime('%B %Y')}\n\n"
                f"✅ Updated your live dashboard budget gauge and runway."
            )
            return (
                "budget_created",
                res,
                {
                    "category": budget_obj.category,
                    "limit": str(budget_obj.limit_amount),
                    "daily_limit": str(daily_limit),
                    "is_daily": is_daily,
                },
            )

    # 3. Action: Record Income
    if "income" in q_lower or "received" in q_lower or "got" in q_lower and ("money" in q_lower or "stipend" in q_lower):
        amount_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)", q_lower)
        if amount_match and ("add" in q_lower or "record" in q_lower or "got" in q_lower or "received" in q_lower):
            amount = Decimal(amount_match.group(1))
            matched_source = Income.SourceType.POCKET_MONEY
            for source, keywords in INCOME_SOURCE_KEYWORDS.items():
                if any(kw in q_lower for kw in keywords):
                    matched_source = source
                    break

            income = Income.objects.create(
                user=user,
                title=f"{matched_source.replace('_', ' ').capitalize()}",
                amount=amount,
                source_type=matched_source,
                date=curr_date,
                notes="Logged via BudgetBuddy AI Assistant",
            )

            res = (
                f"💰 Income Recorded!\n\n"
                f"• Source: {income.get_source_type_display()}\n"
                f"• Amount: ₹{income.amount:,.2f}\n"
                f"• Date: {income.date.strftime('%d %b %Y')}\n\n"
                f"Your net balance has been updated."
            )
            return ("income_created", res, {"id": income.id, "amount": str(income.amount)})

    return None


def generate_assistant_response(user, query: str) -> Tuple[str, str, Dict[str, Any]]:
    """Generates financial response for the authenticated user using Gemini API,
    with clean formatting (no double stars) and security sanitization.
    """
    ctx = build_user_finance_context(user)
    sym = ctx["curr_sym"]

    # 1. Check for actionable commands first
    action = try_action_dispatch(user, query)
    if action:
        action_type, resp, data = action
        return (sanitize_output(strip_markdown_stars(resp)), action_type, data)

    # 2. Query Google Gemini with live context
    gemini_reply = call_gemini_api(user, query, ctx)
    if gemini_reply:
        cleaned_reply = strip_markdown_stars(gemini_reply)
        return (sanitize_output(cleaned_reply), "gemini_response", {})

    # 3. Fallback deterministic reasoning if Gemini is temporarily unavailable
    q = query.strip().lower()

    if any(k in q for k in ["safe", "daily", "per day", "burn rate", "how much can i spend"]):
        if ctx["total_budget_limit"] > 0:
            resp = (
                f"📊 Daily Spending Recommendation for {ctx['current_month']}:\n\n"
                f"• Remaining Total Budget: {sym}{ctx['remaining_budget']:,.2f}\n"
                f"• Remaining Days in Month: {ctx['remaining_days']} days\n"
                f"• Safe Daily Allowance: {sym}{ctx['safe_daily_spend']:,.2f} / day\n\n"
                f"💡 Student Pro-Tip: Staying below {sym}{ctx['safe_daily_spend']:,.2f} per day ensures you finish {ctx['current_month']} within your budget."
            )
        else:
            resp = (
                f"You haven't set any monthly budget limits yet for {ctx['current_month']}.\n\n"
                f"• Total spent so far: {sym}{ctx['total_expense']:,.2f} over {31 - ctx['remaining_days']} days.\n\n"
                f"You can set a limit by typing: 'Set budget 4000 for food' or on the Budgets page."
            )
        return (sanitize_output(strip_markdown_stars(resp)), "query_daily_safe", {})

    if any(k in q for k in ["total spend", "how much have i spent", "my expenses", "spending summary", "spent this month"]):
        top_text = f"Your highest expenditure is on {ctx['top_category'][0].capitalize()} ({sym}{ctx['top_category'][1]:,.2f})." if ctx["top_category"] else "No expenses recorded this month."
        resp = (
            f"📈 Your Spending Snapshot for {ctx['current_month']}:\n\n"
            f"• Total Spent: {sym}{ctx['total_expense']:,.2f}\n"
            f"• Total Income Recorded: {sym}{ctx['total_income']:,.2f}\n"
            f"• Net Balance: {sym}{ctx['net_balance']:,.2f}\n\n"
            f"{top_text}"
        )
        return (sanitize_output(strip_markdown_stars(resp)), "query_expenses", {})

    # General fallback
    resp = (
        f"Hello {ctx['user_name']}! Here is your quick budget overview for {ctx['current_month']}:\n\n"
        f"• Total Spent: {sym}{ctx['total_expense']:,.2f}\n"
        f"• Remaining Budget: {sym}{ctx['remaining_budget']:,.2f}\n"
        f"• Safe Daily Rate: {sym}{ctx['safe_daily_spend']:,.2f} / day\n\n"
        f"You can ask me questions about your spending, daily allowances, or type 'Spent 150 on food' to log a transaction."
    )
    return (sanitize_output(strip_markdown_stars(resp)), "fallback", {})
