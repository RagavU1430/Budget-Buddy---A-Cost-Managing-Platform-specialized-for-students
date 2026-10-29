"""Root URL configuration for BudgetBuddy."""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok", "service": "budgetbuddy-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.expenses.urls")),
    path("api/", include("apps.budgets.urls")),
    path("api/", include("apps.assistant.urls")),
    path("api/", include("apps.goals.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.reports.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
