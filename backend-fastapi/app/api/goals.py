"""SavingsGoals router — port of ``apps/goals`` (viewset + deposit action).

Serializer quirks preserved:

* ``saved_amount``/``deadline`` are writable aliases of
  ``current_amount``/``target_date`` (a later ``deadline`` key wins, like the
  DRF field ordering) while ``current_amount``/``target_date`` write too —
  ``target_date`` is required on full writes but may be null;
* the cross-field ``validate()`` errors render wrapped in a list
  (``{"target_amount": ["Target amount must be positive."]}``)
  whereas the ``deposit`` action answers with plain strings.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession, json_body, owned_object
from app.core.errors import APIError
from app.core.pagination import paginate
from app.core.serializers import goal_dict
from app.core.validation import (
    BLANK,
    NULL,
    REQUIRED,
    DATE_FORMAT,
    Errors,
    validate_char,
    validate_choice,
    validate_decimal,
)
from app.db import models
from app.services.notifications import create_goal_completed_notification

router = APIRouter()


def _parse_deposit_amount(raw: Any) -> Decimal | None:
    try:
        return Decimal(str(raw))
    except (KeyError, TypeError, ValueError, InvalidOperation, ArithmeticError):
        return None


def _values(
    body: dict[str, Any], partial: bool, instance: models.SavingsGoal | None
) -> tuple[Errors, dict[str, Any]]:
    errors = Errors()
    values: dict[str, Any] = {}

    # title — CharField(max_length=120)
    if "title" in body:
        values["title"] = errors.run(
            validate_char, body, "title", max_length=120, required=True
        )
    elif not partial:
        errors.add("title", "This field is required.")

    # description — TextField(blank=True, default="")
    if "description" in body:
        values["description"] = errors.run(
            _text_value, body, "description"
        )
    elif not partial:
        values["description"] = ""

    # target_amount — DecimalField(max_digits=12, decimal_places=2, required)
    if "target_amount" in body:
        values["target_amount"] = errors.run(validate_decimal, body, "target_amount")
    elif not partial:
        errors.add("target_amount", "This field is required.")

    # priority — ChoiceField(default="medium")
    if "priority" in body:
        values["priority"] = errors.run(
            validate_choice, body, "priority", models.GOAL_PRIORITIES
        )
    elif not partial:
        values["priority"] = "medium"

    # target_date — DateField(required, allow_null)
    if "target_date" in body:
        values["target_date"] = errors.run(_target_date, body, "target_date")
    elif not partial:
        errors.add("target_date", "This field is required.")

    # deadline — DateField(source="target_date", required=False, allow_null)
    # Declared after target_date, so a duplicate key wins (DRF field order).
    if "deadline" in body:
        values["target_date"] = errors.run(_target_date, body, "deadline")

    # saved_amount — DecimalField(source="current_amount", required=False)
    if "saved_amount" in body:
        values["current_amount"] = errors.run(
            _saved_amount, body, "saved_amount"
        )

    # current_amount is read-only in the serializer; nothing to do on input.

    return errors, values


def _text_value(body: dict[str, Any], field: str):
    from app.core.validation import validate_text

    return validate_text(body, field, default="")


def _target_date(body: dict[str, Any], field: str):
    """DateField(allow_null=True)."""
    raw = body[field]
    if raw is None:
        return None
    if isinstance(raw, _dt.date):
        return raw
    try:
        return _dt.date.fromisoformat(str(raw).strip())
    except (TypeError, ValueError):
        raise APIError(400, {field: [DATE_FORMAT]}) from None


def _saved_amount(body: dict[str, Any], field: str):
    from app.core.validation import validate_decimal

    return validate_decimal(body, field)


def _cross_validation(
    values: dict[str, Any], instance: models.SavingsGoal | None
) -> None:
    """ ``SavingsGoalSerializer.validate`` (only reached with clean fields)."""
    target = values.get(
        "target_amount",
        instance.target_amount if instance is not None else None,
    )
    current = values.get(
        "current_amount",
        instance.current_amount if instance is not None else Decimal("0"),
    )
    if target is not None and Decimal(target) <= 0:
        raise APIError(400, {"target_amount": ["Target amount must be positive."]})
    if current < 0:
        raise APIError(400, {"current_amount": ["Current amount cannot be negative."]})


def _apply(values: dict[str, Any], goal: models.SavingsGoal) -> None:
    for field, value in values.items():
        setattr(goal, field, value)
    goal.sync_completion()  # Django model save() recompute


@router.get("/goals/", response_model=None)
async def list_goals(request: Request, user: CurrentUser, db: DbSession):
    rows = (
        await db.execute(
            select(models.SavingsGoal)
            .where(models.SavingsGoal.user_id == user.id)
            .order_by(models.SavingsGoal.created_at.desc())
        )
    ).scalars().all()
    items = [goal_dict(row) for row in rows]
    return paginate(request, items, len(rows))


@router.post("/goals/", status_code=201, response_model=None)
async def create_goal(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    errors, values = _values(body, partial=False, instance=None)
    errors.raise_if_any()
    _cross_validation(values, instance=None)

    goal = models.SavingsGoal(user_id=user.id, **values)
    goal.sync_completion()
    db.add(goal)
    await db.flush()
    await create_goal_completed_notification(db, goal)  # goals.post_save port
    await db.commit()
    return goal_dict(goal)


@router.get("/goals/{pk}/", response_model=None)
async def retrieve_goal(pk: str, user: CurrentUser, db: DbSession):
    goal = await owned_object(db, models.SavingsGoal, user, pk)
    return goal_dict(goal)


async def _update_goal(
    request: Request, user: models.User, db: DbSession, raw_pk: str, *, partial: bool
):
    goal = await owned_object(db, models.SavingsGoal, user, raw_pk)
    body = await json_body(request)
    errors, values = _values(body, partial=partial, instance=goal)
    errors.raise_if_any()
    _cross_validation(values, instance=goal)

    _apply(values, goal)
    await db.flush()
    await create_goal_completed_notification(db, goal)  # goals.post_save port
    await db.commit()
    return goal_dict(goal)


@router.patch("/goals/{pk}/", response_model=None)
async def patch_goal(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_goal(request, user, db, pk, partial=True)


@router.put("/goals/{pk}/", response_model=None)
async def put_goal(pk: str, request: Request, user: CurrentUser, db: DbSession):
    return await _update_goal(request, user, db, pk, partial=False)


@router.delete("/goals/{pk}/", status_code=204, response_model=None)
async def delete_goal(pk: str, user: CurrentUser, db: DbSession):
    goal = await owned_object(db, models.SavingsGoal, user, pk)
    await db.delete(goal)
    await db.commit()
    return Response(status_code=204)


@router.post("/goals/{pk}/deposit/", response_model=None)
async def deposit_goal(pk: str, request: Request, user: CurrentUser, db: DbSession):
    goal = await owned_object(db, models.SavingsGoal, user, pk)
    amount = _parse_deposit_amount((await json_body(request)).get("amount"))
    if amount is None:
        raise APIError(400, {"amount": "A valid amount is required."})
    if amount <= 0:
        raise APIError(400, {"amount": "Amount must be positive."})

    goal.current_amount += amount
    goal.sync_completion()
    await db.flush()
    await create_goal_completed_notification(db, goal)  # goals.post_save port
    await db.commit()
    return goal_dict(goal)
