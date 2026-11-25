"""Enforce composite tenant foreign keys on assessment_attempts."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("attempts", "0001_initial"),
        ("assessments", "0004_assignment_composite_fks"),
        ("students", "0002_composite_tenant_fks"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE assessment_attempts
              ADD CONSTRAINT fk_attempt_assignment_tenant
              FOREIGN KEY (assignment_id, institution_id)
              REFERENCES assessment_assignments(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE assessment_attempts
              ADD CONSTRAINT fk_attempt_student_tenant
              FOREIGN KEY (student_profile_id, institution_id)
              REFERENCES student_profiles(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE assessment_attempts DROP CONSTRAINT IF EXISTS fk_attempt_student_tenant;
            ALTER TABLE assessment_attempts DROP CONSTRAINT IF EXISTS fk_attempt_assignment_tenant;
            """,
        ),
    ]

