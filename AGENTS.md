# AGENTS.md — MCA Career Compass Engineering Charter

This document defines the permanent architecture, security boundaries, coding conventions, phase boundaries, and verification rules for **MCA Career Compass** (Institutional MCA Student Talent Mapping & Empowerment Platform).

Every contributor and AI coding agent working in this repository **must** read and follow this file.

---

## 1. Product & Ethical Guardrails

- **Purpose**: Institutional MCA student assessment, talent mapping, and personalized development empowerment across technical disciplines, cognitive/problem-solving skills, soft skills, and career interests.
- **Measurement Separation**: Keep **Demonstrated Performance** (objective/rubric-scored capability), **Self-Reported Proficiency** (Likert/perceived ratings), and **Stated Career Interest** as strictly separate measurement families. Never collapse them into a single undocumented psychometric score.
- **Non-Clinical Boundary**: Never claim clinical or validated psychological diagnosis from educational assessment scores.
- **No Fake Data or Stubs**: Never ship hardcoded dashboard metrics, placeholder buttons that do nothing, or mock API responses masquerading as live data.

---

## 2. Technology Stack & Local Topology

| Layer | Technology | Local Address |
| --- | --- | --- |
| Frontend | React + TypeScript + Vite + Tailwind CSS + React Router + Axios | `http://localhost:5173` |
| Backend | Python + Django + Django REST Framework | `http://localhost:8000/api/v1/` |
| Database | PostgreSQL (13+), UUID PKs, UTC timestamps (`TIMESTAMPTZ`) | `localhost:5432` |
| Environment | Windows (PowerShell), portable via `.env` | — |

- Do **not** introduce microservices, NoSQL databases, or unnecessary third-party frameworks.
- Keep all configuration environment-driven (`.env` / `.env.example`). Never hardcode secrets, credentials, or local absolute paths.

---

## 3. Repository Structure

```text
mca-career-compass/
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── docs/                                # Architecture, schema, permissions, phase plans
├── scripts/                             # Local dev/seed/verification scripts
├── backend/
│   ├── manage.py
│   ├── config/                          # Django settings, urls, wsgi/asgi
│   └── apps/
│       ├── core/                        # Abstract base models, health check, exceptions, pagination
│       ├── tenancy/                     # Institution, Membership, tenant context resolution
│       ├── accounts/                    # Custom User, Role, Permissions, Auth endpoints
│       ├── academics/                   # Programme, AcademicYear, Cohort
│       ├── students/                    # StudentProfile management
│       ├── faculty/                     # FacultyProfile, CohortFaculty assignments
│       ├── imports/                     # ImportJob, ImportRowError, XLSX/CSV parser & commit
│       └── audit/                       # Append-only AuditEvent logging & query APIs
└── frontend/
    └── src/
        ├── app/                         # Router, Auth/Tenant providers, layouts, protected routes
        ├── components/                  # Reusable institutional UI primitives & data tables
        ├── features/                    # Domain-scoped screens & hooks
        │   ├── auth/
        │   ├── dashboard/
        │   ├── institutions/
        │   ├── users/
        │   ├── academics/
        │   ├── students/
        │   ├── faculty/
        │   ├── imports/
        │   └── audit/
        ├── services/                    # Typed Axios API clients
        └── types/                       # Shared TypeScript interfaces/DTOs
```

Future phase Django apps (`assessments`, `attempts`, `analytics`, `development`) will plug into `backend/apps/` without modifying Phase 1 core identity or tenant tables.

---

## 4. Multi-Institution Tenancy & Security Rules (Non-Negotiable)

1. **Shared Database, Strict Logical Isolation**: Every tenant-owned table includes an `institution_id` foreign key and composite `(id, institution_id)` uniqueness where referenced by child tables.
2. **Server-Derived Tenant Context**:
   - Never trust an `institution_id` supplied in a client request body, query param, or URL to grant access to an institution's data.
   - Always derive `active_institution` and `active_membership` server-side from the authenticated user's session and verified active `Membership`.
   - Deny by default if tenant context is missing on any tenant-scoped endpoint.
3. **Database & Migration Discipline**:
   - Django models and Django migrations are the single authoritative source of database schema.
   - Custom `AUTH_USER_MODEL` (`accounts.User`, `db_table = "app_users"`) **must** exist before the first migration.
   - Use UUID primary keys (`UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`).
   - Enforce composite tenant integrity `(child_fk, institution_id) -> parent(id, institution_id)` in PostgreSQL via migration SQL alongside Django ORM `OneToOneField`/`ForeignKey` + model/serializer validation.
   - Never cascade-delete historical records; use `on_delete=models.PROTECT` for core entities and soft deactivation (`is_active=False` / `status='inactive'`) to preserve audit & assessment history.
