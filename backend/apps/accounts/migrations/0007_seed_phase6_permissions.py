"""Data migration to seed Phase 6 Institutional Intelligence & Executive permissions."""
from django.db import migrations


def seed_phase6(apps, schema_editor):
    from apps.accounts.services import seed_roles_and_permissions
    seed_roles_and_permissions()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_seed_phase5_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_phase6, migrations.RunPython.noop),
    ]

