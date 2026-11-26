# User Manual — MCA Career Compass

**Peer Testing & Complete Step-by-Step Guide (Phases 1–6 — HTTPS Edition)**

---

## 1. Access Links (HTTPS URLs)

Use the **Live Server (HTTPS)** links below when testing and exploring the deployed application:

| Entry Point | Live Server (HTTPS) | Local Development | Who Signs In Here? |
| --- | --- | --- | --- |
| **Landing & Health Status** | `https://140.238.246.25/` | `http://localhost:5173/` | Public home page & live backend health check |
| **Admin Portal** | `https://140.238.246.25/admin/login` | `http://localhost:5173/admin/login` | Institution Admin, Assessment Admin |
| **Academic Portal** | `https://140.238.246.25/login` | `http://localhost:5173/login` | Faculty / HOD and Students |
| **Password Reset Page** | `https://140.238.246.25/reset-password` | `http://localhost:5173/reset-password` | Users confirming a reset/onboarding token |

> **First-Time HTTPS Browser Notice:** While the temporary self-signed certificate is active before domain purchase, Chrome/Edge will display *"Your connection is not private"* on your first visit. Click **Advanced → Proceed to 140.238.246.25 (unsafe)** once to enter the encrypted HTTPS site.

> **Important Portal Rule:** Administrative accounts **must** sign in at `https://140.238.246.25/admin/login`. Faculty and Student accounts **must** sign in at `https://140.238.246.25/login`. Signing in through the wrong portal intentionally denies access.

---

## 2. Peer Testing Login Credentials (All Roles Except Super Admin)

Use the accounts below to explore every institutional workflow across **`MITT`** (*Maharaja Institute of Technology Thandavapura*). *(Platform Super Admin credentials are restricted to the platform owner and intentionally excluded from peer testing.)*

| Role | Portal URL | Institution Code | Username / Registration No. | Test Password | Assigned Scope |
| --- | --- | --- | --- | --- | --- |
| **Institution Admin** | `https://140.238.246.25/admin/login` | `MITT` | `admin@mitt.local` | `PeerTest@2026!` | Full `MITT` institution management & executive reports |
| **Assessment Admin** | `https://140.238.246.25/admin/login` | `MITT` | `assessment@mitt.local` | `PeerTest@2026!` | Dimensions, question bank, templates, assignments, evaluation, catalogue, executive reports |
| **Faculty / HOD (Sec A)** | `https://140.238.246.25/login` | `MITT` | `kavitha.faculty@mitt.local` | `PeerTest@2026!` | Assigned strictly to `MCA 2025-2027 Sem 1 Sec A` |
| **Faculty / Mentor (Sec B)** | `https://140.238.246.25/login` | `MITT` | `rajesh.faculty@mitt.local` | `PeerTest@2026!` | Assigned strictly to `MCA 2025-2027 Sem 1 Sec B` |
| **Student 1 (Sec A)** | `https://140.238.246.25/login` | `MITT` | `aarav.sharma@mitt.local` or `4MT25MC001` | `PeerTest@2026!` | Self-only (`Sem 1 Sec A`) |
| **Student 2 (Sec A)** | `https://140.238.246.25/login` | `MITT` | `bhavana.nair@mitt.local` or `4MT25MC002` | `PeerTest@2026!` | Self-only (`Sem 1 Sec A`) |
| **Student 3 (Sec A)** | `https://140.238.246.25/login` | `MITT` | `chetan.patil@mitt.local` or `4MT25MC003` | `PeerTest@2026!` | Self-only (`Sem 1 Sec A`) |
| **Student 4 (Sec B)** | `https://140.238.246.25/login` | `MITT` | `divya.rao@mitt.local` or `4MT25MC004` | `PeerTest@2026!` | Self-only (`Sem 1 Sec B`) |
| **Student 5 (Sec B)** | `https://140.238.246.25/login` | `MITT` | `eshan.verma@mitt.local` or `4MT25MC005` | `PeerTest@2026!` | Self-only (`Sem 1 Sec B`) |

*(For **local developer** testing on `http://localhost:5173/`, run `.\.venv\Scripts\python.exe backend\manage.py seed_dev_data --password "PeerTest@2026!"` when `DJANGO_DEBUG=True`.)*

---

## 3. Role 1 — Institution Admin Walkthrough

Sign in at **`https://140.238.246.25/admin/login`** with Institution Code **`MITT`**, Email **`admin@mitt.local`**, Password **`PeerTest@2026!`**:

1. **Institution Profile (`/institution/profile`)**: Update institution name, timezone, and institutional metadata.
2. **Users & Roles (`/institution/users`)**:
   - Create users and assign/revoke institution roles (`INSTITUTION_ADMIN`, `ASSESSMENT_ADMIN`, `FACULTY_HOD`, `STUDENT`).
   - Deactivate or trigger password resets cleanly; role changes take effect immediately on the user's next request.
