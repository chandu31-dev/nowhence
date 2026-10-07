from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create an admin user if it doesn't already exist."

    def handle(self, *args, **kwargs):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "owner")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        existing_user = User.objects.filter(username=username).first()
        if existing_user:
            if existing_user.is_superuser:
                self.stdout.write(self.style.SUCCESS("Owner admin already exists."))
                return
            raise CommandError(f"Username '{username}' is already in use by a non-admin account.")

        if not password:
            raise CommandError(
                "Set DJANGO_SUPERUSER_PASSWORD to a strong password before creating the owner admin."
            )

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(self.style.SUCCESS(f"Owner admin '{username}' created successfully."))