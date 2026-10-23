"""Budget and per-category budget models.

Design notes:
  - Budget is the flat, per-category spending limit.
    One row = one category limit for one user for one month.
  - UniqueConstraint ensures a student cannot set two limits for the same
    category in the same month.
  - `month` is always stored as the first day of the month (YYYY-MM-01) so
    Django's __year / __month ORM filters work without string parsing.
"""

from django.conf import settings
from django.db import models


class Budget(models.Model):
    """Per-category monthly spending limit."""

    class Category(models.TextChoices):
        FOOD = "food", "Food"
        TRAVEL = "travel", "Travel"
        SHOPPING = "shopping", "Shopping"
        EDUCATION = "education", "Education"
        ENTERTAINMENT = "entertainment", "Entertainment"
        MISC = "misc", "Miscellaneous"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    # Always store as YYYY-MM-01 (first day of month)
    month = models.DateField(
        help_text="First day of the budget month, e.g. 2026-10-01.",
        db_index=True,
    )
    category = models.CharField(
        max_length=15, choices=Category.choices, default=Category.MISC
    )
    limit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Maximum allowed spending for this category in this month.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-month", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "month", "category"],
                name="uq_budget_user_month_category",
            )
        ]
        indexes = [
            models.Index(fields=["user", "month"], name="ix_budget_user_month"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} | {self.month:%B %Y} | {self.category}: {self.limit_amount}"
