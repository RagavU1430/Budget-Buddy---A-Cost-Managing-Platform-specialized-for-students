from io import BytesIO
from django.core.files.base import ContentFile
from django.db.models import Sum
from apps.expenses.models import Expense, Income


def build_report(user, month, report_type, file_format):
    expenses = Expense.objects.filter(user=user, date__year=month.year, date__month=month.month)
    incomes = Income.objects.filter(user=user, date__year=month.year, date__month=month.month)
    summary = {
        "month": month.isoformat(),
        "income": str(incomes.aggregate(total=Sum("amount"))["total"] or 0),
        "expenses": str(expenses.aggregate(total=Sum("amount"))["total"] or 0),
        "categories": {row["category"]: str(row["total"]) for row in expenses.values("category").annotate(total=Sum("amount"))},
    }
    if file_format == "excel":
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
        return ContentFile(output.getvalue(), name=f"{report_type}-{month:%Y-%m}.xlsx"), summary
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
    return ContentFile(output.getvalue(), name=f"{report_type}-{month:%Y-%m}.pdf"), summary
