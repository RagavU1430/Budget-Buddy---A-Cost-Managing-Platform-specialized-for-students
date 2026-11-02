"""Seed/demo user management script for BudgetBuddy FastAPI backend.

Usage:
    python -m app.scripts.seed_demo_users [--password "YourPassword123"]

This script creates or refreshes demo accounts across all 3 roles:
- student@budgetbuddy.local (default monthly income: ₹12,000)
- premium@budgetbuddy.local (default monthly income: ₹25,000)
- admin@budgetbuddy.local (default monthly income: ₹50,000)

This replaces the Django `manage.py seed_demo_users` command with a FastAPI-native implementation.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from decimal import Decimal

import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import models
from app.db.base import Base


DEMO_USERS = [
    {
        "email": "student@budgetbuddy.local",
        "username": "student",
        "first_name": "Student",
        "last_name": "User",
        "role": "student",
        "monthly_income": Decimal("12000.00"),
    },
    {
        "email": "premium@budgetbuddy.local",
        "username": "premium",
        "first_name": "Premium",
        "last_name": "User",
        "role": "premium",
        "monthly_income": Decimal("25000.00"),
    },
    {
        "email": "admin@budgetbuddy.local",
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "monthly_income": Decimal("50000.00"),
    },
]


async def seed_demo_users(password: str | None = None, dry_run: bool = False) -> None:
    """Create or refresh demo users in the database."""
    if password is None:
        password = secrets.token_urlsafe(16)

    print(f"Using password: {password}")
    print()

    # Create SQLite async engine
    engine = create_async_engine("sqlite+aiosqlite:///./budgetbuddy.db", echo=False)

    # Ensure all tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        for user_data in DEMO_USERS:
            # Check if user exists
            existing = await session.execute(
                models.User.__table__.select().where(models.User.email == user_data["email"])
            )
            existing_user = existing.scalar_one_or_none()

            if existing_user:
                if dry_run:
                    print(f"[DRY RUN] Would update: {user_data['email']}")
                    continue

                # Update existing user
                existing_user.username = user_data["username"]
                existing_user.first_name = user_data["first_name"]
                existing_user.last_name = user_data["last_name"]
                existing_user.role = user_data["role"]
                existing_user.is_active = True
                existing_user.is_staff = user_data["role"] == "admin"
                existing_user.is_superuser = user_data["role"] == "admin"
                existing_user.password = hash_password(password)

                print(f"✓ Updated: {user_data['email']} ({user_data['role']})")
            else:
                if dry_run:
                    print(f"[DRY RUN] Would create: {user_data['email']}")
                    continue

                # Create new user
                user = models.User(
                    email=user_data["email"],
                    username=user_data["username"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    role=user_data["role"],
                    is_active=True,
                    is_staff=user_data["role"] == "admin",
                    is_superuser=user_data["role"] == "admin",
                    password=hash_password(password),
                    date_joined=None,
                    last_login=None,
                )
                session.add(user)

                print(f"✓ Created: {user_data['email']} ({user_data['role']})")

            await session.flush()

        await session.commit()

    await engine.dispose()

    if not dry_run:
        print()
        print("=" * 50)
        print("Demo users seeded successfully!")
        print("=" * 50)
        print()
        print("Demo Accounts:")
        print("-" * 50)
        for user_data in DEMO_USERS:
            print(f"  🎓 {user_data['role'].capitalize()}: {user_data['email']}")
            print(f"     Monthly Income: ₹{user_data['monthly_income']:,.2f}")
        print()
        print(f"Password: {password}")
        print()
        print("Login at: http://localhost:5173/login")
        print()


async def auto_seed_if_empty(session: AsyncSession) -> None:
    """Ensure baseline demo accounts exist so login works out-of-the-box."""
    from sqlalchemy import select
    for user_data in DEMO_USERS:
        existing = (await session.execute(
            select(models.User).where(models.User.email == user_data["email"])
        )).scalars().first()
        if existing is None:
            user = models.User(
                email=user_data["email"],
                username=user_data["username"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                role=user_data["role"],
                is_active=True,
                is_staff=user_data["role"] == "admin",
                is_superuser=user_data["role"] == "admin",
                password=hash_password("Password123!"),
            )
            session.add(user)
            await session.flush()
            profile = models.Profile(
                user_id=user.id,
                monthly_income=user_data["monthly_income"],
                currency="INR",
            )
            session.add(profile)
    await session.commit()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Seed demo users for BudgetBuddy FastAPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m app.scripts.seed_demo_users
    python -m app.scripts.seed_demo_users --password "MyPass123"
    python -m app.scripts.seed_demo_users --dry-run
        """,
    )
    parser.add_argument(
        "--password",
        type=str,
        help="Password for demo accounts (default: random secure password)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    try:
        import asyncio

        asyncio.run(seed_demo_users(password=args.password, dry_run=args.dry_run))
        return 0
    except Exception as e:
        print(f"Error seeding demo users: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())