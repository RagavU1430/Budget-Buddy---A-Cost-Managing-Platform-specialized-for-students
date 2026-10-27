from django.conf import settings
from django.db import models


class ChatMessage(models.Model):
    """Stores chat conversations between a student and BudgetBuddy AI."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.USER)
    content = models.TextField()
    action_type = models.CharField(max_length=50, blank=True, default="")
    action_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="ix_chat_user_created"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} [{self.role}]: {self.content[:40]}"
