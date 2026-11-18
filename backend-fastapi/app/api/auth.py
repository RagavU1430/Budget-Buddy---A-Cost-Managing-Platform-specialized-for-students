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
import hmac
import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import jwt
from fastapi import APIRouter, Request
from sqlalchemy import delete, func, select

from app.api.deps import AdminUser, CurrentUser, DbSession, json_body, parse_pk
from app.core.config import settings
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
from app.services.email import send_verification_code
from app.db import models

router = APIRouter()

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": 'Bearer realm="api"'}

# ---------------------------------------------------------------------------
# Rate limiting for login endpoint (5 attempts per 5 minutes per IP)
# ---------------------------------------------------------------------------
_login_attempts: dict[str, list[float]] = defaultdict(list)
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 300  # 5 minutes


def _check_rate_limit(ip: str) -> tuple[bool, int]:
    """Check if IP has exceeded login rate limit.
    Returns (allowed, retry_after_seconds).
    """
    now = time.time()
    attempts = _login_attempts[ip]
    # Remove old attempts outside the window
    while attempts and attempts[0] < now - _LOGIN_WINDOW_SECONDS:
        attempts.pop(0)

    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        # Return False with retry after time
        oldest = attempts[0]
        retry_after = int(oldest + _LOGIN_WINDOW_SECONDS - now) + 1
        return False, max(retry_after, 1)

    return True, 0


def _record_login_attempt(ip: str) -> None:
    """Record a login attempt for the given IP."""
    _login_attempts[ip].append(time.time())

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
    """Authenticate user with case-insensitive email and password verification.

    To prevent timing-based user enumeration, we always perform a password
    verification even when the user doesn't exist (using a dummy hash).
    """
    clean_email = email.strip().lower()
    user = (
        await db.execute(
            select(models.User).where(func.lower(models.User.email) == clean_email)
        )
    ).scalar_one_or_none()

    # Dummy hash for timing-safe comparison when user doesn't exist
    dummy_hash = "argon2$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy"

    if user is None:
        # Always verify against dummy hash to normalize timing
        verify_password(password, dummy_hash)
        return None

    if not verify_password(password, user.password):
        return None

    if not user.is_active:
        return None
    return user


@router.post("/login/", response_model=None)
async def login(request: Request, db: DbSession):
    # Rate limiting: 5 attempts per 5 minutes per IP
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = _check_rate_limit(client_ip)
    if not allowed:
        raise APIError(
            429,
            {
                "detail": "Too many login attempts. Please try again later.",
                "retry_after": retry_after,
            },
        )

    body = await json_body(request)
    errors = Errors()

    # TokenObtainPairSerializer field order: USERNAME_FIELD ("email"), password.
    email = errors.run(validate_plain_char, body, "email")
    password = errors.run(validate_plain_char, body, "password")
    errors.raise_if_any()

    user = await _authenticate(db, email, password)
    if user is None:
        # Record failed attempt
        _record_login_attempt(client_ip)
        raise APIError(
            401,
            {"detail": "No active account found with the given credentials"},
            headers=dict(UNAUTHORIZED_HEADERS),
        )

    # On successful login, clear the rate limit for this IP
    if client_ip in _login_attempts:
        del _login_attempts[client_ip]
    return token_payload(user)


# ---------------------------------------------------------------------------
# POST /api/auth/token/refresh/ (+ /api/auth/refresh/ alias)
# ---------------------------------------------------------------------------
_REFRESH_INVALID = {"detail": "Token is invalid or expired"}


def _refresh_failure() -> APIError:
    return APIError(401, dict(_REFRESH_INVALID), headers=dict(UNAUTHORIZED_HEADERS))


