"""Pytest configuration and fixtures for BudgetBuddy backend tests."""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db import models
from app.main import app


# ---------------------------------------------------------------------------
# Test Database Setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_test_db():
    """Initialize test database with all tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_test_db():
    """Drop all test tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    await init_test_db()
    async with TestAsyncSessionLocal() as session:
        yield session
    await drop_test_db()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with dependency overrides."""

    # Override the database dependency
    from app.api.deps import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


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


@pytest_asyncio.fixture
async def registered_user(async_client: AsyncClient, test_user_data: dict) -> dict:
    """Register a test user and return their data + tokens."""
    response = await async_client.post("/api/auth/register/", json=test_user_data)
    assert response.status_code == 201, f"Registration failed: {response.text}"
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(registered_user: dict) -> dict:
    """Authorization headers with access token."""
    return {"Authorization": f"Bearer {registered_user['access']}"}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> models.User:
    """Create an admin user directly in the database."""
    user = models.User(
        email="admin@example.com",
        username="adminuser",
        first_name="Admin",
        last_name="User",
        role="admin",
        is_staff=True,
        is_active=True,
        is_superuser=True,
        password=hash_password("AdminPass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_auth_headers(async_client: AsyncClient, admin_user: models.User) -> dict:
    """Get auth headers for admin user."""
    response = await async_client.post("/api/auth/login/", json={
        "email": "admin@example.com",
        "password": "AdminPass123",
    })
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access']}"}


# ---------------------------------------------------------------------------
# Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_email_service():
    """Mock the email service."""
    with patch("app.api.auth.send_verification_code", new_callable=AsyncMock) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Test Configuration
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "security: mark test as security-related"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_test_user(
    db: AsyncSession,
    email: str = "test@example.com",
    username: str = "testuser",
    role: str = "student",
    password: str = "TestPass123",
) -> models.User:
    """Helper to create a test user directly in DB."""
    user = models.User(
        email=email,
        username=username,
        role=role,
        is_active=True,
        password=hash_password(password),
    )
    db.add(user)
    return user


async def get_tokens_for_user(user: models.User) -> dict[str, str]:
    """Generate token pair for a user."""
    from app.core.security import token_pair
    return token_pair(user.id, user.role, user.email)