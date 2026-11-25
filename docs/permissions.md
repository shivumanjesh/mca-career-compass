# Roles & Granular Permission Catalogue

## 1. Canonical Roles

| Role Code | Name | Scope | Login Portal |
| --- | --- | --- | --- |
| `PLATFORM_SUPER_ADMIN` | Platform Super Admin | `platform` | `/admin/login` |
| `INSTITUTION_ADMIN` | Institution Admin | `institution` | `/admin/login` |
| `ASSESSMENT_ADMIN` | Assessment Admin | `institution` | `/admin/login` |
| `FACULTY_HOD` | Faculty / HOD | `institution` | `/login` |
| `STUDENT` | Student | `institution` | `/login` |

## 2. Phase 1 Enforced Permission Codes

- `platform.institution.manage` — Create/edit/activate/deactivate institutions
- `platform.admin.manage` — Create/manage Institution Admins
- `audit.platform.view` — View platform-level audit events
- `institution.profile.manage` — View/update active institution profile
- `institution.user.manage` — Create/edit/deactivate institution users and assign/revoke institution roles
- `academics.cohort.manage` — Manage programmes, academic years, and cohorts
- `institution.student.manage` — Create/edit/deactivate students
- `institution.student.import` — Upload, validate, commit, and view student bulk imports
- `institution.faculty.manage` — Create/edit/deactivate faculty and manage cohort assignments
- `student.assigned.view` — View students in assigned cohorts (Faculty / HOD)
- `student.self.view` — View own student profile (Student)
- `audit.institution.view` — View active institution audit events

Backend views enforce permission codes via DRF permission classes—never UI hiding alone.

