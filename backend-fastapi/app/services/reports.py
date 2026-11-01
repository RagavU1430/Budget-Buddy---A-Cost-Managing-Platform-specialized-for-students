"""Report generation — a port of ``apps/reports/generator.py``.

The files are byte-for-byte equivalent in *content* to the Django output:

* Excel: rows ``["BudgetBuddy report", <month>]``, ``["Income", <total>]``,
  ``["Expenses", <total>]``, then one ``[<category>, <total>]`` row per category.
* PDF: letter page, title at ``(72, 750)``, income at ``720``, expenses at
  ``700``, category rows from ``680`` stepping down 20 points.

Totals are SQL ``SUM`` aggregates rendered with ``str()``, matching Django's
``str(aggregate or 0)`` (so an empty month is ``"0"`` and money keeps its two
decimal places, e.g. ``"1250.00"``).

One deliberate correction: Django's ``values("category").annotate(Sum(...))``
is affected by ``Expense.Meta.ordering`` (the ordering columns leak into the
``GROUP BY``), so its category totals could show only a single bucket. This
implementation returns the intended per-category sum, ordered by category for
a stable file layout.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.services.notifications import month_bounds


def _render_excel(month: date, summary: dict[str, Any]) -> bytes:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["BudgetBuddy report", month.isoformat()])
    sheet.append(["Income", summary["income"]])
    sheet.append(["Expenses", summary["expenses"]])
    for category, total in summary["categories"].items():
        sheet.append([category, total])

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _render_pdf(month: date, report_type: str, summary: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter)
    pdf.drawString(72, 750, f"BudgetBuddy {report_type.title()} Report - {month:%B %Y}")
    pdf.drawString(72, 720, f"Income: {summary['income']}")
    pdf.drawString(72, 700, f"Expenses: {summary['expenses']}")
    y = 680
    for category, total in summary["categories"].items():
        pdf.drawString(72, y, f"{category}: {total}")
        y -= 20
    pdf.save()
    return output.getvalue()


async def build_report(
    db: AsyncSession,
    user: models.User,
    month: date,
    report_type: str,
    file_format: str,
) -> tuple[str, bytes, dict[str, Any]]:
    """Build the file and its summary; returns ``(filename, content, summary)``."""
    month_start, next_month_start = month_bounds(month)
    window = (
        models.Expense.user_id == user.id,
        models.Expense.date >= month_start,
        models.Expense.date < next_month_start,
    )
    income_window = (
        models.Income.user_id == user.id,
        models.Income.date >= month_start,
        models.Income.date < next_month_start,
    )

    expenses_total = (
        await db.execute(
            select(func.coalesce(func.sum(models.Expense.amount), 0)).where(*window)
        )
    ).scalar_one()
    income_total = (
        await db.execute(
            select(func.coalesce(func.sum(models.Income.amount), 0)).where(*income_window)
        )
    ).scalar_one()

    category_rows = (
        await db.execute(
            select(models.Expense.category, func.sum(models.Expense.amount))
            .where(*window)
            .group_by(models.Expense.category)
            .order_by(models.Expense.category)
        )
    ).all()

    summary: dict[str, Any] = {
        "month": month.isoformat(),
        "income": str(income_total or 0),
        "expenses": str(expenses_total or 0),
        "categories": {row[0]: str(row[1]) for row in category_rows},
    }

    if file_format == "excel":
        filename = f"{report_type}-{month:%Y-%m}.xlsx"
        content = _render_excel(month, summary)
    else:
        filename = f"{report_type}-{month:%Y-%m}.pdf"
        content = _render_pdf(month, report_type, summary)

    return filename, content, summary
