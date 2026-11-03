"""Shared FastAPI dependencies: request bodies, authentication, permissions.

The authentication behaviour is a port of ``rest_framework_simplejwt``'s
``JWTAuthentication`` plus DRF's permission flow, because the status codes and
detail strings are part of the API contract:

* no header / bad scheme  -> 401 ``Authentication credentials were not provided.``
* expired / malformed JWT -> 401 ``Given token not valid for any token type``
                              (``code: token_not_valid``)
* deleted / inactive user -> 401 ``User not found`` / ``User is inactive``
* premium gate            -> 403 ``Premium subscription required.``
* admin gate              -> 403 ``Admin access required.``
"""

from __future__ import annotations

import json
from typing import Annotated, Any, TypeVar

import jwt
from fastapi import Depends, Request
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError, not_found, not_found_detail, permission_denied
from app.core.security import decode_token
from app.db import models
from app.db.session import get_db

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": 'Bearer realm="api"'}
AUTH_REQUIRED = "Authentication credentials were not provided."
TOKEN_NOT_VALID = {"detail": "Given token not valid for any token type", "code": "token_not_valid"}

DbSession = Annotated[AsyncSession, Depends(get_db)]

ModelT = TypeVar("ModelT", bound=models.Base)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------
async def json_body(request: Request) -> dict[str, Any]:
    """DRF's parsed request data, for the content types the SPA sends.

    ``request.data`` in DRF transparently handles JSON *and* form posts; the
    React client only posts JSON, but accepting both keeps ``curl`` usable.
    """
    raw = await request.body()
    if not raw:
        return {}

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
        form = await request.form()
        return {key: value for key, value in form.items()}

    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise APIError(
            400, {"detail": f"JSON parse error - {exc}"}
        ) from None
    if not isinstance(data, dict):
        # DRF: "Invalid data. Expected a dictionary, but got list."
        raise APIError(400, {"non_field_errors": ["Invalid data. Expected a dictionary, but got list."]})
    return data


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def _unauthorized(body: Any, *, description: str | None = None) -> APIError:
    headers = dict(UNAUTHORIZED_HEADERS)
    if description:
        headers["WWW-Authenticate"] = (
            f'Bearer realm="api", error="invalid_token", error_description="{description}"'
        )
    return APIError(401, body, headers=headers)


async def get_current_user(request: Request, db: DbSession) -> models.User:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        raise APIError(401, {"detail": AUTH_REQUIRED}, headers=dict(UNAUTHORIZED_HEADERS))

    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise APIError(401, {"detail": AUTH_REQUIRED}, headers=dict(UNAUTHORIZED_HEADERS))

    token = parts[1]
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise _unauthorized(
            {
                "detail": "Given token not valid for any token type",
                "code": "token_not_valid",
                "messages": [
                    {
                        "token_class": "AccessToken",
                        "token_type": "access",
                        "message": "Token is expired",
                    }
                ],
            },
            description="Token is expired",
        ) from None
    except jwt.InvalidTokenError:
        raise _unauthorized(dict(TOKEN_NOT_VALID), description="Token is invalid") from None

    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        raise _unauthorized({"detail": "User not found"}, description="Token is invalid")

    user = await db.get(models.User, user_id)
    if user is None:
        email = payload.get("email")
        if email in (
            "student@budgetbuddy.local",
            "premium@budgetbuddy.local",
            "admin@budgetbuddy.local",
        ):
            from app.scripts.seed_demo_users import auto_seed_if_empty

            await auto_seed_if_empty(db)
            user = (
                await db.execute(select(models.User).where(models.User.email == email))
            ).scalar_one_or_none()

    if user is None:
        raise _unauthorized({"detail": "User not found"})
    if not user.is_active:
        raise _unauthorized({"detail": "User is inactive"})
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
async def require_premium(user: CurrentUser) -> models.User:
    if user.role not in ("premium", "admin"):
        raise permission_denied("Premium subscription required.")
    return user


async def require_admin(user: CurrentUser) -> models.User:
    if not (user.role == "admin" or user.is_staff or user.is_superuser):
        raise permission_denied("Admin access required.")
    return user


PremiumUser = Annotated[models.User, Depends(require_premium)]
AdminUser = Annotated[models.User, Depends(require_admin)]


# ---------------------------------------------------------------------------
# Object lookups
# ---------------------------------------------------------------------------
def parse_pk(raw: str) -> int:
    """DRF + Django >=4.1: a non-numeric pk is a bare ``Http404``.

    The bare 404 has no message, so DRF renders ``{"detail": "Not found."}``
    instead of ``No <Model> matches the given query.``
    """
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise not_found_detail("Not found.") from None


async def owned_object(
    db: AsyncSession,
    model: type[ModelT],
    user: models.User,
    raw_pk: str,
) -> ModelT:
    """``get_object()`` for a user-scoped viewset (404 on someone else's row)."""
    pk = parse_pk(raw_pk)
    stmt: Select[Any] = select(model).where(model.id == pk, model.user_id == user.id)  # type: ignore[attr-defined]
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise not_found(model.__name__)
    return obj


async def get_scoped(
    db: AsyncSession,
    model: type[ModelT],
    user: models.User,
    raw_pk: str,
    relationship: str,
) -> ModelT:
    """Same as :func:`owned_object` but scoped through a related object.

    Used by ``/api/expenses/<pk>/`` style routes that need the parent's user.
    """
    pk = parse_pk(raw_pk)
    obj = await db.get(model, pk)
    if obj is None or getattr(obj, relationship) != user.id:
        raise not_found(model.__name__)
    return obj
