from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Promote a user to the admin role (staff + superuser flags included)."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username of the account to promote.")

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No user named '{username}'.")

        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["role", "is_staff", "is_superuser"])

        self.stdout.write(self.style.SUCCESS(f"'{username}' is now an admin."))
