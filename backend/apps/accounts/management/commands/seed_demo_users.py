"""Management command to seed pre-configured demo users for testing."""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Seed standard demo users for student, premium, and admin roles."

    def handle(self, *args, **options):
        demos = [
            {
                "username": "student",
                "email": "student@budgetbuddy.local",
                "password": "Student123!",
                "role": User.Role.STUDENT,
                "first_name": "Aarav",
                "is_staff": False,
                "is_superuser": False,
                "income": 12000,
            },
            {
                "username": "premium",
                "email": "premium@budgetbuddy.local",
                "password": "Premium123!",
                "role": User.Role.PREMIUM,
                "first_name": "Priya",
                "is_staff": False,
                "is_superuser": False,
                "income": 25000,
            },
            {
                "username": "admin",
                "email": "admin@budgetbuddy.local",
                "password": "Admin123!",
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
            user.set_password(item["password"])
            user.role = item["role"]
            user.first_name = item["first_name"]
            user.is_staff = item["is_staff"]
            user.is_superuser = item["is_superuser"]
            user.save()

            if hasattr(user, "profile"):
                user.profile.monthly_income = item["income"]
                user.profile.currency = "INR"
                user.profile.save()

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"{action} demo user: {item['email']} ({item['role']})")
            )
