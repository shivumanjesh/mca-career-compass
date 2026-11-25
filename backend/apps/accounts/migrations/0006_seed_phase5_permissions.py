"""Data migration seeding Phase 5 student empowerment permissions."""
from django.db import migrations
from apps.accounts.rbac import CANONICAL_PERMISSIONS, ROLE_PERMISSION_MAP


def seed_phase5_perms(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    perm_map = {}
    for code, name, scope, description in CANONICAL_PERMISSIONS:
        perm, _ = Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "scope": scope, "description": description},
        )
        perm_map[code] = perm

    for role_code, perm_codes in ROLE_PERMISSION_MAP.items():
        role = Role.objects.filter(code=role_code).first()
        if role:
            for perm_code in perm_codes:
                RolePermission.objects.get_or_create(
                    role=role,
                    permission=perm_map[perm_code],
                )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_seed_phase4_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_phase5_perms, migrations.RunPython.noop),
    ]

