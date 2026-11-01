"""Reports router — port of ``apps/reports`` (ReportViewSet).

Endpoints:
- GET  /api/reports/
- POST /api/reports/
- POST /api/reports/generate/
- GET  /api/reports/{pk}/
- GET  /api/reports/{pk}/download/
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import Response as RawResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, PremiumUser, json_body, owned_object
from app.core.errors import bad_request, bad_request_detail, not_found_detail
from app.core.serializers import report_dict
from app.db import models
from app.services.reports import build_report
from app.services.storage import download_filename, read_report, save_report

router = APIRouter()


def _get_download_url(request: Request, report_id: int) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/reports/{report_id}/download/"


@router.get("/reports/", response_model=None)
async def list_reports(request: Request, user: PremiumUser, db: DbSession):
    """List generated reports for the current user."""
    stmt = (
        select(models.Report)
        .where(models.Report.user_id == user.id)
        .order_by(models.Report.generated_at.desc())
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()
    return [report_dict(r, _get_download_url(request, r.id)) for r in reports]


@router.post("/reports/", status_code=201, response_model=None)
@router.post("/reports/generate/", status_code=201, response_model=None)
async def create_report(
    request: Request,
    user: PremiumUser,
    db: DbSession,
):
    """Generate a report for the specified month."""
    body = await json_body(request)
    raw_month = (body.get("month") or "").strip()
    try:
        month_str = raw_month + "-01" if len(raw_month) == 7 else raw_month
        month = date.fromisoformat(month_str)
    except (ValueError, TypeError):
        raise bad_request({"month": "Use YYYY-MM or YYYY-MM-DD."}) from None

    report_type = body.get("report_type", "monthly")
    file_format = body.get("file_format", "pdf")

    if report_type not in models.REPORT_TYPES or file_format not in models.REPORT_FORMATS:
        raise bad_request_detail("Invalid report type or format.")

    filename, content, summary = await build_report(
        db, user, month, report_type, file_format
    )

    storage_key = await save_report(filename, content)

    report = models.Report(
        user_id=user.id,
        month=month,
        report_type=report_type,
        file_format=file_format,
        file=storage_key,
        summary=summary,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report_dict(report, _get_download_url(request, report.id))


@router.get("/reports/{pk}/", response_model=None)
async def get_report_detail(request: Request, pk: str, user: PremiumUser, db: DbSession):
    """Retrieve details of a specific report."""
    report = await owned_object(db, models.Report, user, pk)
    return report_dict(report, _get_download_url(request, report.id))


@router.get("/reports/{pk}/download/", response_model=None)
async def download_report_file(pk: str, user: PremiumUser, db: DbSession):
    """Download the generated report file."""
    report = await owned_object(db, models.Report, user, pk)
    if not report.file:
        raise not_found_detail("Report file is unavailable.")

    try:
        content = await read_report(report.file)
    except Exception:
        raise not_found_detail("Report file is unavailable.") from None

    filename = download_filename(report.file)
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if report.file_format == "excel"
        else "application/pdf"
    )

    return RawResponse(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
