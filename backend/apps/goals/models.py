"""SavingsGoal model — a savings target tracked by a student.

Design notes:
  - `is_completed` is a stored boolean (not computed) to avoid re-evaluating
    current_amount >= target_amount on every read. It is set automatically
    via a post_save signal in the goals app's apps.py ready().
  - `current_amount` maps to `saved_amount` in the schema; the field is named
    `current_amount` here to be self-documenting but the JSON key exposed by
    the serialiser will use `saved_amount` to match the API contract.
  - `target_date` maps to `deadline` in the schema.
"""

from django.conf import settings
from django.db import models


class SavingsGoal(models.Model):
    """A savings target tracked by the student (e.g. New Laptop Fund)."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="savings_goals",
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_date = models.DateField(null=True, blank=True, help_text="Optional deadline; null = open-ended.")
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    # Stored boolean — updated via post_save signal when current_amount changes
    is_completed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_completed"], name="ix_goal_user_status"),
            models.Index(fields=["user", "target_date"], name="ix_goal_user_deadline"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.user.email})"

    @property
    def progress_pct(self) -> float:
        """Percentage of target achieved (0–100). Computed, never stored."""
        if not self.target_amount:
            return 0.0
        return round(float(self.current_amount / self.target_amount) * 100, 2)
