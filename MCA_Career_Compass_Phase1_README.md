# MCA Career Compass – Phase 1 Starter

## Selected architecture
- Frontend: React + TypeScript + Vite
- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Initial deployment: local Windows
- Tenancy: shared database, institution-scoped records
- Onboarding: manual + Excel/CSV import

## Local service addresses
- Frontend: http://localhost:5173
- Backend: http://localhost:8000/api/v1/
- PostgreSQL: localhost:5432

## Phase 1 sequence
1. Repository and environment setup
2. Custom Django user model and tenant models
3. Authentication and institution context
4. Role/permission catalogue and API enforcement
5. Institution, programme, academic year and cohort management
6. Manual student/faculty management
7. Spreadsheet preview, validation and transactional import
8. Audit events, tests and documentation

## Important implementation rules
- Create a custom Django user model before the first migration.
- Derive institution scope from authenticated membership; never trust tenant IDs supplied by the client.
- Use synthetic data during development.
- Do not store plaintext passwords or email passwords.
- Keep published assessment versions immutable when assessment modules are added.
- Separate demonstrated performance, self-reported proficiency and career interest.
- Use migrations as the source of truth for database schema; do not manually edit production tables.