3. **Academic Structure (`/academics`)**:
   - Create a **Programme** (e.g., `MCA`).
   - Create an **Academic Year** (e.g., `2025-26`, start `2025-08-01`, end `2026-07-31`).
   - Create **Cohorts** (e.g., Batch `2025-2027`, Semester `1`, Section `A` and Section `B`).
4. **Students (`/students`) & Bulk Import (`/students/import`)**:
   - Manually add students (with unique `registration_no` per institution and cohort assignment), OR
   - Open **Bulk Import** → click **Download XLSX / CSV Template** → upload your filled file → review row-by-row validation preview (valid rows vs errors) → click **Commit Valid Rows** → export error rows if any failed.
5. **Faculty (`/faculty`)**:
   - Create Faculty profiles (`employee_code`, department, designation).
   - Click **Assign Cohort** to bind a Faculty / HOD strictly to specific cohorts (`Mentor`, `HOD`, `Faculty`, `Coordinator`).
6. **Executive Reports (`/executive-reports`)**: View full institutional rollup across all cohorts and export CSV, XLSX, or PDF executive reports (also shared with Assessment Admin).

---

## 4. Role 2 — Assessment Admin Walkthrough

Sign in at **`https://140.238.246.25/admin/login`** with Institution Code **`MITT`**, Email **`assessment@mitt.local`**, Password **`PeerTest@2026!`**:

1. **Dimensions (`/assessments/dimensions`)**:
   - Click **Seed Starter Catalogue** to populate standard MCA categories & dimensions across all three measurement families (`PROG`, `DSA`, `DBMS`, `SE_TEST`, `WEBMOB`, `AIML`, `CLOUDSEC`, `LOGIC`, `ANALYTICAL`, `NUMERICAL`, `DEBUG`, `COMM`, plus Self-Reported & Career Interest dimensions like `INT_SDE`, `INT_AIML`).
   - Or click **+ Add Category** / **+ Add Dimension** to create custom dimensions.
2. **Question Bank (`/assessments/questions`)**:
   - Author questions across 8 supported types: `single_mcq`, `multi_mcq`, `true_false`, `numeric`, `likert`, `self_rating`, `situational_judgement`, `descriptive`, `coding`.
   - Link each question to one or more weighted dimensions matching its measurement family (`Demonstrated Performance` vs `Self-Reported Proficiency` vs `Stated Career Interest`).
   - For `descriptive` and `coding` questions, configure max marks and optional evaluation rubrics.
3. **Assessment Builder (`/assessments/templates`)**:
   - Click **+ New Template** (e.g., *MCA Semester 1 Baseline Assessment*).
   - Open the draft version (`v1`), pick questions from the Question Bank, configure duration (minutes), max attempts, and randomization toggles.
   - Click **Publish Version** to freeze an immutable snapshot (`Published` versions cannot be mutated; editing requires cloning to `v2` Draft).
4. **Assignments (`/assessments/assignments`)**:
   - Click **+ Assign Assessment**, select a published version, target a **Cohort** (or specific Student), set Opens At / Closes At timestamps, and toggle **Release Results to Students** when ready.
5. **Learning Catalogue (`/development/catalogue`)**:
   - Click **Seed Starter Catalogue** to populate institutional Learning Pathways, Remedial Trainings, Capstone Projects, and Certifications mapped to MCA domains and dimension codes, or add/archive custom resources.

---

## 5. Role 3 — Student Walkthrough

Sign in at **`https://140.238.246.25/login`** with Institution Code **`MITT`**, **Email OR Registration No** (e.g., `4MT25MC001` or `aarav.sharma@mitt.local`), Password **`PeerTest@2026!`**:

1. **My Assessments (`/my-assessments`)**:
   - Lists currently active assigned assessments with availability windows and attempt status.
   - Click **Start Assessment** (or **Resume**) to enter the timed Test Runner (`/my-assessments/attempt/:attemptId`).
2. **Test Runner**:
   - Live server-authoritative countdown timer, question navigation palette, unanswered indicator, automatic periodic autosave, and explicit **Submit Assessment** confirmation.
   - Objective items are scored immediately; descriptive/coding answers enter the Faculty Evaluation Queue (`Pending Manual Evaluation`).
3. **My Results (`/my-results`)**:
   - Once the Assignment has **Release Results** enabled, view:
     - **Demonstrated Performance** (overall %, cohort benchmark comparison, strengths `>= 70%`, gaps `< 50%`, dimension bar chart)
     - **Self-Reported Proficiency** (separate `1–5` scale section)
     - **Stated Career Interest** (separate `1–5` scale section)
4. **My Empowerment & Roadmap (`/my-empowerment`)**:
   - Review **Evidence-Cited Career Domain Mapping** (e.g., *Software Development*, *AI / ML Engineering*, *Data Analytics*, *Cloud / DevOps*, *Cybersecurity*, *UI / UX & Web Engineering*) with exact demonstrated % and stated interest ratings.
   - Browse recommended **Learning Pathways**, **Trainings**, **Projects**, and **Certifications**, each showing a **Why recommended** badge citing your real assessment scores.
   - Click **Propose New Plan** or click **+ Add to Plan** on any recommended resource.
   - Click **Update Progress** on any activity to slide progress (`0–100%`), write a learning reflection, and attach an evidence link (GitHub/certificate URL). When all activities in a plan reach `100%`, the plan automatically transitions to **Completed**.
