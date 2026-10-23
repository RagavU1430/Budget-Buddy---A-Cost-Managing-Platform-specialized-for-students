from django.contrib import admin

from .models import SavingsGoal


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user",
        "target_amount",
        "current_amount",
        "progress_pct",
        "is_completed",
        "priority",
        "target_date",
    ]
    list_filter = ["is_completed", "priority"]
    search_fields = ["title", "user__email", "user__username"]
    ordering = ["-created_at"]

    @admin.display(description="Progress %")
    def progress_pct(self, obj):
        return f"{obj.progress_pct}%"
