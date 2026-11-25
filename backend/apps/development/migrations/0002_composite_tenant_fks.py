"""Enforce composite tenant foreign keys on development_plans and development_activities."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("development", "0001_initial"),
        ("students", "0002_composite_tenant_fks"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE development_plans
              ADD CONSTRAINT fk_dev_plan_student_tenant
              FOREIGN KEY (student_profile_id, institution_id)
              REFERENCES student_profiles(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE development_activities
              ADD CONSTRAINT fk_dev_act_plan_tenant
              FOREIGN KEY (plan_id, institution_id)
              REFERENCES development_plans(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE development_activities DROP CONSTRAINT IF EXISTS fk_dev_act_plan_tenant;
            ALTER TABLE development_plans DROP CONSTRAINT IF EXISTS fk_dev_plan_student_tenant;
            """,
        ),
    ]

