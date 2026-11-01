"""DRF-compatible error primitives.

Every endpoint answers with the exact JSON envelope the Django/DRF backend
produced, so the React client needs no changes:

    {"detail": "No Expense matches the given query."}
    {"<field>": ["<message>"]}
    {"non_field_errors": ["<message>"]}
"""

from __future__ import annotations

from typing import Any

AUTH_REQUIRED = {"detail": "Authentication credentials were not provided."}


class APIError(Exception):
    """An error that is rendered as an exact HTTP JSON body."""

    def __init__(
        self,
        status_code: int,
        body: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(str(body))
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}


def validation_error(errors: dict[str, Any]) -> APIError:
    return APIError(400, errors)


def not_found(model_name: str) -> APIError:
    return not_found_detail(f"No {model_name} matches the given query.")


def not_found_detail(message: str) -> APIError:
    return APIError(404, {"detail": message})


def invalid_page() -> APIError:
    return not_found_detail("Invalid page.")


def permission_denied(message: str) -> APIError:
    return APIError(403, {"detail": message})


def bad_request_detail(message: str) -> APIError:
    return APIError(400, {"detail": message})


def bad_request(body: Any) -> APIError:
    return APIError(400, body)
