from django.apps import AppConfig


class GoalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.goals"
    label = "goals"
    verbose_name = "Savings Goals"

    def ready(self):
        from . import signals  # noqa: F401
