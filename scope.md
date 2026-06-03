# TalentForge AI — Application Scope

> **Version:** 1.0  
> **Repository:** https://github.com/Advaith4/HRMS  
> **Stack:** FastAPI · SQLModel · Supabase PostgreSQL · React 19 · Vite · Framer Motion · CrewAI · Groq LLM

---

## 1. Overview

TalentForge AI is a full-stack Human Resource Management System (HRMS) that combines traditional HR workflows with AI-powered recruitment intelligence. The system serves four distinct user roles through a unified React frontend, backed by a FastAPI REST API and a Supabase PostgreSQL database.

### Core Purpose
- Automate candidate screening using LLM-based resume analysis
- Manage the complete employee lifecycle from application to departure
- Give HR and Managers a single dashboard for recruitment, attendance, leave approvals, and workforce insights
- Empower employees with self-service attendance, leave, and skill-gap tools

---

## 2. User Roles & Access

| Role | Description | Key Capabilities |
|---|---|---|
| **Candidate** | External job applicant | Browse jobs, submit resume, track applications, view AI scores |
| **Employee** | Hired internal staff | Attendance check-in/out, leave requests, skill gap analysis, AI HR chatbot |
| **Manager** | Team lead | All candidate features + approve/reject leave, view recruitment pipeline |
| **HR** | Human resources admin | All manager features + post/edit/delete jobs, hire candidates, view all applicants |
| **Admin** | Super user | All HR features across the entire organization |

> Role assignment happens at registration. JWT tokens carry the role claim. All protected routes enforce role-based access via `require_roles()` dependency.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser (React 19)                  │
│  Vite · React Router · Zustand · Framer Motion · Recharts│
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP (JWT Bearer)
┌───────────────────────────▼─────────────────────────────┐
│                  FastAPI + Uvicorn                        │
│  GZip · CORS · JWT Auth · Background Tasks               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ /api/auth│ │ /api/jobs│ │/api/apps │ │/api/empl.. │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │/api/cands│ │/api/resme│ │/api/dash │ │/api/intview│  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │ SQLModel ORM
┌───────────────────────────▼─────────────────────────────┐
│           Supabase PostgreSQL (Remote)                    │
│  Connection pool: size=10, overflow=20, recycle=300s     │
└─────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│              Groq LLM API (llama-3.1-8b-instant)         │
│  CrewAI agents · Deterministic fallback scorer           │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Frontend — Pages & Features

### 4.1 Login Page (`/`)
- Unified login form for all roles
- Registration with role selection (candidate / employee / hr / manager)
- JWT stored in Zustand `authStore` + `localStorage`
- Redirects to role-appropriate dashboard on login

### 4.2 Candidate Dashboard (`/overview`, `/jobs`, `/applications`)

**Overview tab**
- Welcome banner with call-to-action
- KPI cards: Available Jobs · Applications Submitted · Pending Evaluations · Hired
- Recommended vacancies (latest 2 jobs)
- My recent applications with status pills

**Jobs tab**
- Full searchable job board with department filter chips
- Job cards showing title, department, salary, experience, description
- "Details" button opens `JobDetailDrawer`:
  - Full job info (skills, salary, experience, location)
  - PDF resume drag-and-drop upload (react-dropzone)
  - Submit application → backend saves to DB → AI analysis runs in background
  - Success state with confirmation message

**My Applications tab**
- All submitted applications in an expandable accordion table
- AI fit score badge (colour-coded: green ≥75, yellow ≥50, red <50)
- Status pill (Applied / Under Review / Shortlisted / Hired / Rejected)
- Expand row to see AI recommendation, strengths, weaknesses

### 4.3 HR Dashboard (`/overview`, `/jobs`, `/pipeline`, `/candidates`, `/leaves`)

**Overview tab**
- KPI cards: Open Jobs · Total Applicants · Pending Review · Hired · Avg AI Score
- Application volume trend chart (Recharts)
- Score distribution donut chart
- Clickable Active Postings sidebar → opens Job Applicants Drawer

