"""Management command to ensure a superuser exists.

This command reads superuser credentials from environment variables and creates
a superuser if one doesn't already exist. Useful for automated deployments.

Environment Variables:
    DJANGO_SUPERUSER_USERNAME: Username for the superuser
    DJANGO_SUPERUSER_EMAIL: Email for the superuser
    DJANGO_SUPERUSER_PASSWORD: Password for the superuser

Usage:
    python manage.py ensure_superuser
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from league_gotta_bike.config import settings as env_settings

User = get_user_model()


class Command(BaseCommand):
    """Ensure a superuser account exists with credentials from environment variables."""

    help = "Creates a superuser if credentials are provided via environment variables"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing superuser email/password if user already exists",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        username = env_settings.DJANGO_SUPERUSER_USERNAME
        email = env_settings.DJANGO_SUPERUSER_EMAIL
        password = env_settings.DJANGO_SUPERUSER_PASSWORD

        # Check if credentials are provided
        if not username or not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Superuser credentials not provided in environment variables. "
                    "Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and "
                    "DJANGO_SUPERUSER_PASSWORD to auto-create a superuser."
                )
            )
            return

        # Check if user already exists
        try:
            user = User.objects.get(username=username)
            if options["update"]:
                # Update existing user
                user.email = email
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Superuser "{username}" already exists. '
                        "Email and password have been updated."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Superuser "{username}" already exists. Use --update to update credentials.'
                    )
                )
        except User.DoesNotExist:
            # Create new superuser
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser "{username}" created successfully with email: {email}'
                )
            )