4. **Authentication & RBAC**:
   - Separate login entry points: `/admin/login` (Platform Super Admin, Institution Admin, Assessment Admin) and `/login` (Faculty / HOD, Student).
   - Enforce granular permission codes (e.g., `institution.student.manage`, `academics.cohort.manage`, `audit.institution.view`) on every backend view/viewset—never rely on UI hiding alone.
   - Role assignments are strictly scoped: `platform` roles live in `PlatformRole`; `institution` roles live in `MembershipRole` bound to a specific `Membership`.
   - Faculty/HOD access is restricted to students in their assigned `CohortFaculty` cohorts (unless granted broader explicit institution permission).
   - Student endpoints must derive `StudentProfile` from `request.active_membership`, never from a URL/query student ID.
5. **Credential & Upload Hygiene**:
   - Never store, log, email, or export plaintext passwords, tokens, or secrets in spreadsheets, API responses, or `AuditEvent` payloads.
   - Bulk-imported accounts start with unusable passwords and require secure reset/onboarding tokens.
   - Validate uploaded `.xlsx` / `.csv` files for extension, MIME/header sanity, size limits, and formula-injection sanitization on CSV exports.
6. **Audit Trail**:
   - Every critical mutation (institution create/status change, user creation/deactivation, role assignment/revocation, student/faculty lifecycle changes, cohort assignment, bulk import upload/commit/failure) must emit an `AuditEvent` inside or right after the transaction, stripping any sensitive keys (`password`, `token`, `secret`).

---

## 5. Coding Conventions

### Backend (Django / DRF)
- Python 3.12+ (compatible with installed Python 3.13/3.14), PEP 8, type hints on service functions.
- Thin views/viewsets; place business logic, transactions (`transaction.atomic()`), and audit calls in dedicated `services.py` modules.
- Base all tenant-scoped querysets on a tenant-aware manager/helper (`queryset.filter(institution=request.active_institution)`).
- Return consistent structured JSON errors (`code`, `message`, `details`).
- Prefix all REST routes with `/api/v1/`.

### Frontend (React / TypeScript)
- Strict TypeScript (`strict: true`); no `any` in API contracts or domain models.
- Centralized Axios client with CSRF handling, credentialed requests (`withCredentials: true`), and unified error parsing.
- Institutional UI aesthetic: clean light/white surfaces, navy/slate primary (`#0F2942` / `#1E3A5F`), blue interactive controls, teal accents (`#0D9488`), responsive layout, accessible labels, explicit loading/empty/error states.
- All list views support search, filters, and pagination backed by live API endpoints.

---

## 6. Phase Boundaries

- **Phase 1 (COMPLETED & VERIFIED)**: Repo & environment setup, PostgreSQL config, custom `User` & tenancy models, authentication & RBAC, Platform Super Admin portal, Institution Admin portal, Academic structure (Programmes, Academic Years, Cohorts/Batches/Semesters/Sections), Manual Student & Faculty management, Cohort-Faculty assignment, Staged Excel/CSV import, Audit logging, Automated security/isolation/functional tests.
- **Phase 2 (COMPLETED & VERIFIED)**: Assessment categories, dimensions (with strict measurement-family separation), skill tags, dynamic question bank (MCQ, true/false, numeric, Likert, self-rating, situational judgement, descriptive, coding), marks/negative-marking/rubric scoring configuration, assessment template builder, immutable published versioning, and publishing.
- **Phase 3 (COMPLETED & VERIFIED)**: Assessment assignments (cohort or student target), student test runner, question navigation, server-authoritative timer, idempotent autosave and submission, objective scoring from immutable snapshots, and faculty/admin manual rubric evaluation.
- **Phase 4 (COMPLETED & VERIFIED)**: Individual student reports, domain-wise assessment results (with strict measurement-family separation), student comparison, cohort analytics, strength and weakness analysis, and exportable CSV/XLSX/PDF reports.
- **Phase 5 (COMPLETED & VERIFIED)**: Evidence-cited domain-fit recommendations, learning pathways, training/project/certification catalogue, student & faculty development plans, and milestone/progress reflection tracking.
- **Phase 6 (COMPLETED & VERIFIED)**: Faculty & HOD intelligence dashboards, institution-level executive reports, pre/post assessment comparison, placement readiness indicators, and executive exports.

All Phases 1–6 capabilities are migrated on PostgreSQL and verified with automated tests and frontend production builds.

---

## 7. Verification & Definition of Done

Before marking any milestone or task complete:
1. Database migrations are generated and cleanly applied on PostgreSQL.
2. Backend automated tests pass (authentication, RBAC permissions, cross-institution isolation, duplicate registration detection, Excel import validation & transaction safety, faculty cohort scoping, audit logging).
3. Frontend TypeScript compilation (`tsc --noEmit`) and production build (`npm run build`) pass with zero errors.
4. End-to-end flows are verified against the running backend and PostgreSQL database using synthetic test data only.
5. Documentation (`README.md`, `.env.example`, `docs/`) accurately reflects commands and behavior.

