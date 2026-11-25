# System Architecture — MCA Career Compass

## 1. Logical Layers

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Presentation | React, TypeScript, Vite, Tailwind CSS, React Router, Axios | Responsive role-based portals (`/admin/login`, `/login`), live API views |
| API / Application | Django + Django REST Framework | REST endpoints (`/api/v1/`), service layer, serializers, RBAC, tenant resolution |
| Identity & Access | Django Session Auth + CSRF + Custom `User` + Granular Permissions | Secure password hashing, session-bound institution context, immediate revocation |
| Data | PostgreSQL 13+ | UUID primary keys, UTC `TIMESTAMPTZ`, composite tenant FKs, migrations |

## 2. Local Development Topology

- React/Vite dev server: `http://localhost:5173` (proxies `/api/*` to `http://localhost:8000`)
- Django API server: `http://localhost:8000/api/v1/`
- PostgreSQL: `localhost:5432` (accessed solely by Django backend)

## 3. Multi-Institution Isolation Model

- **Shared database, strict logical isolation**: every tenant-owned model stores `institution_id`.
- **Server-derived tenant context**: `active_institution_id` is stored in the server-side session after verifying an active `Membership` for the authenticated user. Client-supplied `institution_id` parameters are never trusted for tenant authorization.
- **Database defense-in-depth**: composite unique keys `(id, institution_id)` paired with composite foreign keys `(child_fk, institution_id) -> parent(id, institution_id)` guarantee cross-tenant links cannot exist even at the SQL layer.

## 4. Future Phase Extensibility

Phase 1 apps (`core`, `tenancy`, `accounts`, `academics`, `students`, `faculty`, `imports`, `audit`) establish clean extension points so Phase 2+ (`assessments`, `attempts`, `analytics`, `development`) plug in without altering identity or tenant tables.

