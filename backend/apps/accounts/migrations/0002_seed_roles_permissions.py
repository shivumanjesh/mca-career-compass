"""Data migration seeding canonical roles and permissions."""
from django.db import migrations
from apps.accounts.rbac import CANONICAL_PERMISSIONS, CANONICAL_ROLES, ROLE_PERMISSION_MAP


def seed_rbac(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    role_map = {}
    for code, name, scope in CANONICAL_ROLES:
        role, _ = Role.objects.update_or_create(
            code=code,
            defaults={"name": name, "scope": scope},
        )
        role_map[code] = role

    perm_map = {}
    for code, name, scope, description in CANONICAL_PERMISSIONS:
        perm, _ = Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "scope": scope, "description": description},
        )
        perm_map[code] = perm

    for role_code, perm_codes in ROLE_PERMISSION_MAP.items():
        role = role_map[role_code]
        for perm_code in perm_codes:
            RolePermission.objects.get_or_create(
                role=role,
                permission=perm_map[perm_code],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_rbac, migrations.RunPython.noop),
    ]

