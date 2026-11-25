-- MCA Career Compass: PostgreSQL Phase 1 foundation schema
-- Version 1.0. Review and adapt through Django migrations in the application.
-- Uses UUIDs. Requires PostgreSQL 13+.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE institutions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(40) NOT NULL UNIQUE,
  name VARCHAR(200) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','suspended')),
  timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
  settings JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Global identity. Django's custom User model should be created before first migration.
CREATE TABLE app_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(254) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL DEFAULT '',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(60) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  scope VARCHAR(20) NOT NULL CHECK (scope IN ('platform','institution'))
);

INSERT INTO roles(code,name,scope) VALUES
 ('PLATFORM_SUPER_ADMIN','Platform Super Admin','platform'),
 ('INSTITUTION_ADMIN','Institution Admin','institution'),
 ('ASSESSMENT_ADMIN','Assessment Admin','institution'),
 ('FACULTY_HOD','Faculty / HOD','institution'),
 ('STUDENT','Student','institution');

CREATE TABLE memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  user_id UUID NOT NULL REFERENCES app_users(id),
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','pending')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(institution_id,user_id),
  UNIQUE(id,institution_id)
);

CREATE TABLE membership_roles (
  membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id),
  assigned_by UUID REFERENCES app_users(id),
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(membership_id,role_id)
);

CREATE TABLE platform_roles (
  user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id),
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(user_id,role_id)
);

CREATE TABLE programmes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  code VARCHAR(40) NOT NULL,
  name VARCHAR(160) NOT NULL,
  level VARCHAR(40) NOT NULL DEFAULT 'PG',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(institution_id,code),
  UNIQUE(id,institution_id)
);

CREATE TABLE academic_years (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  name VARCHAR(40) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  CHECK(end_date >= start_date),
  UNIQUE(institution_id,name),
  UNIQUE(id,institution_id)
);

CREATE TABLE cohorts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  programme_id UUID NOT NULL,
  academic_year_id UUID NOT NULL,
  batch_name VARCHAR(100) NOT NULL,
  semester SMALLINT CHECK (semester BETWEEN 1 AND 8),
  section VARCHAR(30) NOT NULL DEFAULT 'A',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(programme_id,institution_id) REFERENCES programmes(id,institution_id),
  FOREIGN KEY(academic_year_id,institution_id) REFERENCES academic_years(id,institution_id),
  UNIQUE(id,institution_id)
);

CREATE TABLE student_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  user_id UUID NOT NULL,
  cohort_id UUID,
  registration_no VARCHAR(80) NOT NULL,
  admission_year SMALLINT,
  phone VARCHAR(30),
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(user_id,institution_id) REFERENCES memberships(user_id,institution_id)
    DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(cohort_id,institution_id) REFERENCES cohorts(id,institution_id),
  UNIQUE(institution_id,registration_no),
  UNIQUE(user_id,institution_id),
  UNIQUE(id,institution_id)
);

CREATE TABLE faculty_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  user_id UUID NOT NULL,
  employee_code VARCHAR(80),
  department VARCHAR(120),
  designation VARCHAR(120),
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(user_id,institution_id) REFERENCES memberships(user_id,institution_id)
    DEFERRABLE INITIALLY DEFERRED,
  UNIQUE(institution_id,employee_code),
  UNIQUE(user_id,institution_id),
  UNIQUE(id,institution_id)
);

CREATE TABLE cohort_faculty (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  cohort_id UUID NOT NULL,
  faculty_profile_id UUID NOT NULL,
  assignment_type VARCHAR(40) NOT NULL DEFAULT 'mentor',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(cohort_id,institution_id) REFERENCES cohorts(id,institution_id),
  FOREIGN KEY(faculty_profile_id,institution_id) REFERENCES faculty_profiles(id,institution_id),
  UNIQUE(cohort_id,faculty_profile_id,assignment_type)
);

CREATE TABLE audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID REFERENCES institutions(id),
  actor_user_id UUID REFERENCES app_users(id),
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(100) NOT NULL,
  entity_id UUID,
  before_json JSONB,
  after_json JSONB,
  ip_hash VARCHAR(128),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE import_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id),
  created_by UUID NOT NULL REFERENCES app_users(id),
  file_name VARCHAR(255) NOT NULL,
  status VARCHAR(20) NOT NULL CHECK(status IN ('uploaded','validated','committed','failed','cancelled')),
  total_rows INTEGER NOT NULL DEFAULT 0 CHECK(total_rows >= 0),
  success_rows INTEGER NOT NULL DEFAULT 0 CHECK(success_rows >= 0),
  error_rows INTEGER NOT NULL DEFAULT 0 CHECK(error_rows >= 0),
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE import_row_errors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  import_job_id UUID NOT NULL REFERENCES import_jobs(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  field_name VARCHAR(100),
  error_code VARCHAR(80) NOT NULL,
  message TEXT NOT NULL,
  row_data JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_memberships_user_status ON memberships(user_id,status);
CREATE INDEX idx_memberships_institution_status ON memberships(institution_id,status);
CREATE INDEX idx_cohorts_institution_programme ON cohorts(institution_id,programme_id);
CREATE INDEX idx_students_institution_cohort ON student_profiles(institution_id,cohort_id);
CREATE INDEX idx_students_registration ON student_profiles(institution_id,registration_no);
CREATE INDEX idx_faculty_institution_department ON faculty_profiles(institution_id,department);
CREATE INDEX idx_audit_tenant_created ON audit_events(institution_id,created_at DESC);
CREATE INDEX idx_import_jobs_tenant_created ON import_jobs(institution_id,created_at DESC);

-- NOTE:
-- 1) The production Django implementation should use a custom AUTH_USER_MODEL from day one.
-- 2) The composite membership FK above is illustrative; implement tenant-safe constraints
--    using explicit membership/profile relationships in Django models and migrations.
-- 3) Do not expose this SQL as a substitute for backend authorization.
-- 4) Add assessment/question/attempt tables in Phase 2/3 after scoring rules are approved.