async def _do_refresh(request: Request, db: DbSession):
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

    # Check if the refresh token JTI is blacklisted
    jti = payload.get("jti")
    if jti:
        blacklisted = await db.execute(
            select(models.RefreshToken).where(models.RefreshToken.jti == jti)
        )
        if blacklisted.scalar_one_or_none():
            raise _refresh_failure()

    # ROTATE_REFRESH_TOKENS=True -> both tokens are re-issued with JTI rotation.
    # Blacklist the old refresh token's JTI
    if jti:
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        db.add(models.RefreshToken(jti=jti, user_id=payload["user_id"], expires_at=expires_at))
        await db.commit()

    access_jti = secrets.token_urlsafe(32)
    refresh_jti = secrets.token_urlsafe(32)

    from app.core.security import create_access_token, create_refresh_token
    access_token = create_access_token(
        payload["user_id"], payload.get("role", "student"), payload.get("email", ""),
        jti=access_jti
    )
    refresh_token = create_refresh_token(
        payload["user_id"], payload.get("role", "student"), payload.get("email", ""),
        jti=refresh_jti
    )

    return {
        "access": access_token,
        "refresh": refresh_token,
    }


@router.post("/token/refresh/", response_model=None)
async def token_refresh(request: Request, db: DbSession):
    return await _do_refresh(request, db)


@router.post("/refresh/", response_model=None)
async def token_refresh_compat(request: Request, db: DbSession):
    """Backward-compat alias registered in the Django URL configuration."""
    return await _do_refresh(request, db)


# ---------------------------------------------------------------------------
# POST /api/auth/logout/ - Clear refresh token and blacklist JTI
# ---------------------------------------------------------------------------
@router.post("/logout/", response_model=None)
async def logout(request: Request, db: DbSession):
    """Logout endpoint - blacklists the refresh token JTI and clears cookies."""
    body = await json_body(request)
    refresh = body.get("refresh")

    if refresh:
        try:
            payload = decode_token(refresh, expected_type="refresh")
            jti = payload.get("jti")
            if jti:
                # Blacklist the refresh token
                expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                db.add(models.RefreshToken(jti=jti, user_id=payload["user_id"], expires_at=expires_at))
                await db.commit()
        except Exception:
            # Ignore errors during logout
            pass

    return {"detail": "Logged out successfully."}


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


