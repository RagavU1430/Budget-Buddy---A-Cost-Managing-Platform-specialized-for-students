from django.contrib import admin

from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["user", "month", "category", "limit_amount", "created_at"]
    list_filter = ["category", "month"]
    search_fields = ["user__email", "user__username"]
    date_hierarchy = "month"
    ordering = ["-month", "user__email"]
