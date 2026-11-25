"""Secure management command to create a Platform Super Admin user."""
import getpass
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.accounts.models import PlatformRole, Role, User
from apps.accounts.rbac import ROLE_PLATFORM_SUPER_ADMIN
from apps.accounts.services import seed_roles_and_permissions


class Command(BaseCommand):
    help = "Create or promote a Platform Super Admin account securely via interactive prompt."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Platform Super Admin email address")
        parser.add_argument("--first-name", required=True, help="First name")
        parser.add_argument("--last-name", default="", help="Last name")

    def handle(self, *args, **options):
        seed_roles_and_permissions()
        email = options["email"].strip().lower()
        password = getpass.getpass("Enter Platform Super Admin password (min 10 chars): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise CommandError("Passwords do not match.")
        if len(password) < 10:
            raise CommandError("Password must be at least 10 characters.")

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": options["first_name"].strip(),
                    "last_name": options["last_name"].strip(),
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            user.set_password(password)
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.save()

            role = Role.objects.get(code=ROLE_PLATFORM_SUPER_ADMIN)
            PlatformRole.objects.get_or_create(user=user, role=role)

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Platform Super Admin: {user.email}"))