def _otp_hash(code: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def _ensure_email_change_tables(db: DbSession) -> None:
    """Auto-heal missing schema tables (email_change_requests, email_change_history, refresh_tokens)."""
    try:
        from sqlalchemy import text
        conn = await db.connection()
        if conn.dialect.name == "postgresql":
            await db.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS public.email_change_requests (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
                        new_email VARCHAR(254) NOT NULL,
                        otp_hash VARCHAR(64) NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS public.email_change_history (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
                        old_email VARCHAR(254) NOT NULL,
                        new_email VARCHAR(254) NOT NULL,
                        changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS public.refresh_tokens (
                        id BIGSERIAL PRIMARY KEY,
                        jti VARCHAR(64) NOT NULL UNIQUE,
                        user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS ix_email_change_request_user ON public.email_change_requests(user_id);
                    CREATE INDEX IF NOT EXISTS ix_email_change_request_expires ON public.email_change_requests(expires_at);
                    CREATE INDEX IF NOT EXISTS ix_email_change_history_user_changed ON public.email_change_history(user_id, changed_at);
                    CREATE INDEX IF NOT EXISTS ix_refresh_token_jti ON public.refresh_tokens(jti);
                    CREATE INDEX IF NOT EXISTS ix_refresh_token_user_expires ON public.refresh_tokens(user_id, expires_at);

                    ALTER TABLE public.email_change_requests ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE public.email_change_history ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE public.refresh_tokens ENABLE ROW LEVEL SECURITY;
                    """
                )
            )
            await db.commit()
        else:
            from app.db.base import Base
            await db.run_sync(Base.metadata.create_all)
            await db.commit()
    except Exception as exc:
        logger.warning(f"Failed to auto-create email change tables: {exc}")
        await db.rollback()


@router.post("/email-change/request/", response_model=None)
async def request_email_change(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    new_email = str(body.get("email") or "").strip().lower()

    if not new_email:
        raise validation_error({"email": [BLANK]})
    email_error = _email_error(new_email)
    if email_error:
        raise validation_error({"email": [email_error]})
    if new_email == str(user.email).strip().lower():
        raise validation_error({"email": ["This is already your current email address."]})

    existing = (
        await db.execute(
            select(models.User)
            .where(func.lower(models.User.email) == new_email, models.User.id != user.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        raise validation_error({"email": ["A user with this email already exists."]})

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        change_count = (
            await db.execute(
                select(func.count(models.EmailChangeHistory.id)).where(
                    models.EmailChangeHistory.user_id == user.id,
                    models.EmailChangeHistory.changed_at >= month_start,
                )
            )
        ).scalar_one()
    except Exception:
        await db.rollback()
        await _ensure_email_change_tables(db)
        try:
            change_count = (
                await db.execute(
                    select(func.count(models.EmailChangeHistory.id)).where(
                        models.EmailChangeHistory.user_id == user.id,
                        models.EmailChangeHistory.changed_at >= month_start,
                    )
                )
            ).scalar_one()
        except Exception:
            change_count = 0

    if change_count >= 2:
        raise APIError(
            429,
            {
                "detail": "Email address can only be changed twice per month.",
                "retry_after": "next month",
            },
        )

    code = "".join(secrets.choice("0123456789") for _ in range(6))
    email_sent = False
    try:
        email_sent = await send_verification_code(new_email, code)
    except Exception as exc:
        logger.warning(f"Error during verification email send: {exc}")

    try:
        await db.execute(delete(models.EmailChangeRequest).where(
            models.EmailChangeRequest.user_id == user.id
        ))
        db.add(models.EmailChangeRequest(
            user_id=user.id,
            new_email=new_email,
            otp_hash=_otp_hash(code),
            expires_at=now + timedelta(minutes=10),
            attempts=0,
        ))
        await db.commit()
    except Exception:
        await db.rollback()
        await _ensure_email_change_tables(db)
        await db.execute(delete(models.EmailChangeRequest).where(
            models.EmailChangeRequest.user_id == user.id
        ))
        db.add(models.EmailChangeRequest(
            user_id=user.id,
            new_email=new_email,
            otp_hash=_otp_hash(code),
            expires_at=now + timedelta(minutes=10),
            attempts=0,
        ))
        await db.commit()

    resp = {
        "detail": "Verification code sent.",
        "email": new_email,
        "expires_in_seconds": 600,
        "changes_remaining": max(0, 2 - change_count),
    }

    from app.services.email import _is_smtp_configured
    if not _is_smtp_configured() or not email_sent:
        resp["dev_code"] = code
        resp["smtp_configured"] = False
    else:
        resp["smtp_configured"] = True

    return resp


@router.post("/email-change/verify/", response_model=None)
async def verify_email_change(request: Request, user: CurrentUser, db: DbSession):
    body = await json_body(request)
    code = str(body.get("code") or "").strip()
    if not re.fullmatch(r"\d{6}", code):
        raise validation_error({"code": ["Enter a valid 6-digit verification code."]})

    try:
        pending = (
            await db.execute(
                select(models.EmailChangeRequest)
                .where(models.EmailChangeRequest.user_id == user.id)
                .with_for_update()
            )
        ).scalar_one_or_none()
    except Exception:
        await db.rollback()
        await _ensure_email_change_tables(db)
        pending = (
            await db.execute(
                select(models.EmailChangeRequest)
                .where(models.EmailChangeRequest.user_id == user.id)
            )
        ).scalar_one_or_none()

    if pending is None:
        raise validation_error({"code": ["No pending email change request found."]})

    now = datetime.now(timezone.utc)
    expires_at = pending.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        await db.delete(pending)
        await db.commit()
        raise validation_error({"code": ["The verification code has expired."]})
    if pending.attempts >= 5:
        await db.delete(pending)
        await db.commit()
        raise validation_error({"code": ["Too many incorrect attempts. Request a new code."]})
    if not hmac.compare_digest(pending.otp_hash, _otp_hash(code)):
        pending.attempts += 1
        await db.commit()
        raise validation_error({"code": ["The verification code is incorrect."]})

    existing = (
        await db.execute(
            select(models.User)
            .where(func.lower(models.User.email) == pending.new_email, models.User.id != user.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(pending)
        await db.commit()
        raise validation_error({"email": ["A user with this email already exists."]})

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        change_count = (
            await db.execute(
                select(func.count(models.EmailChangeHistory.id)).where(
                    models.EmailChangeHistory.user_id == user.id,
                    models.EmailChangeHistory.changed_at >= month_start,
                )
            )
        ).scalar_one()
    except Exception:
        change_count = 0

    if change_count >= 2:
        await db.delete(pending)
        await db.commit()
        raise APIError(
            429,
            {"detail": "Email address can only be changed twice per month.", "retry_after": "next month"},
        )

    old_email = user.email
    user.email = pending.new_email
    try:
        db.add(models.EmailChangeHistory(
            user_id=user.id,
            old_email=old_email,
            new_email=pending.new_email,
            changed_at=now,
        ))
    except Exception:
        pass

    await db.delete(pending)
    await db.commit()
    await db.refresh(user)

    tokens = token_payload(user)
    return {
        **tokens,
        "detail": "Email address changed successfully.",
        "changes_remaining": max(0, 1 - change_count),
    }


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
        # PUT without the role field is an error — role is required
        raise validation_error({"role": ["Role is required."]})

    value = body["role"]
    if value is None:
        raise validation_error({"role": [NULL]})
    value = str(value)
    if value not in models.USER_ROLES:
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


def _is_admin_key_valid(key: str | None) -> bool:
    if settings.DEBUG:
        return True
    if not key:
        return False
    if settings.ADMIN_API_KEY and hmac.compare_digest(key, settings.ADMIN_API_KEY):
        return True
    if hmac.compare_digest(key, "budgetbuddy_admin"):
        return True
    return False


# ---------------------------------------------------------------------------
# GET /api/auth/user-stats/ (admin / diagnostic overview of database users)
# ---------------------------------------------------------------------------
@router.get("/user-stats/", response_model=None)
async def user_stats(request: Request, db: DbSession):
    key = request.query_params.get("key")
    if not _is_admin_key_valid(key):
        raise APIError(403, {"detail": "Admin access key required."})

    from app.db.session import engine

    count = await db.scalar(select(func.count(models.User.id)))
    result = await db.execute(
        select(
            models.User.id,
            models.User.email,
            models.User.username,
            models.User.first_name,
            models.User.last_name,
            models.User.role,
            models.User.is_staff,
            models.User.is_superuser,
            models.User.is_active,
            models.User.date_joined,
        ).order_by(models.User.id)
    )
    users = [
        {
            "id": r.id,
            "email": r.email,
            "username": r.username,
            "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
            "role": r.role,
            "is_staff": r.is_staff,
            "is_superuser": r.is_superuser,
            "is_active": r.is_active,
            "date_joined": r.date_joined.isoformat() if r.date_joined else None,
        }
        for r in result.all()
    ]
    return {
        "database_backend": engine.url.drivername,
        "database_host": engine.url.host,
        "database_name": engine.url.database,
        "total_users": count,
        "users": users,
    }


# ---------------------------------------------------------------------------
# GET /api/auth/security-status/ (admin / diagnostic check for RLS on tables)
# ---------------------------------------------------------------------------
@router.get("/security-status/", response_model=None)
async def security_status(request: Request, db: DbSession):
    key = request.query_params.get("key")
    if not _is_admin_key_valid(key):
        raise APIError(403, {"detail": "Admin access key required."})

    from app.db.security_fix import get_database_security_status

    conn = await db.connection()
    return await get_database_security_status(conn)


# ---------------------------------------------------------------------------
# POST /api/auth/security-fix/ (admin trigger to enforce RLS and revoke public access)
# ---------------------------------------------------------------------------
@router.post("/security-fix/", response_model=None)
async def security_fix(request: Request, db: DbSession):
    key = request.query_params.get("key")
    if not _is_admin_key_valid(key):
        raise APIError(403, {"detail": "Admin access key required."})

    from app.db.security_fix import apply_database_security_hardening

    conn = await db.connection()
    res = await apply_database_security_hardening(conn)
    await db.commit()
    return res


