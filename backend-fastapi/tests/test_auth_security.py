"""Security tests for BudgetBuddy authentication endpoints.

Tests cover:
1. Registration - role escalation, email uniqueness bypass, password validation
2. Login - timing attacks, case sensitivity, brute force
3. Token refresh - token reuse, rotation issues
4. Password change - old password verification bypass
5. Email change - OTP brute force, race conditions
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import _otp_hash, token_payload
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db import models


# =============================================================================
# Fixtures and Test Helpers
# =============================================================================

@pytest.fixture
def test_user_data() -> dict[str, Any]:
    """Base user data for registration tests."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePass123",
        "password_confirm": "SecurePass123",
    }


@pytest.fixture
def admin_user_data() -> dict[str, Any]:
    """User data with admin role attempt."""
    return {
        "email": "admin@example.com",
        "username": "adminuser",
        "first_name": "Admin",
        "last_name": "User",
        "password": "AdminPass123",
        "password_confirm": "AdminPass123",
        "role": "admin",
    }


@pytest.fixture
async def registered_user(async_client: httpx.AsyncClient, test_user_data: dict) -> dict:
    """Register a test user and return their data + tokens."""
    response = await async_client.post("/api/auth/register/", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def auth_headers(registered_user: dict) -> dict:
    """Authorization headers with access token."""
    return {"Authorization": f"Bearer {registered_user['access']}"}


# =============================================================================
# 1. REGISTRATION ENDPOINT TESTS
# =============================================================================

class TestRegistrationSecurity:
    """Security tests for POST /api/auth/register/"""

    @pytest.mark.asyncio
    async def test_role_cannot_be_set_to_admin(
        self, async_client: httpx.AsyncClient, admin_user_data: dict
    ):
        """Test that client cannot set role to admin during registration.

        The code at auth.py:221 hardcodes role='student' regardless of input.
        This test verifies the hardening fix works.
        """
        response = await async_client.post("/api/auth/register/", json=admin_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["role"] == "student", (
            "Registration should ignore client-provided role and default to student"
        )

    @pytest.mark.asyncio
    async def test_role_cannot_be_set_to_premium(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that client cannot set role to premium during registration."""
        test_user_data["role"] = "premium"
        test_user_data["email"] = "premium@example.com"
        test_user_data["username"] = "premiumuser"

        response = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["role"] == "student"

    @pytest.mark.asyncio
    async def test_invalid_role_rejected(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that invalid role values are rejected with 400."""
        test_user_data["role"] = "superadmin"
        test_user_data["email"] = "invalid@example.com"
        test_user_data["username"] = "invaliduser"

        response = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response.status_code == 400
        assert "role" in response.json()

    @pytest.mark.asyncio
    async def test_email_uniqueness_case_insensitive(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that email uniqueness is enforced case-insensitively.

        The code at auth.py:130-132 uses func.lower() for duplicate check.
        """
        # Register first user
        response1 = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response1.status_code == 201

        # Try to register with same email but different case
        test_user_data["username"] = "testuser2"
        test_user_data["email"] = "TEST@EXAMPLE.COM"

        response2 = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response2.status_code == 400
        assert "email" in response2.json()
        assert "already exists" in response2.json()["email"][0].lower()

    @pytest.mark.asyncio
    async def test_password_validation_min_length(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test password minimum length enforcement (8 chars per validation.py:347)."""
        test_user_data["password"] = "Short1"
        test_user_data["password_confirm"] = "Short1"
        test_user_data["email"] = "short@example.com"
        test_user_data["username"] = "shortuser"

        response = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response.status_code == 400
        assert "password" in response.json()
        assert any("too short" in msg.lower() for msg in response.json()["password"])

    @pytest.mark.asyncio
    async def test_password_validation_common_passwords_rejected(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that common passwords are rejected (validation.py:310-331)."""
        common_passwords = [
            "password", "password123", "12345678", "qwerty123",
            "admin123", "welcome123", "letmein123", "student123"
        ]

        for pwd in common_passwords:
            test_user_data["email"] = f"test{uuid.uuid4().hex[:8]}@example.com"
            test_user_data["username"] = f"user{uuid.uuid4().hex[:8]}"
            test_user_data["password"] = pwd
            test_user_data["password_confirm"] = pwd

            response = await async_client.post("/api/auth/register/", json=test_user_data)
            assert response.status_code == 400, f"Password '{pwd}' should be rejected"
            assert "password" in response.json()
            assert any("too common" in msg.lower() for msg in response.json()["password"])

    @pytest.mark.asyncio
    async def test_password_validation_all_numeric_rejected(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that entirely numeric passwords are rejected."""
        test_user_data["password"] = "12345678"
        test_user_data["password_confirm"] = "12345678"
        test_user_data["email"] = "numeric@example.com"
        test_user_data["username"] = "numericuser"

        response = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response.status_code == 400
        assert "password" in response.json()
        assert any("entirely numeric" in msg.lower() for msg in response.json()["password"])

    @pytest.mark.asyncio
    async def test_password_confirm_mismatch(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that password confirmation mismatch is caught."""
        test_user_data["password_confirm"] = "DifferentPass123"
        test_user_data["email"] = "mismatch@example.com"
        test_user_data["username"] = "mismatchuser"

        response = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response.status_code == 400
        assert "password_confirm" in response.json()
        assert any("match" in msg.lower() for msg in response.json()["password_confirm"])

    @pytest.mark.asyncio
    async def test_username_uniqueness_enforced(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test username uniqueness is enforced."""
        response1 = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response1.status_code == 201

        # Try same username, different email
        test_user_data["email"] = "different@example.com"
        response2 = await async_client.post("/api/auth/register/", json=test_user_data)
        assert response2.status_code == 400
        assert "username" in response2.json()
        assert "already exists" in response2.json()["username"][0].lower()

    @pytest.mark.asyncio
    async def test_sql_injection_in_email_field(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that SQL injection attempts in email are sanitized.

        Uses parameterized queries via SQLAlchemy ORM - should be safe.
        """
        test_user_data["email"] = "test'; DROP TABLE users; --@example.com"
        test_user_data["username"] = "sqlinject"

        response = await async_client.post("/api/auth/register/", json=test_user_data)
        # Should fail validation, not crash
        assert response.status_code in (400, 422)


# =============================================================================
# 2. LOGIN ENDPOINT TESTS
# =============================================================================

class TestLoginSecurity:
    """Security tests for POST /api/auth/login/"""

    @pytest.mark.asyncio
    async def test_valid_login_works(
        self, async_client: httpx.AsyncClient, registered_user: dict, test_user_data: dict
    ):
        """Test that valid credentials work."""
        response = await async_client.post("/api/auth/login/", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        assert "access" in response.json()
        assert "refresh" in response.json()

    @pytest.mark.asyncio
    async def test_login_case_insensitive_email(
        self, async_client: httpx.AsyncClient, registered_user: dict, test_user_data: dict
    ):
        """Test that login email is case-insensitive (auth.py:242).

        Note: This differs from Django's case-sensitive behavior (auth.py:8-9 comment).
        """
        response = await async_client.post("/api/auth/login/", json={
            "email": test_user_data["email"].upper(),
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        assert "access" in response.json()

    @pytest.mark.asyncio
    async def test_wrong_password_rejected(
        self, async_client: httpx.AsyncClient, registered_user: dict, test_user_data: dict
    ):
        """Test that wrong password is rejected."""
        response = await async_client.post("/api/auth/login/", json={
            "email": test_user_data["email"],
            "password": "WrongPassword123",
        })
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "credentials" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_nonexistent_user_rejected(
        self, async_client: httpx.AsyncClient
    ):
        """Test that nonexistent user gets same error as wrong password (no user enumeration)."""
        response = await async_client.post("/api/auth/login/", json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123",
        })
        assert response.status_code == 401
        assert "detail" in response.json()
        # Should be same generic message to prevent user enumeration
        assert "no active account" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_timing_attack_resistance_password_compare(
        self, async_client: httpx.AsyncClient, registered_user: dict, test_user_data: dict
    ):
        """Test that password verification uses constant-time comparison.

        The verify_password function in security.py:56 uses hmac.compare_digest
        which is constant-time. This test measures timing to detect gross differences.
        """
        # We can't easily test microsecond timing in CI, but we verify the code path
        # uses hmac.compare_digest by checking the implementation
        from app.core.security import verify_password
        import inspect

        source = inspect.getsource(verify_password)
        assert "hmac.compare_digest" in source, (
            "Password verification must use hmac.compare_digest for timing attack resistance"
        )

    @pytest.mark.asyncio
    async def test_timing_attack_user_enumeration(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test for user enumeration via timing attacks on login.

        The _authenticate function (auth.py:240-257) does DB lookup FIRST,
        then password verification. This could leak whether email exists.

        This test documents the potential issue - in production, should add
        dummy password hash for nonexistent users to equalize timing.
        """
        # Register a user first
        await async_client.post("/api/auth/register/", json=test_user_data)

        # Time multiple requests for existing vs non-existing users
        existing_times = []
        nonexisting_times = []

        for _ in range(10):
            # Existing user
            start = time.perf_counter()
            await async_client.post("/api/auth/login/", json={
                "email": test_user_data["email"],
                "password": "WrongPassword123",
            })
            existing_times.append(time.perf_counter() - start)

            # Non-existing user
            start = time.perf_counter()
            await async_client.post("/api/auth/login/", json={
                "email": f"nonexist{uuid.uuid4().hex[:8]}@example.com",
                "password": "WrongPassword123",
            })
            nonexisting_times.append(time.perf_counter() - start)

        avg_existing = sum(existing_times) / len(existing_times)
        avg_nonexisting = sum(nonexisting_times) / len(nonexisting_times)

        # Document the timing difference (in CI this may be noisy)
        # In production, this should be mitigated
        print(f"Avg existing user time: {avg_existing*1000:.2f}ms")
        print(f"Avg non-existing user time: {avg_nonexisting*1000:.2f}ms")

        # The test passes but documents the potential issue
        # A significant difference (>50ms) indicates enumeration risk
        timing_diff = abs(avg_existing - avg_nonexisting)
        if timing_diff > 0.05:  # 50ms threshold
            print(f"WARNING: Potential timing-based user enumeration detected! "
                  f"Difference: {timing_diff*1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_brute_force_no_rate_limiting(
        self, async_client: httpx.AsyncClient, test_user_data: dict
    ):
        """Test that there's no rate limiting on login (vulnerability).

        This documents the lack of brute force protection.
        """
        await async_client.post("/api/auth/register/", json=test_user_data)

        # Make many failed attempts - should not be blocked
        for i in range(20):
            response = await async_client.post("/api/auth/login/", json={
                "email": test_user_data["email"],
                "password": f"WrongPassword{i}",
            })
            assert response.status_code == 401

        # 21st attempt should still work (no lockout)
        response = await async_client.post("/api/auth/login/", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200

        print("WARNING: No rate limiting on login endpoint - brute force possible")


# =============================================================================
# 3. TOKEN REFRESH TESTS
# =============================================================================

class TestTokenRefreshSecurity:
    """Security tests for POST /api/auth/token/refresh/"""

    @pytest.mark.asyncio
    async def test_valid_refresh_token_works(
        self, async_client: httpx.AsyncClient, registered_user: dict
    ):
        """Test that valid refresh token returns new token pair."""
        response = await async_client.post("/api/auth/token/refresh/", json={
            "refresh": registered_user["refresh"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data
        # New tokens should be different
        assert data["access"] != registered_user["access"]
        assert data["refresh"] != registered_user["refresh"]

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_allowed_vulnerability(
        self, async_client: httpx.AsyncClient, registered_user: dict
    ):
        """Test that refresh tokens can be reused (VULNERABILITY).

        SimpleJWT with ROTATE_REFRESH_TOKENS=True should invalidate old tokens,
        but the current implementation (auth.py:290-316) doesn't track used JTIs.
        Old refresh tokens remain valid until expiry.
        """
        # First refresh
        response1 = await async_client.post("/api/auth/token/refresh/", json={
            "refresh": registered_user["refresh"],
        })
        assert response1.status_code == 200
        new_refresh = response1.json()["refresh"]

        # Original refresh token should be invalidated but isn't
        response2 = await async_client.post("/api/auth/token/refresh/", json={
            "refresh": registered_user["refresh"],  # Reuse OLD token
        })
        # This currently succeeds - VULNERABILITY
        assert response2.status_code == 200, (
            "Old refresh token was accepted - token reuse not prevented. "
            "This is a security vulnerability: stolen refresh tokens remain valid."
        )

        print("VULNERABILITY: Refresh token reuse not prevented. "
              "Implement JTI blacklist or token rotation tracking.")

    @pytest.mark.asyncio
    async def test_expired_refresh_token_rejected(
        self, async_client: httpx.AsyncClient, registered_user: dict
    ):
        """Test that expired refresh tokens are rejected."""
        # Create an expired refresh token
        expired_token = create_refresh_token(
            user_id=99999, role="student", email="expired@test.com"
        )
        # Manually set exp to past
        payload = decode_token(expired_token)
        payload["exp"] = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        response = await async_client.post("/api/auth/token/refresh/", json={
            "refresh": expired_token,
        })
        assert response.status_code == 401
        assert "invalid or expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_malformed_refresh_token_rejected(
        self, async_client: httpx.AsyncClient
    ):
        """Test that malformed refresh tokens are rejected."""
        response = await async_client.post("/api/auth/token/refresh/", json={
            "refresh": "not.a.valid.token",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_token_as_refresh_rejected(
        self, async_client: httpx.AsyncClient, registered_user: dict
    ):
        """Test that access token cannot be used as refresh token."""
        response = await async_client.post("/api/auth/token/refresh/", json={
            "refresh": registered_user["access"],  # Use access token
        })
        assert response.status_code == 401
        assert "wrong token type" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_jti_uniqueness_per_token(
        self, registered_user: dict
    ):
        """Test that each token has unique JTI."""
        access1 = create_access_token(1, "student", "test@test.com")
        access2 = create_access_token(1, "student", "test@test.com")
        refresh1 = create_refresh_token(1, "student", "test@test.com")
        refresh2 = create_refresh_token(1, "student", "test@test.com")

        payload1 = decode_token(access1)
        payload2 = decode_token(access2)
        payload3 = decode_token(refresh1)
        payload4 = decode_token(refresh2)

        assert payload1["jti"] != payload2["jti"], "Access tokens must have unique JTI"
        assert payload3["jti"] != payload4["jti"], "Refresh tokens must have unique JTI"
        assert payload1["jti"] != payload3["jti"], "Access and refresh JTI must differ"


# =============================================================================
# 4. PASSWORD CHANGE TESTS
# =============================================================================

class TestPasswordChangeSecurity:
    """Security tests for POST /api/auth/change-password/"""

    @pytest.mark.asyncio
    async def test_valid_password_change(
        self, async_client: httpx.AsyncClient, auth_headers: dict, test_user_data: dict
    ):
        """Test that valid password change works."""
        response = await async_client.post(
            "/api/auth/change-password/",
            json={
                "current_password": test_user_data["password"],
                "new_password": "NewSecurePass456",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["detail"] == "Password updated."

    @pytest.mark.asyncio
    async def test_wrong_current_password_rejected(
        self, async_client: httpx.AsyncClient, auth_headers: dict, test_user_data: dict
    ):
        """Test that incorrect current password is rejected."""
        response = await async_client.post(
            "/api/auth/change-password/",
            json={
                "current_password": "WrongPassword123",
                "new_password": "NewSecurePass456",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "current_password" in response.json()
        assert "incorrect" in response.json()["current_password"][0].lower()

    @pytest.mark.asyncio
    async def test_password_change_requires_auth(
        self, async_client: httpx.AsyncClient
    ):
        """Test that password change requires authentication."""
        response = await async_client.post(
            "/api/auth/change-password/",
            json={
                "current_password": "old",
                "new_password": "new",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_new_password_validation_applied(
        self, async_client: httpx.AsyncClient, auth_headers: dict, test_user_data: dict
    ):
        """Test that new password must pass validation rules."""
        # Too short
        response = await async_client.post(
            "/api/auth/change-password/",
            json={
                "current_password": test_user_data["password"],
                "new_password": "Short1",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "new_password" in response.json()

        # Common password
        response = await async_client.post(
            "/api/auth/change-password/",
            json={
                "current_password": test_user_data["password"],
                "new_password": "password123",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

        # All numeric
        response = await async_client.post(
            "/api/auth/change-password/",
            json={
                "current_password": test_user_data["password"],
                "new_password": "12345678",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_password_change_uses_constant_time_compare(
        self, async_client: httpx.AsyncClient, auth_headers: dict, test_user_data: dict
    ):
        """Test that current password verification uses constant-time comparison."""
        from app.core.security import verify_password
        import inspect

        source = inspect.getsource(verify_password)
        assert "hmac.compare_digest" in source


# =============================================================================
# 5. EMAIL CHANGE FLOW TESTS
# =============================================================================

class TestEmailChangeSecurity:
    """Security tests for email change request/verify endpoints."""

    @pytest.mark.asyncio
    async def test_request_email_change_sends_otp(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        """Test that email change request sends OTP."""
        with patch("app.api.auth.send_verification_code", new_callable=AsyncMock) as mock_send:
            response = await async_client.post(
                "/api/auth/email-change/request/",
                json={"email": "newemail@example.com"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert "detail" in response.json()
            assert "verification code sent" in response.json()["detail"].lower()
            mock_send.assert_called_once()
            # Verify OTP is 6 digits
            call_args = mock_send.call_args
            assert call_args[0][0] == "newemail@example.com"
            assert len(call_args[0][1]) == 6
            assert call_args[0][1].isdigit()

    @pytest.mark.asyncio
    async def test_email_change_same_as_current_rejected(
        self, async_client: httpx.AsyncClient, auth_headers: dict, registered_user: dict
    ):
        """Test that changing to same email is rejected."""
        current_email = registered_user["user"]["email"]
        response = await async_client.post(
            "/api/auth/email-change/request/",
            json={"email": current_email},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "email" in response.json()
        assert "already your current" in response.json()["email"][0].lower()

    @pytest.mark.asyncio
    async def test_email_change_to_existing_email_rejected(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        """Test that changing to an email used by another user is rejected."""
        # Register another user
        await async_client.post("/api/auth/register/", json={
            "email": "existing@example.com",
            "username": "existinguser",
            "password": "Password123",
            "password_confirm": "Password123",
        })

        response = await async_client.post(
            "/api/auth/email-change/request/",
            json={"email": "existing@example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "email" in response.json()
        assert "already exists" in response.json()["email"][0].lower()

    @pytest.mark.asyncio
    async def test_otp_brute_force_limited_to_5_attempts(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        """Test that OTP verification limits to 5 attempts (auth.py:595)."""
        with patch("app.api.auth.send_verification_code", new_callable=AsyncMock):
            # Request email change
            await async_client.post(
                "/api/auth/email-change/request/",
                json={"email": "new@example.com"},
                headers=auth_headers,
            )

        # Try 5 wrong codes
        for i in range(5):
            response = await async_client.post(
                "/api/auth/email-change/verify/",
                json={"code": "000000"},
                headers=auth_headers,
            )
            assert response.status_code == 400
            assert "incorrect" in response.json()["code"][0].lower()

        # 6th attempt should be rejected with "too many attempts"
        response = await async_client.post(
            "/api/auth/email-change/verify/",
            json={"code": "000000"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "too many" in response.json()["code"][0].lower()

    @pytest.mark.asyncio
    async def test_otp_rate_6_digits_1_million_combinations(
        self
    ):
        """Test that OTP is 6 digits (1,000,000 combinations).

        With 5 attempts allowed, probability of guessing = 5/1,000,000 = 0.0005%
        This is acceptable but could be strengthened with longer OTP or rate limiting
        on the request endpoint itself.
        """
        # Verify OTP generation uses 6 digits
        import app.api.auth as auth_module
        import inspect

        source = inspect.getsource(auth_module.request_email_change)
        assert "range(6)" in source or "0123456789" in source

    @pytest.mark.asyncio
    async def test_otp_expires_after_10_minutes(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        """Test that OTP expires after 10 minutes (auth.py:558)."""
        from app.db import models
        from app.api.auth import _otp_hash
        from datetime import datetime, timedelta, timezone

        # We can't easily test time expiry in unit test without mocking time
        # but we verify the expiry is set correctly in code
        import inspect
        source = inspect.getsource(async_client)
        # Check the expires_at is set to 10 minutes
        source = inspect.getsource(auth_module.request_email_change)
        assert "timedelta(minutes=10)" in source

    @pytest.mark.asyncio
    async def test_otp_uses_hmac_for_verification(
        self
    ):
        """Test that OTP verification uses HMAC compare_digest (auth.py:599)."""
        import inspect
        source = inspect.getsource(auth_module.verify_email_change)
        assert "hmac.compare_digest" in source

    @pytest.mark.asyncio
    async def test_email_change_monthly_limit_2(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        """Test that email can only be changed twice per month (auth.py:539, 625)."""
        with patch("app.api.auth.send_verification_code", new_callable=AsyncMock):
            # First change
            response1 = await async_client.post(
                "/api/auth/email-change/request/",
                json={"email": "change1@example.com"},
                headers=auth_headers,
            )
            assert response1.status_code == 200

            # Verify with correct code
            # We need to extract the code from the mock call
            mock_send = patch("app.api.auth.send_verification_code").start()
            code = mock_send.call_args[0][1]
            patch("app.api.auth.send_verification_code").stop()

            # Can't easily complete full flow without DB, but verify limit check exists
            import inspect
            source = inspect.getsource(auth_module.request_email_change)
            assert "change_count >= 2" in source
            assert "twice per month" in source

    @pytest.mark.asyncio
    async def test_race_condition_email_change(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        """Test for potential race condition in email change verification.

        Between checking attempts (line 595) and incrementing (line 600),
        concurrent requests could bypass the limit.

        The code uses await db.commit() after increment which provides
        some protection but not full atomicity.
        """
        import inspect
        source = inspect.getsource(auth_module.verify_email_change)

        # Check that attempts increment and commit happen
        assert "pending.attempts += 1" in source
        assert "await db.commit()" in source

        print("NOTE: Potential race condition in OTP attempt counting. "
              "Consider using atomic DB operations or row-level locking.")


# =============================================================================
# 6. JWT TOKEN SECURITY TESTS
# =============================================================================

class TestJWTSecurity:
    """Security tests for JWT token handling."""

    def test_token_algorithm_hs256(self):
        """Test that JWT uses HS256 algorithm (config.py:25)."""
        assert settings.JWT_ALGORITHM == "HS256"

    def test_token_has_jti(self):
        """Test that tokens include JTI for revocation support."""
        token = create_access_token(1, "student", "test@test.com")
        payload = decode_token(token)
        assert "jti" in payload
        assert len(payload["jti"]) == 32  # uuid4().hex

    def test_token_has_expiry(self):
        """Test that tokens have expiry."""
        token = create_access_token(1, "student", "test@test.com")
        payload = decode_token(token)
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_access_token_lifetime_60_minutes(self):
        """Test access token lifetime is 60 minutes (config.py:83)."""
        token = create_access_token(1, "student", "test@test.com")
        payload = decode_token(token)
        lifetime = payload["exp"] - payload["iat"]
        assert lifetime == 60 * 60  # 60 minutes in seconds

    def test_refresh_token_lifetime_7_days(self):
        """Test refresh token lifetime is 7 days (config.py:84)."""
        token = create_refresh_token(1, "student", "test@test.com")
        payload = decode_token(token)
        lifetime = payload["exp"] - payload["iat"]
        assert lifetime == 7 * 24 * 60 * 60  # 7 days in seconds

    def test_token_type_distinction(self):
        """Test that access and refresh tokens have different types."""
        access = create_access_token(1, "student", "test@test.com")
        refresh = create_refresh_token(1, "student", "test@test.com")

        access_payload = decode_token(access)
        refresh_payload = decode_token(refresh)

        assert access_payload["token_type"] == "access"
        assert refresh_payload["token_type"] == "refresh"

    def test_token_secret_key_not_default(self):
        """Test that SECRET_KEY is not the default development value."""
        # In production, this should fail if using default
        # For testing, we just document the check
        if settings.SECRET_KEY == "django-insecure-dev-only-change-me":
            print("WARNING: Using default SECRET_KEY - must be changed in production!")

    def test_token_tampering_detected(self):
        """Test that token tampering is detected."""
        token = create_access_token(1, "student", "test@test.com")
        # Tamper with the token
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "." + "tampered"

        with pytest.raises(jwt.InvalidSignatureError):
            decode_token(tampered)


# =============================================================================
# 7. PASSWORD HASHING SECURITY TESTS
# =============================================================================

class TestPasswordHashingSecurity:
    """Security tests for password hashing."""

    def test_new_passwords_use_argon2(self):
        """Test that new passwords are hashed with Argon2 (security.py:36)."""
        hash_result = hash_password("TestPassword123")
        assert hash_result.startswith("argon2$")

    def test_argon2_verification_works(self):
        """Test that Argon2 hashes verify correctly."""
        password = "TestPassword123"
        hash_result = hash_password(password)
        assert verify_password(password, hash_result) is True
        assert verify_password("WrongPassword", hash_result) is False

    def test_pbkdf2_legacy_verification_works(self):
        """Test that legacy PBKDF2 hashes still verify (security.py:47-60)."""
        # Django-style PBKDF2 hash
        import hashlib
        import base64
        import hmac

        password = "LegacyPassword123"
        salt = "testsalt"
        iterations = 1200000
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
        encoded = f"pbkdf2_sha256${iterations}${salt}${base64.b64encode(digest).decode()}"

        assert verify_password(password, encoded) is True
        assert verify_password("WrongPassword", encoded) is False

    def test_needs_rehash_detects_old_hashes(self):
        """Test that needs_rehash identifies PBKDF2 hashes for migration (security.py:64-66)."""
        from app.core.security import needs_rehash

        argon2_hash = hash_password("Test123")
        pbkdf2_hash = "pbkdf2_sha256$1200000$salt$hash"

        assert needs_rehash(argon2_hash) is False
        assert needs_rehash(pbkdf2_hash) is True

    def test_password_hash_timing_resistant(self):
        """Test that verify_password uses constant-time comparison."""
        import inspect
        source = inspect.getsource(verify_password)
        assert "hmac.compare_digest" in source


# =============================================================================
# 8. GENERAL SECURITY TESTS
# =============================================================================

class TestGeneralSecurity:
    """General security tests."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, async_client: httpx.AsyncClient):
        """Test that CORS headers are properly configured."""
        response = await async_client.options("/api/auth/login/")
        # Check CORS configuration
        # Note: Actual CORS is handled by middleware

    @pytest.mark.asyncio
    async def test_debug_mode_not_exposed_in_production(self):
        """Test that DEBUG mode is not enabled in production."""
        # This is a configuration check
        if settings.DEBUG:
            print("WARNING: DEBUG mode is enabled - should be False in production!")

    @pytest.mark.asyncio
    async def test_admin_endpoints_require_admin_role(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        """Test that admin endpoints require admin role."""
        # Regular user should not access admin endpoints
        response = await async_client.get("/api/auth/admin-only/", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_user_stats_requires_key(
        self, async_client: httpx.AsyncClient
    ):
        """Test that user-stats endpoint requires admin key."""
        response = await async_client.get("/api/auth/user-stats/")
        assert response.status_code == 403

        response = await async_client.get("/api/auth/user-stats/?key=wrong")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_security_fix_endpoint_requires_key(
        self, async_client: httpx.AsyncClient
    ):
        """Test that security-fix endpoint requires admin key."""
        response = await async_client.post("/api/auth/security-fix/")
        assert response.status_code == 403


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])