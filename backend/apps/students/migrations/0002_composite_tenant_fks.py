"""Enforce composite tenant foreign keys on student_profiles in PostgreSQL."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0001_initial"),
        ("tenancy", "0001_initial"),
        ("academics", "0002_composite_tenant_fks"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE student_profiles
              ADD CONSTRAINT fk_student_membership_tenant
              FOREIGN KEY (membership_id, institution_id)
              REFERENCES memberships(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE student_profiles
              ADD CONSTRAINT fk_student_cohort_tenant
              FOREIGN KEY (cohort_id, institution_id)
              REFERENCES cohorts(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE student_profiles DROP CONSTRAINT IF EXISTS fk_student_cohort_tenant;
            ALTER TABLE student_profiles DROP CONSTRAINT IF EXISTS fk_student_membership_tenant;
            """,
        ),
    ]

