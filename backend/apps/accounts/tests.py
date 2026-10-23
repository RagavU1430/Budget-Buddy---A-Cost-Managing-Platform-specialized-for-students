import os
import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

# Dynamically generated or environment-provided test secret credentials:
TEST_PASSWORD = os.getenv("TEST_USER_PASSWORD", f"Test_{uuid.uuid4().hex[:10]}!Aa1")


class AuthFlowTests(APITestCase):
    def register(self, email="student@example.com", username="student", password=None):
        pwd = password or TEST_PASSWORD
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": email,
                "username": username,
                "password": pwd,
                "password_confirm": pwd,
                "first_name": "Test",
            },
            format="json",
        )
        return response

    def test_register_creates_user_with_student_role(self):
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], User.Role.STUDENT)
        self.assertTrue(User.objects.filter(email="student@example.com").exists())
        self.assertTrue(User.objects.get(email="student@example.com").profile)

    def test_register_rejects_duplicate_email(self):
        self.register()
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_password_mismatch(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "student@example.com",
                "username": "student",
                "password": TEST_PASSWORD,
                "password_confirm": f"{TEST_PASSWORD}_mismatch",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_tokens_and_user(self):
        self.register()
        response = self.client.post(
            reverse("auth-login"),
            {"email": "student@example.com", "password": TEST_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["email"], "student@example.com")

    def test_login_rejects_bad_credentials(self):
        self.register()
        response = self.client.post(
            reverse("auth-login"),
            {"email": "student@example.com", "password": f"{TEST_PASSWORD}_wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        response = self.register()
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], "student@example.com")
        self.assertIn("profile", me.data)

    def test_refresh_token_returns_new_access_token(self):
        response = self.register()
        refresh = self.client.post(
            reverse("auth-refresh"), {"refresh": response.data["refresh"]}, format="json"
        )
        self.assertEqual(refresh.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh.data)

    def test_admin_endpoints_are_staff_only(self):
        response = self.register()
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        admin_users = self.client.get(reverse("auth-admin-users"))
        self.assertEqual(admin_users.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_change_user_role(self):
        user = User.objects.create_user(
            username="member", email="member@example.com", password=TEST_PASSWORD
        )
        admin = User.objects.create_user(
            username="root", email="admin@example.com", password=TEST_PASSWORD, is_staff=True, role=User.Role.ADMIN
        )
        self.client.force_authenticate(admin)
        response = self.client.patch(
            reverse("auth-admin-user-role", args=[user.id]), {"role": "premium"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.PREMIUM)

    def test_admin_only_endpoint_access_control(self):
        # 1. Unauthenticated -> 401
        res_anon = self.client.get(reverse("auth-admin-only"))
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Student -> 403
        reg = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {reg.data['access']}")
        res_student = self.client.get(reverse("auth-admin-only"))
        self.assertEqual(res_student.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Admin -> 200
        admin = User.objects.create_user(
            username="superadmin", email="superadmin@example.com", password=TEST_PASSWORD, is_staff=True, role=User.Role.ADMIN
        )
        self.client.force_authenticate(admin)
        res_admin = self.client.get(reverse("auth-admin-only"))
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res_admin.data["role"], "admin")
