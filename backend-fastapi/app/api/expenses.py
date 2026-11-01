"""Expense + Income routers — port of ``apps/expenses`` (viewsets).

POST/PATCH behaviour notes:

* fields with model defaults (``category: misc``, ``payment_method: cash``,
  ``source_type: pocket_money``, blank ``notes``) are optional and filled with
  the model default on full writes (POST/PUT); a PATCH only touches provided
  fields;
* every expense write triggers the post_save ``budget_alert_hook`` port plus
  ``check_budget_alerts`` (the viewset's ``perform_create``/``perform_update``);
* query parameters mirror DRF's ``get_queryset`` — a malformed ``month``
  yields an empty result set (``queryset.none()``), while a malformed
  ``date_from``/``date_to`` raises Django's unhandled 500 path.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, json_body, owned_object
from app.core.errors import APIError
from app.core.pagination import paginate
from app.core.serializers import dt_iso, expense_dict, income_dict
from app.core.validation import (
    MISSING,
    Errors,
    validate_char,
    validate_choice,
    validate_date,
    validate_decimal,
    validate_text,
)
from app.db import models
from app.services.notifications import budget_alert_for_expense, check_budget_alerts

router = APIRouter()

FULL_WRITE = object()  # sentinel: POST or PUT (missing optional fields get defaults)


# ---------------------------------------------------------------------------
# Field validation (message parity — field order matters)
# ---------------------------------------------------------------------------
def _expense_values(
    body: dict[str, Any], partial: bool
) -> tuple[Errors, dict[str, Any]]:
    errors = Errors()
    values: dict[str, Any] = {}

    # category — ChoiceField(default="misc")
    if "category" in body:
        values["category"] = errors.run(
            validate_choice, body, "category", models.EXPENSE_CATEGORIES
        )
    elif not partial:
        values["category"] = "misc"

    # title — CharField(max_length=120)
    if "title" in body:
        values["title"] = errors.run(
            validate_char, body, "title", max_length=120, required=not partial
        )
    else:
        errors.add("title", "This field is required.")

    # amount — DecimalField(max_digits=12, decimal_places=2)
    if "amount" in body:
        values["amount"] = errors.run(validate_decimal, body, "amount")
    else:
        errors.add("amount", "This field is required.")

    # date — DateField
    if "date" in body:
        values["date"] = errors.run(validate_date, body, "date")
    else:
        errors.add("date", "This field is required.")

    # payment_method — ChoiceField(default="cash")
    if "payment_method" in body:
        values["payment_method"] = errors.run(
            validate_choice, body, "payment_method", models.PAYMENT_METHODS
        )
    elif not partial:
        values["payment_method"] = "cash"

    # notes — TextField(blank=True, default="")
    if "notes" in body:
        values["notes"] = errors.run(validate_text, body, "notes", default="")
    elif not partial:
        values["notes"] = ""

    return errors, values


def _income_values(body: dict[str, Any], partial: bool) -> tuple[Errors, dict[str, Any]]:
    errors = Errors()
    values: dict[str, Any] = {}

    # source_type — ChoiceField(default="pocket_money")
    if "source_type" in body:
        values["source_type"] = errors.run(
            validate_choice, body, "source_type", models.INCOME_SOURCES
        )
    elif not partial:
        values["source_type"] = "pocket_money"

    if "title" in body:
        values["title"] = errors.run(
            validate_char, body, "title", max_length=120, required=not partial
        )
    else:
        errors.add("title", "This field is required.")

    if "amount" in body:
        values["amount"] = errors.run(validate_decimal, body, "amount")
    else:
        errors.add("amount", "This field is required.")

    if "date" in body:
        values["date"] = errors.run(validate_date, body, "date")
    else:
        errors.add("date", "This field is required.")

    if "notes" in body:
        values["notes"] = errors.run(validate_text, body, "notes", default="")
    elif not partial:
        values["notes"] = ""

    return errors, values


async def _after_expense_write(
    db: AsyncSession, user: models.User, expense: models.Expense
) -> None:
    """``perform_create``/``perform_update`` + the post_save signal port."""
    await budget_alert_for_expense(db, user, expense)
    await check_budget_alerts(db, user)


# ---------------------------------------------------------------------------
# Shared queryset helpers
# ---------------------------------------------------------------------------
EMPTY = object()  # sentinel for queryset.none() semantics


def _parse_month(raw: str | None) -> tuple[int, int] | None | Any:
    """``(year, month)``, :data:`EMPTY` (bad ``month`` -> empty result) or None."""
    if raw is None:
        return None
    try:
        year, month = (int(part) for part in raw.split("-"))
    except (TypeError, ValueError):
        return EMPTY
    return (year, month)


def _parse_date_bound(raw: str | None) -> date | None:
    """Django raises at SQL time for an unparsable bound -> 500."""
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw.strip())
    except (TypeError, ValueError):
        raise APIError(500, {"detail": "Internal Server Error"}) from None


def _json_date(raw: date | str | Any) -> str | None:
    return raw.isoformat() if hasattr(raw, "isoformat") else str(raw)


async def _expense_filters(
    db: AsyncSession, user: models.User, request: Request
):
    params = request.query_params
    stmt = select(models.Expense).where(models.Expense.user_id == user.id)

    month = _parse_month(params.get("month"))
    if month is EMPTY:
        return None
    if month is not None:
        year, month_no = month
        stmt = stmt.where(
            func.extract("year", models.Expense.date) == year,
            func.extract("month", models.Expense.date) == month_no,
        )

    date_from = _parse_date_bound(params.get("date_from"))
    if date_from is not None:
        stmt = stmt.where(models.Expense.date >= date_from)
    date_to = _parse_date_bound(params.get("date_to"))
    if date_to is not None:
        stmt = stmt.where(models.Expense.date <= date_to)

    if params.get("category"):
        stmt = stmt.where(models.Expense.category == params["category"])
    if params.get("payment_method"):
        stmt = stmt.where(models.Expense.payment_method == params["payment_method"])
    if params.get("search"):
        stmt = stmt.where(func.lower(models.Expense.title).like(f"%{params['search'].lower()}%"))

    return stmt.order_by(models.Expense.date.desc(), models.Expense.created_at.desc())


async def _income_filters(db: AsyncSession, user: models.User, request: Request):
    params = request.query_params
    stmt = select(models.Income).where(models.Income.user_id == user.id)

    month = _parse_month(params.get("month"))
    if month is EMPTY:
        return None
    if month is not None:
        year, month_no = month
        stmt = stmt.where(
            func.extract("year", models.Income.date) == year,
            func.extract("month", models.Income.date) == month_no,
        )

    date_from = _parse_date_bound(params.get("date_from"))
    if date_from is not None:
        stmt = stmt.where(models.Income.date >= date_from)
    date_to = _parse_date_bound(params.get("date_to"))
    if date_to is not None:
        stmt = stmt.where(models.Income.date <= date_to)

    if params.get("source_type"):
        stmt = stmt.where(models.Income.source_type == params["source_type"])

    return stmt.order_by(models.Income.date.desc(), models.Income.created_at.desc())


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------
@router.get("/expenses/", response_model=None)
async def list_expenses(request: Request, user: CurrentUser, db: DbSession):
    stmt = await _expense_filters(db, user, request)
    if stmt is None:  # bad month -> queryset.none()
        return paginate(request, [], 0)
    rows = (await db.execute(stmt)).scalars().all()
    items = [expense_dict(row) for row in rows]
    return paginate(request, items, len(rows))


@router.post("/expenses/", status_code=201, response_model=None)
async def create_expense(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    errors, values = _expense_values(body, partial=False)
    errors.raise_if_any()

    expense = models.Expense(user_id=user.id, **values)
    db.add(expense)
    await db.flush()
    await _after_expense_write(db, user, expense)
    await db.commit()
    return expense_dict(expense)


@router.get("/expenses/{pk}/", response_model=None)
async def retrieve_expense(pk: str, user: CurrentUser, db: DbSession):
    expense = await owned_object(db, models.Expense, user, pk)
    return expense_dict(expense)


async def _update_expense(
    request: Request, user: models.User, db: DbSession, raw_pk: str, *, partial: bool
):
    expense = await owned_object(db, models.Expense, user, raw_pk)
    body = await json_body(request)
    errors, values = _expense_values(body, partial=partial)
    errors.raise_if_any()

    for field, value in values.items():
        setattr(expense, field, value)

    await db.flush()
    await _after_expense_write(db, user, expense)
    await db.commit()
    return expense_dict(expense)


@router.patch("/expenses/{pk}/", response_model=None)
async def patch_expense(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_expense(request, user, db, pk, partial=True)


@router.put("/expenses/{pk}/", response_model=None)
async def put_expense(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_expense(request, user, db, pk, partial=False)


@router.delete("/expenses/{pk}/", status_code=204, response_model=None)
async def delete_expense(pk: str, user: CurrentUser, db: DbSession):
    expense = await owned_object(db, models.Expense, user, pk)
    await db.delete(expense)
    await db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Incomes
# ---------------------------------------------------------------------------
@router.get("/incomes/", response_model=None)
async def list_incomes(request: Request, user: CurrentUser, db: DbSession):
    stmt = await _income_filters(db, user, request)
    if stmt is None:  # bad month -> queryset.none()
        return paginate(request, [], 0)
    rows = (await db.execute(stmt)).scalars().all()
    items = [income_dict(row) for row in rows]
    return paginate(request, items, len(rows))


@router.post("/incomes/", status_code=201, response_model=None)
async def create_income(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    errors, values = _income_values(body, partial=False)
    errors.raise_if_any()

    income = models.Income(user_id=user.id, **values)
    db.add(income)
    await db.flush()
    await db.commit()
    return income_dict(income)


@router.get("/incomes/{pk}/", response_model=None)
async def retrieve_income(pk: str, user: CurrentUser, db: DbSession):
    income = await owned_object(db, models.Income, user, pk)
    return income_dict(income)


async def _update_income(
    request: Request, user: models.User, db: DbSession, raw_pk: str, *, partial: bool
):
    income = await owned_object(db, models.Income, user, raw_pk)
    body = await json_body(request)
    errors, values = _income_values(body, partial=partial)
    errors.raise_if_any()

    for field, value in values.items():
        setattr(income, field, value)

    await db.flush()
    await db.commit()
    return income_dict(income)


@router.patch("/incomes/{pk}/", response_model=None)
async def patch_income(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_income(request, user, db, pk, partial=True)


@router.put("/incomes/{pk}/", response_model=None)
async def put_income(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_income(request, user, db, pk, partial=False)


@router.delete("/incomes/{pk}/", status_code=204, response_model=None)
async def delete_income(pk: str, user: CurrentUser, db: DbSession):
    income = await owned_object(db, models.Income, user, pk)
    await db.delete(income)
    await db.commit()
    return Response(status_code=204)
