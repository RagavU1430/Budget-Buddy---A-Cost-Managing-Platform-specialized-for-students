"""Budget router — port of ``apps/budgets`` (viewset).

Ordering is ``["-month", "category"]``; list filters are ``month``
(``YYYY-MM``) and ``category``. A duplicate ``(user, month, category)``
insert 500s in Django (IntegrityError); here it answers 400 with a
DRF-envelope body — a documented, deliberate deviation.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession, json_body, owned_object
from app.core.errors import APIError
from app.core.pagination import paginate
from app.core.serializers import budget_dict
from app.core.validation import (
    Errors,
    validate_choice,
    validate_date,
    validate_decimal,
)
from app.db import models

router = APIRouter()

INTERNAL_ERROR = APIError(500, {"detail": "Internal Server Error"})


def _parse_month(raw: str | None) -> Any:
    """``(year, month)`` or ``None`` when the filter simply matches nothing.

    ``Budget.objects.filter(month=raw + "-01")`` with a bad ``raw`` raises
    inside Django -> unhandled -> 500; with a valid ``YYYY-MM`` it also
    matches regardless of the day component Django appends.
    """
    if raw is None:
        return None
    try:
        parsed = date.fromisoformat(f"{raw.strip()}-01")
    except (TypeError, ValueError):
        raise APIError(500, {"detail": "Internal Server Error"}) from None
    return parsed


def _values(body: dict[str, Any], partial: bool) -> tuple[Errors, dict[str, Any]]:
    errors = Errors()
    values: dict[str, Any] = {}

    # month — DateField (required, no default/null)
    if "month" in body:
        values["month"] = errors.run(validate_date, body, "month")
    else:
        errors.add("month", "This field is required.")

    # category — ChoiceField(default="misc")
    if "category" in body:
        values["category"] = errors.run(
            validate_choice, body, "category", models.EXPENSE_CATEGORIES
        )
    elif not partial:
        values["category"] = "misc"

    # limit_amount — DecimalField(max_digits=12, decimal_places=2, default=0)
    if "limit_amount" in body:
        values["limit_amount"] = errors.run(validate_decimal, body, "limit_amount")
    elif not partial:
        values["limit_amount"] = 0

    return errors, values


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/budgets/", response_model=None)
async def list_budgets(request: Request, user: CurrentUser, db: DbSession):
    params = request.query_params
    stmt = select(models.Budget).where(models.Budget.user_id == user.id)

    if params.get("month"):
        stmt = stmt.where(models.Budget.month == _parse_month(params["month"]))
    if params.get("category"):
        stmt = stmt.where(models.Budget.category == params["category"])

    stmt = stmt.order_by(models.Budget.month.desc(), models.Budget.category)
    rows = (await db.execute(stmt)).scalars().all()
    items = [budget_dict(row) for row in rows]
    return paginate(request, items, len(rows))


@router.post("/budgets/", status_code=201, response_model=None)
async def create_budget(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    errors, values = _values(body, partial=False)
    errors.raise_if_any()

    budget = models.Budget(user_id=user.id, **values)
    db.add(budget)
    try:
        await db.commit()
    except IntegrityError:
        # Django answers 500 here (IntegrityError); deliberate contract deviation.
        await db.rollback()
        raise APIError(
            400,
            {
                "non_field_errors": [
                    "Budget with this month and category already exists for this user."
                ]
            },
        ) from None
    await db.refresh(budget)
    return budget_dict(budget)


@router.get("/budgets/{pk}/", response_model=None)
async def retrieve_budget(pk: str, user: CurrentUser, db: DbSession):
    budget = await owned_object(db, models.Budget, user, pk)
    return budget_dict(budget)


async def _update_budget(
    request: Request, user: models.User, db: DbSession, raw_pk: str, *, partial: bool
):
    budget = await owned_object(db, models.Budget, user, raw_pk)
    body = await json_body(request)
    errors, values = _values(body, partial=partial)
    errors.raise_if_any()

    for field, value in values.items():
        setattr(budget, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise APIError(
            400,
            {
                "non_field_errors": [
                    "Budget with this month and category already exists for this user."
                ]
            },
        ) from None
    await db.refresh(budget)
    return budget_dict(budget)


@router.patch("/budgets/{pk}/", response_model=None)
async def patch_budget(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_budget(request, user, db, pk, partial=True)


@router.put("/budgets/{pk}/", response_model=None)
async def put_budget(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_budget(request, user, db, pk, partial=False)


@router.delete("/budgets/{pk}/", status_code=204, response_model=None)
async def delete_budget(pk: str, user: CurrentUser, db: DbSession):
    budget = await owned_object(db, models.Budget, user, pk)
    await db.delete(budget)
    await db.commit()
    return Response(status_code=204)
