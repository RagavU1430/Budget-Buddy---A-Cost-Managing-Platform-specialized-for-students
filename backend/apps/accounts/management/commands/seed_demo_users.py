"""Management command to seed pre-configured demo users for testing without hardcoded credentials."""

import os
import secrets
import string
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_secure_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Seed standard demo users for student, premium, and admin roles securely without hardcoded credentials."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            default=None,
            help="Optional password to assign to seeded demo users. If omitted, reads DEMO_USER_PASSWORD env or generates one.",
        )

    def handle(self, *args, **options):
        demo_password = options.get("password") or os.getenv("DEMO_USER_PASSWORD")
        is_generated = False
        if not demo_password:
            demo_password = generate_secure_password()
            is_generated = True

        demos = [
            {
                "username": "student",
                "email": "student@budgetbuddy.local",
                "role": User.Role.STUDENT,
                "first_name": "Aarav",
                "is_staff": False,
                "is_superuser": False,
                "income": 12000,
            },
            {
                "username": "premium",
                "email": "premium@budgetbuddy.local",
                "role": User.Role.PREMIUM,
                "first_name": "Priya",
                "is_staff": False,
                "is_superuser": False,
                "income": 25000,
            },
            {
                "username": "admin",
                "email": "admin@budgetbuddy.local",
                "role": User.Role.ADMIN,
                "first_name": "Rohan",
                "is_staff": True,
                "is_superuser": True,
                "income": 50000,
            },
        ]

        for item in demos:
            user, created = User.objects.get_or_create(
                email=item["email"],
                defaults={
                    "username": item["username"],
                    "first_name": item["first_name"],
                    "role": item["role"],
                    "is_staff": item["is_staff"],
                    "is_superuser": item["is_superuser"],
                },
            )
            user.set_password(demo_password)
            user.role = item["role"]
            user.first_name = item["first_name"]
            user.is_staff = item["is_staff"]
            user.is_superuser = item["is_superuser"]
            user.save()

            # Ensure profile exists with monthly income
            profile = getattr(user, "profile", None)
            if profile:
                profile.monthly_income = item["income"]
                profile.save(update_fields=["monthly_income"])

            status_str = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Demo user '{user.email}' ({user.role}) {status_str} successfully."
                )
            )

        if is_generated:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[Generated Demo Password]: {demo_password}\n"
                    "Note: Keep this password safe. You can also configure DEMO_USER_PASSWORD in your local .env file."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nDemo users successfully configured with provided/configured password."
                )
            )
