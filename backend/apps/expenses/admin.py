from django.contrib import admin

from .models import Expense, Income


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "category", "amount", "date", "payment_method"]
    list_filter = ["category", "payment_method", "date"]
    search_fields = ["title", "user__email", "user__username"]
    date_hierarchy = "date"
    ordering = ["-date"]


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "source_type", "amount", "date"]
    list_filter = ["source_type", "date"]
    search_fields = ["title", "user__email", "user__username"]
    date_hierarchy = "date"
    ordering = ["-date"]
