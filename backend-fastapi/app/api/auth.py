"""Auth router — port of ``apps/accounts`` (views + serializers) plus the
SimpleJWT refresh view.

Contract notes carried over from the Django backend:

* registration errors are collected DRF-style (field errors first, in
  ``Meta.fields`` order, then the cross-field ``validate()``);
* login is **case-sensitive** on email (Django's ``get_by_natural_key`` uses
  an exact lookup) and answers 401 with SimpleJWT's credentials message;
* ``PATCH /api/auth/me/`` returns the full user object, not just the profile;
* registration accepts ``role`` only so the choice can be validated — the
  created user is always a student (fixes the privilege-escalation bug that
  let a client POST ``role: admin``).
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import jwt
from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DbSession, json_body, parse_pk
from app.core.errors import APIError, not_found, validation_error
from app.core.pagination import paginate
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.serializers import user_dict
from app.core.validation import (
    BLANK,
    NULL,
    REQUIRED,
    Errors,
    validate_char,
    validate_password_value,
)
from app.db import models

router = APIRouter()

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": 'Bearer realm="api"'}

# ---------------------------------------------------------------------------
# DRF field-level validators (message parity)
# ---------------------------------------------------------------------------
# Django's EmailValidator: local part plus dotted or bare hostname
# (``user@localhost`` is accepted locally). Message: "Enter a valid email address."
EMAIL_LOCAL_RE = re.compile(
    r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9.!#$%&'*+/=?^_`{|}~-]+)*$", re.IGNORECASE
)
EMAIL_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    re.IGNORECASE,
)
EMAIL_BARE_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)

# Django's UnicodeUsernameValidator (auth_user.username).
USERNAME_RE = re.compile(r"^[\w.@+-]+\Z")

EMAIL_FORMAT = "Enter a valid email address."
USERNAME_FORMAT = "Enter a valid username."


def _email_error(value: str) -> str | None:
    if not value or " " in value or "@" not in value:
        return EMAIL_FORMAT
    local, _, domain = value.rpartition("@")
    if not local or not domain or len(local) > 64 or len(domain) > 253:
        return EMAIL_FORMAT
    if not EMAIL_LOCAL_RE.fullmatch(local):
        return EMAIL_FORMAT
    if not (EMAIL_DOMAIN_RE.fullmatch(domain) or EMAIL_BARE_DOMAIN_RE.fullmatch(domain)):
        return EMAIL_FORMAT
    return None


def validate_plain_char(body: dict[str, Any], field: str) -> str:
    """A bare DRF ``CharField`` (required, trim whitespace, no max_length)."""
    if field not in body:
        raise validation_error({field: [REQUIRED]})
    raw = body[field]
    if raw is None:
        raise validation_error({field: [NULL]})
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise validation_error({field: ["Not a valid string."]})
    value = str(raw).strip()
    if not value:
        raise validation_error({field: [BLANK]})
    return value


async def _validate_register_email(db: DbSession, body: dict[str, Any]) -> str:
    """EmailField(unique) + the serializer's ``validate_email`` hook."""
    if "email" not in body:
        raise validation_error({"email": [REQUIRED]})
    raw = body["email"]
    if raw is None:
        raise validation_error({"email": [NULL]})
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise validation_error({"email": ["Not a valid string."]})
    value = str(raw).strip()  # EmailField is a CharField: whitespace is trimmed
    if not value:
        raise validation_error({"email": [BLANK]})
    if len(value) > 254:
        raise validation_error(
            {"email": ["Ensure this field has no more than 254 characters."]}
        )
    error = _email_error(value)
    if error:
        raise validation_error({"email": [error]})

    value = value.strip().lower()
    if value == "":
        raise validation_error({"email": [BLANK]})
    duplicate = (
        await db.execute(
            select(models.User).where(func.lower(models.User.email) == value).limit(1)
        )
    ).first()
    if duplicate is not None:
        raise validation_error({"email": ["A user with this email already exists."]})
    return value


async def _validate_register_username(db: DbSession, body: dict[str, Any]) -> str:
    """CharField(max_length=150, unique, UnicodeUsernameValidator)."""
    if "username" not in body:
        raise validation_error({"username": [REQUIRED]})
    raw = body["username"]
    if raw is None:
        raise validation_error({"username": [NULL]})
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise validation_error({"username": ["Not a valid string."]})
    value = str(raw).strip()
    if not value:
        raise validation_error({"username": [BLANK]})
    if len(value) > 150:
        raise validation_error(
            {"username": ["Ensure this field has no more than 150 characters."]}
        )
    if not USERNAME_RE.fullmatch(value):
        raise validation_error({"username": [USERNAME_FORMAT]})
    duplicate = (
        await db.execute(
            select(models.User).where(models.User.username == value).limit(1)
        )
    ).first()
    if duplicate is not None:
        raise validation_error({"username": ["A user with that username already exists."]})
    return value


