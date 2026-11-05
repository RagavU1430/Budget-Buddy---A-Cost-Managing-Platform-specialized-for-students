"""Notifications router — port of ``apps/notifications`` (viewset).

``http_method_names`` excludes ``put``, so ``PUT /api/notifications/<pk>/``
answers 405 with DRF's ``Method "PUT" not allowed.`` (handled globally).

The list ordering is ``-created_at``; the ``unread`` filter accepts exactly
``1``/``true``/``yes`` (case-sensitive, like Django's set membership check).
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select, update

from app.api.deps import CurrentUser, DbSession, json_body, owned_object
from app.core.errors import APIError, validation_error
from app.core.pagination import paginate
from app.core.serializers import notification_dict
from app.core.validation import BOOLEAN, NULL, validate_boolean
from app.db import models

router = APIRouter()


def _strict_boolean(raw: object) -> bool:
    """DRF BooleanField semantics (frozenset-style accepted values)."""
    if isinstance(raw, bool):
        return raw
    if raw in (1, "1", "true", "True", "TRUE"):
        return True
    if raw in (0, "0", "false", "False", "FALSE"):
        return False
    raise validation_error({"is_read": [BOOLEAN]})


def _scoped_stmt(request: Request, user: models.User, *, for_count: bool = False):
    """ ``get_queryset()``: user scope + optional ``unread`` filter."""
    stmt = select(models.Notification).where(models.Notification.user_id == user.id)
    if request.query_params.get("unread") in {"1", "true", "yes"}:
        stmt = stmt.where(models.Notification.is_read.is_(False))
    if for_count:
        return stmt
    return stmt.order_by(models.Notification.created_at.desc())


@router.get("/notifications/", response_model=None)
async def list_notifications(request: Request, user: CurrentUser, db: DbSession):
    rows = (await db.execute(_scoped_stmt(request, user))).scalars().all()
    items = [notification_dict(row) for row in rows]
    return paginate(request, items, len(rows))


@router.post("/notifications/", status_code=201, response_model=None)
async def create_notification(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)

    # Writable fields: is_read only — the type/title/message are read-only,
    # so a POST creates the model-default empty row (the quirky contract).
    is_read = False
    if "is_read" in body:
        raw = body["is_read"]
        if raw is None:
            raise validation_error({"is_read": [NULL]})
        is_read = validate_boolean(body, "is_read")

    notification = models.Notification(user_id=user.id, is_read=is_read)
    db.add(notification)
    await db.flush()
    await db.commit()
    await db.refresh(notification)
    return notification_dict(notification)


@router.post("/notifications/mark-all-read/", response_model=None)
@router.post("/notifications/mark_all_read/", response_model=None)
async def mark_all_read(request: Request, user: CurrentUser, db: DbSession):
    _ = request
    await db.execute(
        update(models.Notification)
        .where(
            models.Notification.user_id == user.id,
            models.Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"updated": True}


@router.get("/notifications/unread-count/", response_model=None)
@router.get("/notifications/unread_count/", response_model=None)
async def unread_count(request: Request, user: CurrentUser, db: DbSession):
    _ = request
    stmt = select(func.count()).select_from(models.Notification).where(
        models.Notification.user_id == user.id,
        models.Notification.is_read.is_(False),
    )
    total = (await db.execute(stmt)).scalar() or 0
    return {"count": total, "unread_count": total}


@router.get("/notifications/{pk}/", response_model=None)
async def retrieve_notification(pk: str, user: CurrentUser, db: DbSession):
    notification = await owned_object(db, models.Notification, user, pk)
    return notification_dict(notification)


@router.patch("/notifications/{pk}/", response_model=None)
async def patch_notification(pk: str, request: Request, user: CurrentUser, db: DbSession):
    notification = await owned_object(db, models.Notification, user, pk)
    body = await json_body(request)
    if "is_read" in body:
        raw = body["is_read"]
        if raw is None:
            raise validation_error({"is_read": [NULL]})
        is_read = _strict_boolean(raw)
        if is_read != notification.is_read:
            notification.is_read = is_read
    await db.commit()
    await db.refresh(notification)
    return notification_dict(notification)


@router.delete("/notifications/{pk}/", status_code=204, response_model=None)
async def delete_notification(pk: str, user: CurrentUser, db: DbSession):
    notification = await owned_object(db, models.Notification, user, pk)
    await db.delete(notification)
    await db.commit()
    return Response(status_code=204)


@router.post("/notifications/{pk}/mark_read/", response_model=None)
@router.post("/notifications/{pk}/mark-read/", response_model=None)
async def mark_read(pk: str, request: Request, user: CurrentUser, db: DbSession):
    _ = request  # the POST body is unused, exactly like DRF's action
    notification = await owned_object(db, models.Notification, user, pk)
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification_dict(notification)
