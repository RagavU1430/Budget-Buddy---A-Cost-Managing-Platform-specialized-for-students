from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.budgets.models import Budget
from .models import Expense


@receiver(post_save, sender=Expense)
def budget_alert_hook(sender, instance, **kwargs):
    budget = Budget.objects.filter(
        user=instance.user, month=instance.date.replace(day=1), category=instance.category
    ).first()
    if budget:
        from apps.notifications.utils import create_budget_alert
        spent = Expense.objects.filter(
            user=instance.user, date__year=instance.date.year,
            date__month=instance.date.month, category=instance.category
        ).aggregate(total=Sum("amount"))["total"] or 0
        create_budget_alert(instance.user, budget, spent)
