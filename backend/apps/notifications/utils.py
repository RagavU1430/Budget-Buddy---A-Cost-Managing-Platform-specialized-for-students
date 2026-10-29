from decimal import Decimal

from .models import Notification


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
