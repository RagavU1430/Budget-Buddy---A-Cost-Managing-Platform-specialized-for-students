from django.conf import settings
from django.db import models


class Report(models.Model):
    """Generated monthly / expense / income / savings reports."""

    class ReportType(models.TextChoices):
        MONTHLY = "monthly", "Monthly summary"
        EXPENSE = "expense", "Expense history"
        INCOME = "income", "Income history"
        SAVINGS = "savings", "Savings progress"

    class Format(models.TextChoices):
        PDF = "pdf", "PDF"
        EXCEL = "excel", "Excel"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    report_type = models.CharField(max_length=10, choices=ReportType.choices, default=ReportType.MONTHLY)
    month = models.DateField(help_text="First day of the reported month.", db_index=True)
    file_format = models.CharField(max_length=10, choices=Format.choices, default=Format.PDF)
    file = models.FileField(upload_to="reports/%Y/%m/", null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-month", "-generated_at"]

    def __str__(self) -> str:
        return f"{self.get_report_type_display()} - {self.month:%B %Y}"
