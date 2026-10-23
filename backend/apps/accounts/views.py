from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .permissions import IsAdmin
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    RoleUpdateSerializer,
    UserSerializer,
)


def token_payload(user):
    """Build a consistent JWT response with access, refresh and embedded user data."""
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["email"] = user.email
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — create a new user and return JWT tokens."""

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(token_payload(user), status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """POST /api/auth/login/ — authenticate with email + password, return JWT tokens."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(token_payload(serializer.user), status=status.HTTP_200_OK)


class MeView(generics.RetrieveUpdateAPIView):
    """GET /api/auth/me/ — return authenticated user + profile.
    PATCH /api/auth/me/ — update profile fields (monthly_income, currency, etc.)."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ProfileSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = ProfileSerializer(
            request.user.profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ — change the authenticated user's password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class AdminOnlyView(APIView):
    """GET /api/auth/admin-only/ — protected test endpoint for IsAdmin gate.
    Returns 200 for admin role, 403 for student / premium."""

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(
            {
                "detail": "Admin access confirmed.",
                "user": request.user.email,
                "role": request.user.role,
            }
        )


class AdminUserListView(generics.ListAPIView):
    """GET /api/auth/admin/users/ — list all users (admin only)."""

    permission_classes = [IsAdmin]
    serializer_class = UserSerializer
    queryset = User.objects.select_related("profile").all()


class AdminUserRoleUpdateView(generics.UpdateAPIView):
    """PATCH /api/auth/admin/users/<pk>/role/ — change a user's role (admin only)."""

    permission_classes = [IsAdmin]
    serializer_class = RoleUpdateSerializer
    queryset = User.objects.select_related("profile").all()
