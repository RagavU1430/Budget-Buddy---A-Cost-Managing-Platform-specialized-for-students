import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification
from .models import SavingsGoal


@pytest.mark.django_db
def test_goal_completion_sets_status_and_creates_notification():
    user = User.objects.create_user(email="goal@example.com", username="goal", password="pass")
    goal = SavingsGoal.objects.create(user=user, title="Laptop", target_amount=100, current_amount=100)
    goal.refresh_from_db()
    assert goal.is_completed is True
    assert Notification.objects.filter(user=user, notification_type="goal").exists()


@pytest.mark.django_db
def test_goal_deposit_endpoint_updates_progress():
    user = User.objects.create_user(email="deposit@example.com", username="deposit", password="pass")
    goal = SavingsGoal.objects.create(user=user, title="Trip", target_amount=100)
    client = APIClient()
    client.force_authenticate(user)
    result = client.post(f"/api/goals/{goal.pk}/deposit/", {"amount": "25"}, format="json")
    assert result.status_code == 200
    assert result.data["current_amount"] == "25.00"
