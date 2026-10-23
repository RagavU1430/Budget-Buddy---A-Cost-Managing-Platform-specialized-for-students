"""Income and Expense models.

Design notes:
  - `category` on Expense is a CharField with TextChoices (not a FK to a
    Category table). This avoids a JOIN on the most-frequent query:
    "sum expenses for this category in this month."
  - Composite indexes on (user, date) and (user, category) cover all
    common dashboard queries.
  - DecimalField(max_digits=12, decimal_places=2) for all money fields.
"""

from django.conf import settings
from django.db import models


class Expense(models.Model):
    """A single spending event recorded by a student."""

    class Category(models.TextChoices):
        FOOD = "food", "Food"
        TRAVEL = "travel", "Travel"
        SHOPPING = "shopping", "Shopping"
        EDUCATION = "education", "Education"
        ENTERTAINMENT = "entertainment", "Entertainment"
        MISC = "misc", "Miscellaneous"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        BANK = "bank", "Bank transfer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    category = models.CharField(
        max_length=15, choices=Category.choices, default=Category.MISC
    )
    title = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    payment_method = models.CharField(
        max_length=12,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"], name="ix_expense_user_date"),
            models.Index(fields=["user", "category"], name="ix_expense_user_category"),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.amount}"


class Income(models.Model):
    """A single income event recorded by a student."""

    class SourceType(models.TextChoices):
        POCKET_MONEY = "pocket_money", "Pocket money"
        SCHOLARSHIP = "scholarship", "Scholarship"
        FREELANCE = "freelance", "Freelance"
        PART_TIME = "part_time", "Part-time job"
        GIFT = "gift", "Gift"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incomes",
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.POCKET_MONEY,
    )
    title = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"], name="ix_income_user_date"),
            models.Index(fields=["user", "source_type"], name="ix_income_user_source"),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.amount}"
