import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from .models import Notification


@pytest.mark.django_db
def test_notifications_are_private_and_mark_all_read():
    user = User.objects.create_user(email="notify@example.com", username="notify", password="pass")
    other = User.objects.create_user(email="other@example.com", username="other", password="pass")
    Notification.objects.create(user=user, title="One", notification_type="system")
    Notification.objects.create(user=other, title="Other", notification_type="system")
    client = APIClient()
    client.force_authenticate(user)
    result = client.post("/api/notifications/mark-all-read/")
    assert result.status_code == 200
    assert Notification.objects.get(user=user).is_read is True
    assert Notification.objects.get(user=other).is_read is False
