from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["user", "report_type", "month", "file_format", "generated_at"]
    list_filter = ["report_type", "file_format", "month"]
    search_fields = ["user__email"]