5. **Account & Password (`/account/security`)**: Update your password securely at any time.

---

## 6. Role 4 — Faculty / HOD Walkthrough

Sign in at **`https://140.238.246.25/login`** with Institution Code **`MITT`**, Email **`kavitha.faculty@mitt.local`** (Cohort A) or **`rajesh.faculty@mitt.local`** (Cohort B), Password **`PeerTest@2026!`**:

1. **Assigned Students (`/students`)**: View only students enrolled in cohorts assigned to you via `CohortFaculty` (cohort isolation enforced by the backend).
2. **Evaluations (`/evaluations`)**:
   - Review `Pending Manual` descriptive and coding responses submitted by students in your assigned cohorts.
   - Enter rubric/awarded marks and feedback; submitting marks updates the student's `AssessmentResult` and finalizes the score once all manual items are graded.
3. **Analytics & Reports (`/analytics`)**:
   - Select an assigned cohort, inspect score distribution histograms, Demonstrated Performance domain bars, Strengths & Priority Gaps, Self-Reported vs Stated Interest charts, and the Student Comparison table.
   - Click any student row's **View Report** to inspect their individual domain profile.
   - Export cohort or individual student reports to **CSV**, **XLSX**, or **PDF**.
4. **Development Plans (`/development/plans`)**:
   - Select an authorized student to inspect their evidence-cited recommendations, create mentored development plans, assign top recommended trainings/pathways, add custom milestones, approve student `Proposed` plans to `Active`, and read student progress reflections.
5. **Faculty Intelligence (`/intelligence`)**:
   - View cohort-scoped KPIs (Assessed Students, Placement Ready / Near Ready / Support Needed counts, Plan Adoption %, Pending Manual Grading), domain hotspots, assigned mentors per cohort, and the searchable **Placement Readiness Matrix** with explicit criteria explanations.
6. **Pre / Post Comparison (`/pre-post`)**:
   - Select a cohort and compare either a **Baseline (Pre) vs Follow-Up (Post) Template** or automatic **Earliest vs Latest** attempts.
   - Inspect cohort mean delta, dimension-by-dimension score gains/drops, and individual student Pre → Post trajectories.

---

## 7. Recommended 10-Step Guided Exploration Tour

To see every feature work together end-to-end in ~15 minutes:

1. Sign in as **Institution Admin** (`https://140.238.246.25/admin/login`, `admin@mitt.local`) → confirm **Academic Structure** has `MCA` + `Sem 1 Sec A` + Students + Faculty assigned to `Sec A`.
2. Sign in as **Assessment Admin** (`https://140.238.246.25/admin/login`, `assessment@mitt.local`) → **Dimensions** → click **Seed Starter Catalogue**.
3. Go to **Learning Catalogue** → click **Seed Starter Catalogue**.
4. Go to **Question Bank** → add 2 objective questions (`PROG`, `DSA`), 1 descriptive/coding question (`DBMS`), and 1 interest item (`INT_SDE`).
5. Go to **Assessment Builder** → create a template (`Baseline Test`), add those questions, and click **Publish Version**.
6. Go to **Assignments** → assign `Baseline Test` to `Sem 1 Sec A` (enable **Release Results**).
7. Sign in as **Student** (`https://140.238.246.25/login`, e.g., `4MT25MC001`) → complete and submit the test under **My Assessments**.
8. Sign in as **Faculty / HOD** (`https://140.238.246.25/login`, `kavitha.faculty@mitt.local`) → grade the descriptive/coding answer in **Evaluations**, then inspect **Analytics & Reports** (try PDF/XLSX export) and **Faculty Intelligence**.
9. Switch back to **Student** (`https://140.238.246.25/login`) → open **My Results** and **My Empowerment** → add a recommended training to a plan and log `100%` progress + reflection.
10. Switch to **Assessment / Institution Admin** (`https://140.238.246.25/admin/login`) → open **Executive Reports** and export the Institution Executive PDF/XLSX; open **Audit Logs** to confirm every action was recorded.

---

## 8. Common Questions & Troubleshooting

- **"No active Faculty or Student membership found" on login**: You tried signing in with an Admin account on `/login` instead of `/admin/login`. Click **Admin portal →** (`/admin/login`).
- **Student cannot see results under My Results**: Edit the assignment in `/assessments/assignments` and ensure **Release Results to Students** is enabled.
- **Faculty cannot see a student or cohort**: Faculty/HOD access is strictly scoped by `CohortFaculty`. Ask the Institution Admin to assign that cohort to the faculty member under **Faculty** (`/faculty`).
- **Pre/Post Comparison shows "No comparable student pairs yet"**: Students need at least two completed assessments (either two attempts or both selected Baseline & Follow-up templates) to compute a Pre → Post delta.