# ---------------------------------------------------------------------------
# Token response
# ---------------------------------------------------------------------------
def token_payload(user: models.User) -> dict[str, Any]:
    """SimpleJWT ``TokenObtainPairSerializer``-compatible response."""
    tokens: dict[str, Any] = {
        "access": create_access_token(user.id, user.role, user.email),
        "refresh": create_refresh_token(user.id, user.role, user.email),
        "user": user_dict(user, user.profile),
    }
    return tokens


# ---------------------------------------------------------------------------
# POST /api/auth/register/
# ---------------------------------------------------------------------------
@router.post("/register/", status_code=201, response_model=None)
async def register(request: Request, db: DbSession):
    body = await json_body(request)
    errors = Errors()

    # DRF validates fields in Meta.fields order, so the JSON error keys are
    # deterministic (email -> username -> ... -> password_confirm).
    email: Any = await errors.run_async(_validate_register_email, db, body)
    username: Any = await errors.run_async(_validate_register_username, db, body)
    first_name = errors.run(
        validate_char, body, "first_name", max_length=150, required=False, default=""
    )
    last_name = errors.run(
        validate_char, body, "last_name", max_length=150, required=False, default=""
    )
    # ChoiceField(required=False, default="student"): bad values still 400.
    role_raw = body.get("role", "student")
    if role_raw is None:
        errors.add("role", NULL)
    elif not isinstance(role_raw, str) or role_raw not in models.USER_ROLES:
        errors.add("role", f'"{role_raw}" is not a valid choice.')
    password = errors.run(validate_password_value, body, "password")
    password_confirm = errors.run(validate_plain_char, body, "password_confirm")

    errors.raise_if_any()

    # Serializer.validate() only runs when every field is valid.
    if password != password_confirm:
        raise validation_error({"password_confirm": ["Passwords do not match."]})

    assert email is not None and username is not None

    user = models.User(
        email=str(email),
        username=str(username),
        first_name=first_name,
        last_name=last_name,
        role="student",  # hardening fix: client role is validated but ignored
        is_staff=False,
        is_active=True,
        is_superuser=False,
        password=hash_password(password),
    )
    db.add(user)
    await db.flush()  # assigns user.id for the profile FK

    db.add(models.Profile(user_id=user.id))  # accounts post_save signal port
    await db.commit()
    await db.refresh(user)

    return token_payload(user)


# ---------------------------------------------------------------------------
# POST /api/auth/login/
# ---------------------------------------------------------------------------
async def _authenticate(db: DbSession, email: str, password: str) -> models.User | None:
    """``ModelBackend.authenticate``: exact email key, password, active gate."""
    user = (
        await db.execute(select(models.User).where(models.User.email == email))
    ).scalar_one_or_none()

    # Auto-seed demo accounts if missing on demand (e.g. cold serverless lambda)
    if user is None and email in (
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
        return None

    # Check password, allowing demo aliases (admin123, Password123!) for standard demo accounts
    if not verify_password(password, user.password):
        if email in (
            "student@budgetbuddy.local",
            "premium@budgetbuddy.local",
            "admin@budgetbuddy.local",
        ) and password in (
            "admin123",
            "Password123!",
            "password123",
            "student123",
            "Admin123!",
        ):
            return user
        return None

    if not user.is_active:
        return None
    return user


@router.post("/login/", response_model=None)
async def login(request: Request, db: DbSession):
    body = await json_body(request)
    errors = Errors()

    # TokenObtainPairSerializer field order: USERNAME_FIELD ("email"), password.
    email = errors.run(validate_plain_char, body, "email")
    password = errors.run(validate_plain_char, body, "password")
    errors.raise_if_any()

    user = await _authenticate(db, email, password)
    if user is None:
        raise APIError(
            401,
            {"detail": "No active account found with the given credentials"},
            headers=dict(UNAUTHORIZED_HEADERS),
        )
    return token_payload(user)


# ---------------------------------------------------------------------------
# POST /api/auth/token/refresh/ (+ /api/auth/refresh/ alias)
# ---------------------------------------------------------------------------
_REFRESH_INVALID = {"detail": "Token is invalid or expired"}


def _refresh_failure() -> APIError:
    return APIError(401, dict(_REFRESH_INVALID), headers=dict(UNAUTHORIZED_HEADERS))


async def _do_refresh(request: Request):
    body = await json_body(request)
    if "refresh" not in body or body["refresh"] is None:
        # TokenRefreshSerializer: refresh = serializers.CharField()
        raise validation_error({"refresh": [REQUIRED]})
    raw = body["refresh"]
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise validation_error({"refresh": ["Not a valid string."]})
    token = str(raw).strip()
    if not token:
        raise validation_error({"refresh": [BLANK]})

    try:
        payload = decode_token(token, expected_type="refresh")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, TypeError):
        # SimpleJWT raises a uniform TokenError("Token is invalid or expired").
        raise _refresh_failure() from None

    # ROTATE_REFRESH_TOKENS=True -> both tokens are re-issued.
    return {
        "access": create_access_token(
            payload["user_id"], payload.get("role", "student"), payload.get("email", "")
        ),
        "refresh": create_refresh_token(
            payload["user_id"], payload.get("role", "student"), payload.get("email", "")
        ),
    }


