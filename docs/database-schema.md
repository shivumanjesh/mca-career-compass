# Phase 1 Database Design & Composite FK Corrections

## 1. Authoritative Schema Source

Django models and Django migrations are the single source of truth for the PostgreSQL schema. The uploaded [MCA_Career_Compass_Phase1_Schema.sql](../MCA_Career_Compass_Phase1_Schema.sql) served as the logical starter blueprint and underwent the following structural corrections before implementation:

## 2. Composite Foreign-Key Correction (`student_profiles` / `faculty_profiles` -> `memberships`)

- **Starter Schema Issue:** `student_profiles` and `faculty_profiles` stored `(user_id, institution_id)` with `FOREIGN KEY (user_id, institution_id) REFERENCES memberships(user_id, institution_id)` rather than referencing `memberships.id`, duplicating `user_id` and conflicting with Django's single-column ORM `OneToOneField`/`ForeignKey`.
- **Corrected Design:**
  1. `StudentProfile` and `FacultyProfile` hold `membership = OneToOneField(Membership, on_delete=PROTECT)` and `institution = ForeignKey(Institution, on_delete=PROTECT)`.
  2. `Membership` retains `UNIQUE(id, institution_id)` and `UNIQUE(institution_id, user_id)`.
  3. Django migrations add PostgreSQL composite constraints via `RunSQL`:
     - `FOREIGN KEY (membership_id, institution_id) REFERENCES memberships(id, institution_id)`
     - `FOREIGN KEY (cohort_id, institution_id) REFERENCES cohorts(id, institution_id)`
     - `FOREIGN KEY (programme_id, institution_id) REFERENCES programmes(id, institution_id)`
     - `FOREIGN KEY (academic_year_id, institution_id) REFERENCES academic_years(id, institution_id)`
     - `FOREIGN KEY (faculty_profile_id, institution_id) REFERENCES faculty_profiles(id, institution_id)`

## 3. Additional Phase 1 Schema Enhancements

- `cohorts` enforces `UNIQUE(institution_id, programme_id, academic_year_id, batch_name, semester, section)`.
- Consistent `status` choices across `institutions`, `memberships`, `programmes`, `academic_years`, `cohorts`, `student_profiles`, `faculty_profiles`.
- `faculty_profiles.employee_code` normalizes blank values to `NULL` and uses a partial unique index `WHERE employee_code IS NOT NULL`.
- `on_delete=models.PROTECT` on all core historical records; soft deactivation preserves audit and future assessment history.

