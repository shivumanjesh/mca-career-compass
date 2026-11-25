"""Enforce composite tenant foreign keys on faculty_profiles and cohort_faculty in PostgreSQL."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("faculty", "0001_initial"),
        ("tenancy", "0001_initial"),
        ("academics", "0002_composite_tenant_fks"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE faculty_profiles
              ADD CONSTRAINT fk_faculty_membership_tenant
              FOREIGN KEY (membership_id, institution_id)
              REFERENCES memberships(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE cohort_faculty
              ADD CONSTRAINT fk_cohort_faculty_cohort_tenant
              FOREIGN KEY (cohort_id, institution_id)
              REFERENCES cohorts(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE cohort_faculty
              ADD CONSTRAINT fk_cohort_faculty_profile_tenant
              FOREIGN KEY (faculty_profile_id, institution_id)
              REFERENCES faculty_profiles(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE cohort_faculty DROP CONSTRAINT IF EXISTS fk_cohort_faculty_profile_tenant;
            ALTER TABLE cohort_faculty DROP CONSTRAINT IF EXISTS fk_cohort_faculty_cohort_tenant;
            ALTER TABLE faculty_profiles DROP CONSTRAINT IF EXISTS fk_faculty_membership_tenant;
            """,
        ),
    ]