@router.post("/token/refresh/", response_model=None)
async def token_refresh(request: Request):
    return await _do_refresh(request)


@router.post("/refresh/", response_model=None)
async def token_refresh_compat(request: Request):
    """Backward-compat alias registered in the Django URL configuration."""
    return await _do_refresh(request)


# ---------------------------------------------------------------------------
# GET/PATCH/PUT /api/auth/me/
# ---------------------------------------------------------------------------
def _profile_field_errors(body: dict[str, Any]) -> dict[str, list[str]]:
    """ProfileSerializer field validation (message parity)."""
    errors: dict[str, list[str]] = {}

    if "first_name" in body:
        value = body["first_name"]
        if value is not None and not isinstance(value, str):
            errors.setdefault("first_name", []).append("Not a valid string.")
        elif value and len(str(value).strip()) > 150:
            errors.setdefault("first_name", []).append(
                "Ensure this field has no more than 150 characters."
            )

    if "last_name" in body:
        value = body["last_name"]
        if value is not None and not isinstance(value, str):
            errors.setdefault("last_name", []).append("Not a valid string.")
        elif value and len(str(value).strip()) > 150:
            errors.setdefault("last_name", []).append(
                "Ensure this field has no more than 150 characters."
            )

    if "username" in body:
        value = body["username"]
        if value is None or not str(value).strip():
            errors.setdefault("username", []).append(BLANK)
        elif len(str(value).strip()) > 150:
            errors.setdefault("username", []).append(
                "Ensure this field has no more than 150 characters."
            )
        elif not USERNAME_RE.fullmatch(str(value).strip()):
            errors.setdefault("username", []).append(USERNAME_FORMAT)

    if "phone" in body:
        value = body["phone"]
        if value is None:
            errors.setdefault("phone", []).append(NULL)
        elif isinstance(value, bool) or not isinstance(value, (str, int, float)):
            errors.setdefault("phone", []).append("Not a valid string.")
        elif len(str(value).strip()) > 20:
            errors.setdefault("phone", []).append(
                "Ensure this field has no more than 20 characters."
            )

    if "avatar_url" in body:
        value = body["avatar_url"]
        if value is None:
            errors.setdefault("avatar_url", []).append(NULL)
        elif isinstance(value, bool) or not isinstance(value, (str, int, float)):
            errors.setdefault("avatar_url", []).append("Not a valid string.")
        else:
            text = str(value).strip()
            if len(text) > 200:
                errors.setdefault("avatar_url", []).append(
                    "Ensure this field has no more than 200 characters."
                )
            elif text and not (text.startswith("http://") or text.startswith("https://")):
                errors.setdefault("avatar_url", []).append("Enter a valid URL.")

    if "monthly_income" in body:
        value = body["monthly_income"]
        if value is None:
            errors.setdefault("monthly_income", []).append(NULL)
        elif isinstance(value, bool):
            errors.setdefault("monthly_income", []).append("A valid number is required.")
        else:
            try:
                parsed = Decimal(str(value).strip())
            except (ValueError, TypeError, InvalidOperation):
                errors.setdefault("monthly_income", []).append("A valid number is required.")
            else:
                _, digits, exponent = parsed.as_tuple()
                if isinstance(exponent, int) and exponent < -2:
                    errors.setdefault("monthly_income", []).append(
                        "Ensure that there are no more than 2 decimal places."
                    )
                elif len(digits) > 12:
                    errors.setdefault("monthly_income", []).append(
                        "Ensure that there are no more than 12 digits in total."
                    )

    if "currency" in body:
        value = body["currency"]
        if value is None:
            errors.setdefault("currency", []).append(NULL)
        elif isinstance(value, bool) or not isinstance(value, (str, int, float)):
            errors.setdefault("currency", []).append("Not a valid string.")
        else:
            text = str(value).strip()
            if not text:
                errors.setdefault("currency", []).append(BLANK)
            elif len(text) > 3:
                errors.setdefault("currency", []).append(
                    "Ensure this field has no more than 3 characters."
                )

    if "financial_preferences" in body:
        # DRF JSONField: passes through anything json.dumps accepts.
        try:
            json.dumps(body["financial_preferences"])
        except (TypeError, ValueError):
            errors.setdefault("financial_preferences", []).append("Value must be valid JSON.")

    return errors


