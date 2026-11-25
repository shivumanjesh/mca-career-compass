"""Enforce composite tenant foreign keys on cohorts in PostgreSQL."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE cohorts
              ADD CONSTRAINT fk_cohort_programme_tenant
              FOREIGN KEY (programme_id, institution_id)
              REFERENCES programmes(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE cohorts
              ADD CONSTRAINT fk_cohort_academic_year_tenant
              FOREIGN KEY (academic_year_id, institution_id)
              REFERENCES academic_years(id, institution_id)
              DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE cohorts DROP CONSTRAINT IF EXISTS fk_cohort_academic_year_tenant;
            ALTER TABLE cohorts DROP CONSTRAINT IF EXISTS fk_cohort_programme_tenant;
            """,
        ),
    ]

