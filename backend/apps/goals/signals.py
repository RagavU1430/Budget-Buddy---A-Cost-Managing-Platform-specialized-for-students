from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SavingsGoal


@receiver(post_save, sender=SavingsGoal)
def goal_completion_notification(sender, instance, created, **kwargs):
    from apps.notifications.models import Notification

    if instance.is_completed:
        Notification.objects.get_or_create(
            user=instance.user,
            notification_type=Notification.Type.GOAL,
            title=f"Goal completed: {instance.title}",
            defaults={"message": f"You reached your savings goal of {instance.target_amount}."},
        )