**Jobs tab**
- Job cards grid with "View Applicants" button → Job Applicants Drawer
- Post New Job button → `PostJobModal` (create/edit)
- Delete job with confirmation

**Job Applicants Drawer** (slide-in panel)
- Triggered by clicking any job from Jobs tab or Overview sidebar
- Stats bar: Total · Hired · Pending · Avg Score
- Ranked list of all applicants sorted by AI fit score
- Per-row: rank, avatar, name, status pill, AI recommendation snippet, apply date, score badge
- "Inspect" button opens full `AnalysisDrawer`

**Pipeline tab**
- Kanban-style recruitment funnel view
- Filter by stage: All / Applied / Under Review / Hired / Rejected
- Application cards with AI score and candidate info
- "Inspect" button on each card

**Candidates tab**
- Full candidate list with application count and join date
- Linked to their applications

**Leaves tab**
- All pending employee leave requests
- Approve / Reject with manager note → decision modal

### 4.4 Manager Dashboard (`/overview`, `/pipeline`, `/leaves`)
- Subset of HR dashboard (no job posting/deletion)
- Recruitment pipeline view with job filter dropdown
- AI rankings per job (sorted by fit score)
- Leave approval/rejection with notes

### 4.5 Employee Dashboard (`/overview`, `/attendance`, `/leaves`, `/skills`)

**Overview tab**
- Employee profile card (code, department, designation, joining date)
- Live digital clock + hours worked today
- Attendance status (Checked In / Checked Out)
- Leave summary (pending/approved/rejected counts)
- AI HR Chatbot (streaming drawer) — answers HR policy questions

**Attendance tab**
- Check In / Check Out buttons with timestamp
- Today's record display

**Leave tab**
- Leave request form (type, start date, end date, reason)
- Duplicate submission prevention
- My leave history table with status pills

**Skill Gap tab**
- Input target role
- AI analyses skill gap against current profile
- Returns: missing skills, growth areas, learning suggestions, summary

---

## 5. Backend — API Routes

### Authentication — `/api/auth`
| Method | Endpoint | Description |
|---|---|---|
| POST | `/register` | Create account (candidate/employee/hr/manager) |
| POST | `/login` | Login, returns JWT access token |
| GET | `/me` | Current user profile |

### Jobs — `/api/jobs`
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | All | List all job postings |
| POST | `/` | HR/Admin | Create job posting |
| PUT | `/{id}` | HR/Admin | Edit job posting |
| DELETE | `/{id}` | HR/Admin | Delete job posting |

### Applications — `/api/applications`
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/apply` | Candidate | Submit PDF resume for a job (async AI analysis) |
| GET | `/me` | Candidate | My applications with AI scores |
| GET | `/` | HR/Manager | All applications (batch-loaded, no N+1) |
| POST | `/{id}/analyze` | HR/Manager | Re-run AI analysis on an application |
| POST | `/{id}/hire` | HR | Convert application to employee record |
| GET | `/rankings/{job_id}` | HR/Manager | AI-ranked applicants for a job |

### Candidates — `/api/candidates`
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | HR/Manager | List all candidate users |

### Employees — `/api/employees`
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/dashboard` | Employee | Employee profile, attendance, leave summary, skill gap |
| GET | `/attendance/today` | Employee | Today's check-in/out record |
| POST | `/attendance/checkin` | Employee | Clock in |
| POST | `/attendance/checkout` | Employee | Clock out |
| GET | `/leave` | HR/Manager | All leave requests |
| POST | `/leave/request` | Employee | Submit leave request |
| PUT | `/leave/{id}/decide` | HR/Manager | Approve or reject leave |

