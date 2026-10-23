from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Budget alerts, savings reminders and goal milestones."""

    class Type(models.TextChoices):
        BUDGET = "budget", "Budget"
        SAVINGS = "savings", "Savings"
        GOAL = "goal", "Goal"
        REPORT = "report", "Report"
        SYSTEM = "system", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=10, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=120)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
