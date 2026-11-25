# Phase 1 Implementation Plan & Acceptance Checklist

- **M1: Repo, Environment & DB Foundation** — Repo init, `.env.example`, Django + DRF + PostgreSQL config, Vite + React + TS + Tailwind setup, `/api/v1/health/`, docs.
- **M2: Identity, Tenancy & RBAC** — Custom `User`, `Institution`, `Membership`, `Role`, `Permission`, session+CSRF auth (`/admin/login`, `/login`), institution switching, password reset/change, RBAC enforcement.
- **M3: Platform & Institution Admin Portals** — Super Admin & Institution Admin dashboards (live DB metrics), institution CRUD, institution admin provisioning, user & role management.
- **M4: Academic Structure, Student & Faculty CRUD** — Programmes, academic years, cohorts, manual student CRUD, duplicate registration detection, faculty CRUD, cohort-faculty assignment & scoping, student personal dashboard.
- **M5: Staged Excel/CSV Bulk Import** — Template download, upload, column mapping, validation preview, duplicate detection, transactional commit, job history, password-free error report export.
- **M6: Audit Logging & Verification Suite** — Append-only `AuditEvent`, IP HMAC hashing, secret scrubbing, audit log viewer, synthetic seed command (`MIT Thandavapura` & `Demo Institute B`), full automated test verification.

