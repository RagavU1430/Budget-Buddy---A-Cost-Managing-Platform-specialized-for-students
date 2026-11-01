"""DRF PageNumberPagination parity."""

from __future__ import annotations

from typing import Any, Sequence
from urllib.parse import urlencode

from starlette.requests import Request

from app.core.config import settings
from app.core.errors import invalid_page


def _page_url(request: Request, page: int) -> str:
    params = dict(request.query_params)
    params["page"] = str(page)
    base = str(request.base_url).rstrip("/")
    return f"{base}{request.url.path}?{urlencode(params)}"


def paginate(
    request: Request,
    items: Sequence[Any],
    total: int,
    *,
    page_size: int | None = None,
) -> dict[str, Any]:
    size = page_size or settings.PAGE_SIZE
    raw_page = request.query_params.get("page", "1")
    try:
        page = int(raw_page)
    except (TypeError, ValueError):
        raise invalid_page() from None
    if page < 1:
        raise invalid_page()

    num_pages = (total + size - 1) // size
    if num_pages and page > num_pages:
        raise invalid_page()
    if total == 0 and page != 1:
        raise invalid_page()

    return {
        "count": total,
        "next": _page_url(request, page + 1) if page < num_pages else None,
        "previous": _page_url(request, page - 1) if page > 1 else None,
        "results": list(items),
    }
