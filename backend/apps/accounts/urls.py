"""URL configuration for the accounts (auth) app."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminOnlyView,
    AdminUserListView,
    AdminUserRoleUpdateView,
    ChangePasswordView,
    LoginView,
    MeView,
    RegisterView,
)

urlpatterns = [
    # Public auth
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),

    # Backward-compat alias — SimpleJWT refresh is also reachable at /refresh/
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh-compat"),

    # Authenticated user
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),

    # Permission-gate test endpoint
    path("admin-only/", AdminOnlyView.as_view(), name="auth-admin-only"),

    # Admin management
    path("admin/users/", AdminUserListView.as_view(), name="auth-admin-users"),
    path(
        "admin/users/<int:pk>/role/",
        AdminUserRoleUpdateView.as_view(),
        name="auth-admin-user-role",
    ),
]
