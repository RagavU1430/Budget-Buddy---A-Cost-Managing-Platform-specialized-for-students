from decimal import Decimal

from .models import Notification
from apps.budgets.models import Budget
from apps.expenses.models import Expense
from datetime import date
from django.db.models import Sum


def create_budget_alert(user, budget, spent):
    if not budget.limit_amount:
        return None
    ratio = Decimal(spent) / budget.limit_amount
    if ratio < Decimal("0.8"):
        return None
    threshold = "100%" if ratio >= 1 else "80%"
    return Notification.objects.get_or_create(
        user=user,
        notification_type=Notification.Type.BUDGET,
        title=f"Budget alert: {budget.category}",
        defaults={
            "message": f"You have used {threshold} of your {budget.category} budget for {budget.month:%B %Y}."
        },
    )[0]


def check_budget_alerts(user):
    today = date.today()
    for budget in Budget.objects.filter(user=user, month=date(today.year, today.month, 1)):
        spent = Expense.objects.filter(user=user, category=budget.category,
                                       date__year=today.year, date__month=today.month).aggregate(
                                           value=Sum("amount"))["value"] or 0
        create_budget_alert(user, budget, spent)