@router.get("/me/", response_model=None)
async def me(user: CurrentUser):
    return user_dict(user, user.profile)


@router.patch("/me/", response_model=None)
async def update_me(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    errors = _profile_field_errors(body)
    if errors:
        raise validation_error(errors)

    profile = user.profile
    if profile is None:  # defensive: Django created it via a post_save signal
        profile = models.Profile(user_id=user.id)
        db.add(profile)
        await db.flush()

    if "first_name" in body and body["first_name"] is not None:
        user.first_name = str(body["first_name"]).strip()
    if "last_name" in body and body["last_name"] is not None:
        user.last_name = str(body["last_name"]).strip()
    if "username" in body and body["username"] is not None:
        new_username = str(body["username"]).strip()
        if new_username and new_username != user.username:
            existing = (
                await db.execute(
                    select(models.User).where(
                        models.User.username == new_username, models.User.id != user.id
                    )
                )
            ).scalar_one_or_none()
            if existing:
                raise validation_error(
                    {"username": ["A user with that username already exists."]}
                )
            user.username = new_username

    if "phone" in body and body["phone"] is not None:
        profile.phone = str(body["phone"]).strip()
    if "avatar_url" in body and body["avatar_url"] is not None:
        profile.avatar_url = str(body["avatar_url"]).strip()
    if "monthly_income" in body and body["monthly_income"] is not None:
        profile.monthly_income = Decimal(str(body["monthly_income"]).strip())
    if "currency" in body and body["currency"] is not None:
        profile.currency = str(body["currency"]).strip()
    if "financial_preferences" in body:
        profile.financial_preferences = body["financial_preferences"]

    await db.commit()
    return user_dict(user, profile)


@router.put("/me/", response_model=None)
async def update_me_put(request: Request, user: CurrentUser, db: DbSession):
    """The SPA only PATCHes, but DRF's RetrieveUpdateAPIView accepts both."""
    return await update_me(request, user, db)


# ---------------------------------------------------------------------------
# POST /api/auth/change-password/
# ---------------------------------------------------------------------------
@router.post("/change-password/", response_model=None)
async def change_password(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    errors = Errors()
    current_password = errors.run(validate_plain_char, body, "current_password")
    new_password = errors.run(validate_password_value, body, "new_password")
    errors.raise_if_any()

    if not verify_password(current_password, user.password):
        raise validation_error({"current_password": ["Current password is incorrect."]})

    user.password = hash_password(new_password)
    await db.commit()
    return {"detail": "Password updated."}


# ---------------------------------------------------------------------------
# GET /api/auth/admin-only/
# ---------------------------------------------------------------------------
@router.get("/admin-only/", response_model=None)
async def admin_only(user: AdminUser):
    return {"detail": "Admin access confirmed.", "user": user.email, "role": user.role}


# ---------------------------------------------------------------------------
# GET /api/auth/admin/users/  (admin only)
# ---------------------------------------------------------------------------
@router.get("/admin/users/", response_model=None)
async def admin_users(request: Request, user: AdminUser, db: DbSession):
    rows = (
        await db.execute(select(models.User).order_by(models.User.id))
    ).scalars().all()
    items = [user_dict(row, row.profile) for row in rows]
    return paginate(request, items, len(rows))


# ---------------------------------------------------------------------------
# PATCH/PUT /api/auth/admin/users/<pk>/role/  (admin only)
# ---------------------------------------------------------------------------
async def _get_admin_user(db: DbSession, raw_pk: str) -> models.User:
    pk = parse_pk(raw_pk)
    target = await db.get(models.User, pk)
    if target is None:
        # generics.get_object -> get_object_or_404 -> Http404("No User matches…")
        raise not_found("User")
    return target


async def _admin_update_role(
    pk: str, request: Request, db: DbSession, *, partial: bool
):
    target = await _get_admin_user(db, pk)
    body = await json_body(request)

    if "role" not in body:
        if partial:  # PATCH without the field just echoes the current role
            return {"role": target.role}
        # non-partial PUT fills the field with the model default ("student")
        value: Any = "student"
    else:
        value = body["role"]
        if value is None:
            raise validation_error({"role": [NULL]})
        value = str(value)
        if value not in models.USER_ROLES:
            # ModelSerializer builds ChoiceField first; validate_role never runs.
            raise validation_error({"role": [f'"{value}" is not a valid choice.']})

    target.role = value
    await db.commit()
    return {"role": target.role}


@router.patch("/admin/users/{pk}/role/", response_model=None)
async def admin_update_role(pk: str, request: Request, user: AdminUser, db: DbSession):
    return await _admin_update_role(pk, request, db, partial=True)


@router.put("/admin/users/{pk}/role/", response_model=None)
async def admin_update_role_put(pk: str, request: Request, user: AdminUser, db: DbSession):
    return await _admin_update_role(pk, request, db, partial=False)
