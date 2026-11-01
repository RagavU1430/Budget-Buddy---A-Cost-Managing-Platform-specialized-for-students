"""Password hashing and JWT issuance.

Passwords written by the Django backend are `pbkdf2_sha256$<iterations>$<salt>$<b64>`;
they must keep verifying after the cutover. New passwords are stored in the
Django-compatible Argon2 form (`argon2$argon2id$...`).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 1_200_000  # Django 5.2 default
ARGON2_PREFIX = "argon2$"

_argon2 = PasswordHasher()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a new password with Argon2 in a Django-readable envelope."""
    return ARGON2_PREFIX + _argon2.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    if not encoded:
        return False
    if encoded.startswith(ARGON2_PREFIX):
        try:
            return _argon2.verify(encoded[len(ARGON2_PREFIX):], password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    if encoded.startswith(ALGORITHM + "$"):
        try:
            _, iterations, salt, digest = encoded.split("$", 3)
            expected = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            )
            return hmac.compare_digest(
                base64.b64encode(expected).decode("ascii"), digest
            )
        except (ValueError, TypeError):
            return False
    return False


def needs_rehash(encoded: str) -> bool:
    """Django's `needs_update` equivalent — old PBKDF2 hashes move to Argon2."""
    return not encoded.startswith(ARGON2_PREFIX)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, role: str, email: str) -> str:
    now = _now()
    payload = {
        "token_type": "access",
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
        "iat": now,
        "jti": uuid.uuid4().hex,
        "user_id": user_id,
        "role": role,
        "email": email,
    }
    return _encode(payload)


def create_refresh_token(user_id: int, role: str, email: str) -> str:
    now = _now()
    payload = {
        "token_type": "refresh",
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        "iat": now,
        "jti": uuid.uuid4().hex,
        "user_id": user_id,
        "role": role,
        "email": email,
    }
    return _encode(payload)


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a token. Raises jwt exceptions on failure."""
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_aud": False},
    )
    if expected_type is not None and payload.get("token_type") != expected_type:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


def token_pair(user_id: int, role: str, email: str) -> dict[str, str]:
    return {
        "access": create_access_token(user_id, role, email),
        "refresh": create_refresh_token(user_id, role, email),
    }


def new_salt() -> str:
    return secrets.token_urlsafe(12)
