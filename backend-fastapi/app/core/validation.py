"""Field level validation with DRF-identical messages.

These helpers are intentionally explicit rather than leaning on Pydantic's
messages, because the frontend surfaces the DRF strings verbatim.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

from app.core.errors import APIError, validation_error

MISSING = object()

REQUIRED = "This field is required."
BLANK = "This field may not be blank."
NULL = "This field may not be null."
NOT_A_NUMBER = "A valid number is required."
DATE_FORMAT = "Date has wrong format. Use one of these formats instead: YYYY-MM-DD."
BOOLEAN = "Must be a valid boolean."


def _add(errors: dict[str, Any], field: str, message: str) -> None:
    errors.setdefault(field, []).append(message)


def _present(data: Mapping[str, Any], field: str) -> bool:
    return field in data


def validate_char(
    data: Mapping[str, Any],
    field: str,
    *,
    max_length: int,
    required: bool = True,
    allow_blank: bool = False,
    default: Any = MISSING,
) -> str:
    """CharField semantics (required, no blank by default)."""
    if not _present(data, field):
        if default is not MISSING:
            return default
        if required:
            raise validation_error({field: [REQUIRED]})
        return "" if not allow_blank else ""

    value = data[field]
    if value is None:
        raise validation_error({field: [NULL]})
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise validation_error({field: ["Not a valid string."]})
    text = str(value).strip() if isinstance(value, str) else str(value)
    if not text:
        if allow_blank:
            return ""
        raise validation_error({field: [BLANK]})
    if len(text) > max_length:
        raise validation_error(
            {field: [f"Ensure this field has no more than {max_length} characters."]}
        )
    return text


def validate_text(
    data: Mapping[str, Any],
    field: str,
    *,
    required: bool = False,
    default: str = "",
) -> str:
    """TextField(blank=True, default="") semantics."""
    if not _present(data, field):
        if required:
            raise validation_error({field: [REQUIRED]})
        return default
    value = data[field]
    if value is None:
        raise validation_error({field: [NULL]})
    if not isinstance(value, str):
        return str(value)
    return value


def validate_decimal(
    data: Mapping[str, Any],
    field: str,
    *,
    max_digits: int = 12,
    decimal_places: int = 2,
    required: bool = True,
    default: Decimal | object = MISSING,
) -> Decimal:
    if not _present(data, field):
        if default is not MISSING:
            return default  # type: ignore[return-value]
        if required:
            raise validation_error({field: [REQUIRED]})
        return Decimal("0")

    raw = data[field]
    if raw is None:
        raise validation_error({field: [NULL]})
    if isinstance(raw, bool):
        raise validation_error({field: [NOT_A_NUMBER]})
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise validation_error({field: [NOT_A_NUMBER]}) from None
    if not value.is_finite():
        raise validation_error({field: [NOT_A_NUMBER]})

    _, digits, exponent = value.as_tuple()
    if isinstance(exponent, int) and exponent < -decimal_places:
        raise validation_error(
            {field: [f"Ensure that there are no more than {decimal_places} decimal places."]}
        )
    if len(digits) > max_digits:
        raise validation_error(
            {field: [f"Ensure that there are no more than {max_digits} digits in total."]}
        )
    return value


def validate_int(
    data: Mapping[str, Any],
    field: str,
    *,
    required: bool = True,
    default: Any = MISSING,
    min_value: int | None = None,
) -> int:
    if not _present(data, field):
        if default is not MISSING:
            return default
        if required:
            raise validation_error({field: [REQUIRED]})
        return 0
    raw = data[field]
    if raw is None:
        raise validation_error({field: [NULL]})
    try:
        if isinstance(raw, bool):
            raise ValueError
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise validation_error({field: ["A valid integer is required."]}) from None
    if min_value is not None and value < min_value:
        raise validation_error(
            {field: [f"Ensure this value is greater than or equal to {min_value}."]}
        )
    return value


def validate_date(
    data: Mapping[str, Any],
    field: str,
    *,
    required: bool = True,
    allow_null: bool = False,
    default: Any = MISSING,
) -> date | None:
    if not _present(data, field):
        if default is not MISSING:
            return default  # type: ignore[return-value]
        if required:
            raise validation_error({field: [REQUIRED]})
        return None
    raw = data[field]
    if raw is None:
        if allow_null:
            return None
        raise validation_error({field: [NULL]})
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw).strip())
    except (TypeError, ValueError):
        raise validation_error({field: [DATE_FORMAT]}) from None


def validate_choice(
    data: Mapping[str, Any],
    field: str,
    choices: Iterable[str],
    *,
    required: bool = True,
    default: Any = MISSING,
) -> str:
    allowed = list(choices)
    if not _present(data, field):
        if default is not MISSING:
            return default  # type: ignore[return-value]
        if required:
            raise validation_error({field: [REQUIRED]})
        return allowed[0]
    raw = data[field]
    if raw is None:
        raise validation_error({field: [NULL]})
    value = str(raw)
    if value not in allowed:
        raise validation_error({field: [f'"{value}" is not a valid choice.']})
    return value


def validate_boolean(
    data: Mapping[str, Any],
    field: str,
    *,
    required: bool = True,
    default: Any = MISSING,
) -> bool:
    if not _present(data, field):
        if default is not MISSING:
            return default  # type: ignore[return-value]
        if required:
            raise validation_error({field: [REQUIRED]})
        return False
    raw = data[field]
    if raw is None:
        raise validation_error({field: [NULL]})
    if isinstance(raw, bool):
        return raw
    if raw in (1, "1", "true", "True", "TRUE"):
        return True
    if raw in (0, "0", "false", "False", "FALSE"):
        return False
    raise validation_error({field: [BOOLEAN]})


class Errors:
    """DRF's ``to_internal_value`` accumulator.

    DRF validates every field before raising, so a request with three bad
    fields answers with three messages at once. Each validator above raises
    as soon as it finds a problem, so the routes funnel calls through
    :meth:`run` to collect them instead::

        errors = Errors()
        email = errors.run(validate_email, data)
        username = errors.run(validate_char, data, "username", max_length=150)
        errors.raise_if_any()

    Cross-field checks belong in :meth:`add` (or :meth:`merge`) after
    ``raise_if_any()``, mirroring DRF's ``validate()`` running only once
    every field is valid.
    """

    def __init__(self) -> None:
        self.errors: dict[str, Any] = {}

    # -- collection ---------------------------------------------------------
    def add(self, field: str, message: Any) -> None:
        _add(self.errors, field, message)

    def merge(self, body: Mapping[str, Any]) -> None:
        """Merge a whole ``{"field": [messages]}`` envelope (a validate() body)."""
        for field, messages in body.items():
            if isinstance(messages, list):
                for message in messages:
                    _add(self.errors, field, message)
            else:
                _add(self.errors, field, messages)

    def non_field(self, message: str) -> None:
        _add(self.errors, "non_field_errors", message)

    def run(self, validator: Any, /, *args: Any, **kwargs: Any) -> Any:
        """Call ``validator``; on a 400 validation body keep going.

        Returns :data:`MISSING` when the validator failed. The caller must
        call :meth:`raise_if_any` before using the value, which is why the
        placeholder never reaches a client.
        """
        try:
            return validator(*args, **kwargs)
        except APIError as exc:
            if exc.status_code != 400 or not isinstance(exc.body, dict):
                raise
            self.merge(exc.body)
            return MISSING

    async def run_async(self, validator: Any, /, *args: Any, **kwargs: Any) -> Any:
        """Async variant of :meth:`run` for coroutine validators."""
        try:
            return await validator(*args, **kwargs)
        except APIError as exc:
            if exc.status_code != 400 or not isinstance(exc.body, dict):
                raise
            self.merge(exc.body)
            return MISSING

    # -- reporting ----------------------------------------------------------
    def __bool__(self) -> bool:
        return bool(self.errors)

    def raise_if_any(self) -> None:
        if self.errors:
            raise validation_error(self.errors)


# ---------------------------------------------------------------------------
# Django AUTH_PASSWORD_VALIDATORS parity
# ---------------------------------------------------------------------------
# Django reads a 20 000 entry gzipped list; shipping that is pointless here,
# so this is the common-password subset that actually shows up in practice
# plus every obviously weak pattern a student app sees.
COMMON_PASSWORDS = frozenset(
    {
        "123456", "123456789", "12345678", "1234567", "12345", "1234567890",
        "password", "password1", "password12", "password123", "passw0rd",
        "qwerty", "qwerty123", "qwertyuiop", "abc123", "abcd1234", "abcdef",
        "111111", "000000", "121212", "123123", "123321", "112233", "654321",
        "iloveyou", "admin", "admin123", "administrator", "root", "toor",
        "letmein", "welcome", "welcome1", "welcome123", "monkey", "dragon",
        "sunshine", "princess", "football", "baseball", "basketball",
        "master", "shadow", "superman", "batman", "trustno1", "hello",
        "hello123", "test", "test123", "testing", "guest", "login",
        "changeme", "secret", "default", "access", "starwars", "whatever",
        "freedom", "computer", "internet", "samsung", "google", "michael",
        "jennifer", "jordan", "harley", "ranger", "buster", "soccer",
        "hockey", "killer", "george", "charlie", "andrew", "michelle",
        "love", "lovely", "mypassword", "pass", "pass123", "pass1234",
        "student", "student1", "student123", "college", "school", "india",
        "india123", "chennai", "mumbai", "budgetbuddy", "budget", "money",
        "qazwsx", "zaq12wsx", "asdfgh", "asdfghjkl", "zxcvbnm", "1q2w3e4r",
        "1qaz2wsx", "q1w2e3r4", "aa123456", "aaaaaa", "123qwe", "1234qwer",
    }
)

PASSWORD_TOO_SHORT = "This password is too short. It must contain at least {min_length} characters."
PASSWORD_TOO_COMMON = "This password is too common."
PASSWORD_ENTIRELY_NUMERIC = "This password is entirely numeric."


def password_errors(password: str, *, min_length: int = 8) -> list[str]:
    """Django's ``validate_password`` with ``user=None``.

    ``UserAttributeSimilarityValidator`` short-circuits when no user is
    passed, which is exactly what ``validators=[validate_password]`` does
    in the Django serializers — so similarity is never checked there and is
    not checked here either.
    """
    messages: list[str] = []
    if len(password) < min_length:
        messages.append(PASSWORD_TOO_SHORT.format(min_length=min_length))
    if password.lower() in COMMON_PASSWORDS:
        messages.append(PASSWORD_TOO_COMMON)
    if password.isdigit():
        messages.append(PASSWORD_ENTIRELY_NUMERIC)
    return messages


def validate_password_value(
    data: Mapping[str, Any],
    field: str,
    *,
    required: bool = True,
    min_length: int = 8,
) -> str:
    """CharField (no max_length) + ``validate_password``."""
    if not _present(data, field):
        if required:
            raise validation_error({field: [REQUIRED]})
        return ""
    raw = data[field]
    if raw is None:
        raise validation_error({field: [NULL]})
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise validation_error({field: ["Not a valid string."]})
    # DRF CharField defaults to trim_whitespace=True.
    value = str(raw).strip()
    if not value:
        raise validation_error({field: [BLANK]})
    messages = password_errors(value, min_length=min_length)
    if messages:
        raise validation_error({field: messages})
    return value


def validate_url(
    data: Mapping[str, Any],
    field: str,
    *,
    required: bool = False,
    allow_blank: bool = True,
    max_length: int = 200,
) -> str:
    if not _present(data, field):
        if required:
            raise validation_error({field: [REQUIRED]})
        return ""
    raw = data[field]
    if raw is None:
        raise validation_error({field: [NULL]})
    value = str(raw).strip()
    if not value:
        if allow_blank:
            return ""
        raise validation_error({field: [BLANK]})
    if len(value) > max_length:
        raise validation_error(
            {field: [f"Ensure this field has no more than {max_length} characters."]}
        )
    if not (value.startswith("http://") or value.startswith("https://")):
        raise validation_error({field: ["Enter a valid URL."]})
    return value