### Resume — `/api/resume`
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/upload` | Candidate | Upload and parse PDF resume |
| GET | `/me` | Candidate | My resume status and text |
| POST | `/analyze` | Candidate | Run resume analysis against target role |
| POST | `/fix` | Candidate | Apply AI-suggested resume fixes |

### Dashboard Aggregates — `/api/dashboard`
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/hr` | HR/Manager | Jobs + all applications + candidates in 1 request |
| GET | `/candidate` | Candidate | Jobs + my applications + resume status in 1 request |

### Interview — `/api/interview`
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/start` | Candidate/Employee | Start a mock interview session |
| POST | `/{token}/message` | Candidate/Employee | Send message, get AI response (streaming) |
| GET | `/{token}` | Candidate/Employee | Get session history |
| GET | `/sessions` | Candidate/Employee | List all past sessions |

---

## 6. Database Schema

### `users`
Primary identity table for all roles.

| Column | Type | Notes |
|---|---|---|
| id | int PK | Auto-increment |
| username | str | Unique, indexed |
| hashed_password | str | bcrypt hash |
| role | str | candidate / employee / hr / manager / admin |
| target_role | str? | Career goal (for candidates) |
| location | str? | Default: India |
| experience | str? | Default: Entry-level |
| created_at | datetime | UTC |

### `resumes`
Latest resume state for a candidate.

| Column | Type | Notes |
|---|---|---|
| user_id | FK→users | Indexed |
| raw_text | str | Parsed PDF text |
| original_text | str? | Pre-fix snapshot |
| current_text | str? | Post-fix version |
| parsed_resume | str? | JSON structured parse |
| last_analysis | str? | JSON last AI result |
| applied_fixes | str | JSON array of applied fixes |

### `job_postings`
HR-created vacancies.

| Column | Type | Notes |
|---|---|---|
| title | str | Max 200 chars |
| description | str | Full text |
| required_skills | str | Comma-separated |
| department | str | |
| salary_range | str | e.g. ₹18–24 LPA |
| experience_required | str | e.g. 5+ years |
| created_by | FK→users | HR user ID |

### `candidate_applications`
One record per candidate per job.

| Column | Type | Notes |
|---|---|---|
| candidate_user_id | FK→users | |
| job_id | FK→job_postings | |
| resume_text | str | Extracted from PDF |
| application_date | datetime | |
| status | str | Applied / Under Review / Shortlisted / Selected / Rejected / Hired |

### `application_ai_analyses`
AI analysis result per application (1:1).

| Column | Type | Notes |
|---|---|---|
| application_id | FK (unique) | |
| fit_score | int | 0–100 |
| recommendation | str | Strongly Recommended / Recommended / Consider / Reject |
| summary | str | AI summary text |
| strengths | str | JSON array |
| weaknesses | str | JSON array |
| missing_skills | str | JSON array |
| observations | str | JSON array |
| technical_questions | str | JSON array (interview prep) |
| behavioral_questions | str | JSON array (interview prep) |
| probing_areas | str | JSON array |
| status | str | pending / completed / failed |
| source | str | ai / fallback |

### `employees`
Created when a candidate is hired.

| Column | Type | Notes |
|---|---|---|
| user_id | FK→users (unique) | |
| employee_code | str | e.g. TF-00042 |
| department | str | |
| designation | str | |
| salary | float? | Annual CTC |
| joining_date | date? | |
| skills | str | Comma-separated |

### `attendance_records`
Daily check-in/check-out logs.

| Column | Type | Notes |
|---|---|---|
| employee_id | FK→employees | |
| user_id | FK→users | |
| work_date | date | Indexed |
| check_in | datetime | |
| check_out | datetime? | Null if still checked in |
| status | str | Checked In / Checked Out |

### `leave_requests`
Employee leave with approval workflow.

| Column | Type | Notes |
|---|---|---|
| employee_id | FK→employees | |
| user_id | FK→users | |
| leave_type | str | Annual / Sick / Personal / Emergency / etc. |
| start_date | date | |
| end_date | date | |
| reason | str | |
| status | str | Pending / Approved / Rejected |
| manager_note | str? | Decision notes |
| decided_by | FK→users? | HR/Manager who acted |

### `skill_gap_analyses`
AI skill gap results per employee.

| Column | Type | Notes |
|---|---|---|
| employee_id | FK→employees | |
| role_expectations | str | Target role description |
| missing_skills | str | JSON array |
| growth_areas | str | JSON array |
| learning_suggestions | str | JSON array |
| summary | str | |
| source | str | ai / fallback |

---

## 7. AI / LLM Features

### 7.1 Resume Analysis (Recruitment)
- **Trigger:** Candidate submits PDF resume for a job
- **Process:** PDF → `pypdf` text extraction → CrewAI agent → Groq LLM (`llama-3.1-8b-instant`)
- **Output:** `ApplicationAIAnalysis` record with fit score, recommendation, strengths, weaknesses, missing skills, interview questions
- **Performance:** Runs as FastAPI **background task** — HTTP response returns in <1s; score appears asynchronously
- **Fallback:** Deterministic keyword-matching scorer used when LLM is unavailable

### 7.2 Resume Lab
- Candidate uploads resume → AI parses structure (name, skills, experience, education)
- AI suggests section-by-section improvements
- Candidate can apply/reject individual fixes
- Version history maintained (original vs current)

### 7.3 Skill Gap Analysis (Employees)
- Employee inputs target role
- AI compares current skills (from employee profile) against role expectations
- Returns: missing skills, growth areas, learning suggestions, progress summary
- Falls back to deterministic comparison when LLM unavailable

### 7.4 AI HR Chatbot (Employee)
- Streaming chatbot answering HR policy questions
- Stateful conversation with session memory
- Aware of employee's department, role, and attendance context

### 7.5 Mock Interview Sessions
- Candidate selects role, difficulty, training mode, interviewer persona
- AI conducts structured interview via chat
- Scores each answer in real time
- Saves full session history with `avg_score`
- Long-term coaching memory (`CareerCoachMemory`) tracks recurring weak areas across sessions

---

## 8. Performance Optimisations

| Area | Technique | Impact |
|---|---|---|
| **Dashboard load** | Aggregate endpoints `/api/dashboard/hr` and `/api/dashboard/candidate` | 3 HTTP calls → 1 |
| **DB queries** | Batch `IN` queries for applications, users, analyses | N+1 → 4 fixed queries |
| **Connection pool** | `pool_size=10`, `max_overflow=20`, `pool_recycle=300s`, `pool_pre_ping=True` | Eliminates Supabase cold-start waits |
| **Frontend bundle** | Named Lucide imports, Vite code splitting per route | 632KB → 19KB initial JS |
| **API caching** | 30s in-memory TTL cache on GET requests in axios interceptor | Instant navigation between tabs |
| **AI analysis** | FastAPI `BackgroundTasks` for LLM inference | Submit response: 30s+ → <1s |
| **Transport** | `GZipMiddleware` on all responses | ~60% payload reduction |

---

## 9. Security

- **Passwords:** bcrypt hashed via `passlib`
- **Auth tokens:** HS256 JWT, 7-day expiry, validated on every protected route
- **Role enforcement:** `require_roles()` FastAPI dependency — raises 403 if role not permitted
- **Duplicate prevention:** 409 Conflict responses for duplicate job applications and leave requests
- **File uploads:** PDF-only validation, 5 MB size cap, temp file cleanup after parsing
- **Environment:** All secrets loaded from `.env` via Pydantic `Settings`; proxy env-vars that break Groq API cleaned at startup

---

## 10. Deployment

| Target | Method | Notes |
|---|---|---|
| **Local dev** | `uvicorn src.main:app --reload --host 127.0.0.1 --port 8000` | Frontend built to `static/`, served by FastAPI |
| **Docker** | `docker build -t talentforge-ai . && docker run --env-file .env -p 8000:8000 talentforge-ai` | Single-container, self-contained |
| **Render** | `render.yaml` provided | Backend service; set `DATABASE_URL` to Supabase connection string |
| **Vercel** | `vercel.json` provided | Frontend-only static hosting; backend runs on Render |

---

## 11. Project Structure

```
HRMS/
├── src/
│   ├── main.py                    # FastAPI app, lifespan, router registration
│   ├── config.py                  # Pydantic Settings (reads .env)
│   ├── resume_lab.py              # Resume parsing, validation, fix logic
│   ├── models/__init__.py         # All SQLModel table definitions
│   ├── database/connection.py     # Engine, session factory, startup migrations
│   ├── api/
│   │   ├── dependencies.py        # JWT auth, require_roles()
│   │   └── routes/
│   │       ├── auth.py            # Register, login, /me
│   │       ├── jobs.py            # CRUD for job postings
│   │       ├── applications.py    # Apply, list, analyze, hire
│   │       ├── candidates.py      # Candidate list for HR
│   │       ├── employees.py       # Attendance, leave, employee dashboard
│   │       ├── resume.py          # Resume upload, analysis, fixes
│   │       ├── interview.py       # Mock interview sessions (streaming)
│   │       └── dashboard.py       # Aggregate endpoints (hr + candidate)
│   ├── services/
│   │   └── recruitment_ai.py      # CrewAI orchestration, scoring, payloads
│   └── core/
│       └── security.py            # JWT encode/decode, bcrypt helpers
│
├── frontend/
│   ├── src/
│   │   ├── api/                   # Axios client, all API functions
│   │   ├── pages/                 # LoginPage, CandidateDashboard, HRDashboard,
│   │   │                          # ManagerDashboard, EmployeeDashboard
│   │   ├── components/
│   │   │   ├── layout/            # Layout, Sidebar, TopBar
│   │   │   ├── drawers/           # AnalysisDrawer, JobDetailDrawer
│   │   │   ├── modals/            # PostJobModal
│   │   │   ├── charts/            # ApplicationTrend, ScoreDistribution, SkillGapRadial
│   │   │   └── ui/                # MetricCard, StatusPill, SkeletonCard, EmptyState, AIScoreDonut
│   │   └── store/
│   │       └── authStore.js       # Zustand auth state (token, role, user)
│   └── vite.config.js             # Build config, code splitting
│
├── agents/                        # CrewAI agent definitions
├── tasks/                         # CrewAI task definitions
├── utils/
│   └── resume_parser.py           # pypdf text extraction
├── static/                        # Built frontend assets (served by FastAPI)
├── tests/                         # pytest test suite
├── Dockerfile
├── render.yaml
├── vercel.json
├── requirements.txt
└── scope.md                       # This file
```

---

## 12. Environment Variables

```env
# LLM
GROQ_API_KEY=                      # Groq API key for Llama inference

# Database
DATABASE_URL=postgresql://...      # Supabase PostgreSQL connection string
PGSSLMODE=require
DATABASE_CONNECT_TIMEOUT=10

# Supabase (optional — for direct SDK use)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# App
SECRET_KEY=                        # JWT signing secret (min 32 chars)
AUTO_CREATE_DB_SCHEMA=true         # Run lightweight migrations on startup
DEBUG=false
MODEL_NAME=llama-3.1-8b-instant    # Groq model name
```

---

## 13. Known Constraints & Limitations

- **AI analysis latency:** LLM responses from Groq take 5–30s. Mitigated by background task execution; scores appear on next page refresh.
- **No email notifications:** Status changes (hired, leave decision) are visible in-dashboard only — no email/SMS integration yet.
- **Single-tenant:** No multi-company/organisation support. All data is shared within one deployment.
- **Resume format:** PDF only. DOCX, images, and LinkedIn imports are not yet supported.
- **Attendance:** Basic check-in/out only. No shift management, overtime calculation, or biometric integration.
- **No real-time updates:** Dashboard data refreshes on navigation. No WebSocket/SSE push for live notifications.
