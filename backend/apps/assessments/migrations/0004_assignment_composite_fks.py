"""Enforce composite tenant foreign keys on assessment_assignments."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0003_assessmentassignment"),
        ("academics", "0002_composite_tenant_fks"),
        ("students", "0002_composite_tenant_fks"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE assessment_assignments
              ADD CONSTRAINT fk_assign_version_tenant
              FOREIGN KEY (assessment_version_id, institution_id)
              REFERENCES assessment_versions(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE assessment_assignments
              ADD CONSTRAINT fk_assign_cohort_tenant
              FOREIGN KEY (cohort_id, institution_id)
              REFERENCES cohorts(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE assessment_assignments
              ADD CONSTRAINT fk_assign_student_tenant
              FOREIGN KEY (student_profile_id, institution_id)
              REFERENCES student_profiles(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE assessment_assignments DROP CONSTRAINT IF EXISTS fk_assign_student_tenant;
            ALTER TABLE assessment_assignments DROP CONSTRAINT IF EXISTS fk_assign_cohort_tenant;
            ALTER TABLE assessment_assignments DROP CONSTRAINT IF EXISTS fk_assign_version_tenant;
            """,
        ),
    ]

