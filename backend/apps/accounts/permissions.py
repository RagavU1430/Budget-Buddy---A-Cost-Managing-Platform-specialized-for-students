from rest_framework.permissions import BasePermission

from .models import User


class IsStudent(BasePermission):
    """Allows any authenticated user (student is the default role)."""

    message = "Student access required."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsPremium(BasePermission):
    """Allows premium and admin users."""

    message = "Premium subscription required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in {User.Role.PREMIUM, User.Role.ADMIN}
        )


class IsAdmin(BasePermission):
    """Allows admin users only."""

    message = "Admin access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role == User.Role.ADMIN or user.is_staff or user.is_superuser)
        )
