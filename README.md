# MCA Career Compass

**Institutional MCA Student Talent Mapping & Empowerment Platform**

MCA Career Compass is a multi-institution-capable platform for assessing MCA students across technical disciplines, cognitive/problem-solving capabilities, professional/soft skills, and career interests while keeping **Demonstrated Performance**, **Self-Reported Proficiency**, and **Stated Career Interest** strictly separated.

> **Current Status:** Phases 1–6 Completed & Verified — Multi-Institution Tenancy & RBAC, Dynamic Assessments, Test Delivery & Evaluation, Analytics & CSV/XLSX/PDF Exports, Student Empowerment & Development Plans, and Institutional Intelligence / Pre-Post Comparison / Placement Readiness / Executive Reports.

---

## Technology Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS + React Router + Axios (`http://localhost:5173`)
- **Backend:** Python + Django + Django REST Framework (`http://localhost:8000/api/v1/`)
- **Database:** PostgreSQL 13+ (`localhost:5432`) with UUID primary keys and strict logical tenant isolation

---

## Prerequisites (Windows)

Verify each tool in PowerShell before setup:

```powershell
python --version   # Python 3.12+ (3.13 / 3.14 supported)
node --version     # Node.js 20+ LTS
npm --version      # npm 10+
psql --version     # PostgreSQL 13+
git --version      # Git
```

---

## Local Development Setup (Windows PowerShell)

### 1. Create PostgreSQL Database & Least-Privileged User

Connect to PostgreSQL as `postgres` (e.g., via `psql -U postgres` or pgAdmin) and run:

```sql
CREATE USER mca_compass_user WITH PASSWORD 'your_strong_local_password';
CREATE DATABASE mca_career_compass OWNER mca_compass_user;
GRANT ALL PRIVILEGES ON DATABASE mca_career_compass TO mca_compass_user;
```

### 2. Configure Environment Variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your `DJANGO_SECRET_KEY`, `AUDIT_IP_HMAC_KEY`, and PostgreSQL credentials.

### 3. Backend Setup (Django + DRF)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\manage.py check
python backend\manage.py migrate
python backend\manage.py create_platform_admin --email superadmin@compass.local --first-name Platform --last-name Admin
# Optional: seed synthetic development data (MITT & DEMOB) when DJANGO_DEBUG=True
python backend\manage.py seed_dev_data
python backend\manage.py runserver 8000
```

### 4. Frontend Setup (React + TypeScript + Vite)

In a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Visit:
- Frontend App: `http://localhost:5173`
- Admin Login: `http://localhost:5173/admin/login`
- Faculty / Student Login: `http://localhost:5173/login`
- Backend Health Check: `http://localhost:8000/api/v1/health/` (or via Vite proxy at `http://localhost:5173/api/v1/health/`)

---

## Running Verification Checks

### Backend
```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python manage.py check
python manage.py test
```

### Frontend
```powershell
cd frontend
npx tsc --noEmit
npm run build
```

---

## Documentation Index

- [AGENTS.md](AGENTS.md) — Permanent engineering rules, security boundaries, and phase boundaries
- [docs/concept-document.md](docs/concept-document.md) — Project Concept Document (vision, measurement separation, lifecycle, and architecture)
- [docs/user-manual.md](docs/user-manual.md) — Complete User Manual (URLs, demo accounts, role-by-role walkthrough, and 10-step guided tour)
- [docs/architecture.md](docs/architecture.md) — Multi-institution system architecture
- [docs/database-schema.md](docs/database-schema.md) — Corrected Phase 1 schema & composite FK design
- [docs/permissions.md](docs/permissions.md) — Roles and granular permission matrix
- [docs/phase-1-plan.md](docs/phase-1-plan.md) — Phase 1 milestones and acceptance criteria
- [docs/deployment-ubuntu-oracle.md](docs/deployment-ubuntu-oracle.md) — Automated GitHub + Ubuntu / Oracle Cloud deployment guide

