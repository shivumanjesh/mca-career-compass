"""Enforce composite tenant foreign keys on assessment_dimensions and assessment_versions."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE assessment_dimensions
              ADD CONSTRAINT fk_dimension_category_tenant
              FOREIGN KEY (category_id, institution_id)
              REFERENCES assessment_categories(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE assessment_versions
              ADD CONSTRAINT fk_version_template_tenant
              FOREIGN KEY (template_id, institution_id)
              REFERENCES assessment_templates(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE assessment_versions DROP CONSTRAINT IF EXISTS fk_version_template_tenant;
            ALTER TABLE assessment_dimensions DROP CONSTRAINT IF EXISTS fk_dimension_category_tenant;
            """,
        ),
    ]

