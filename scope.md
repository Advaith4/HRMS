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

---

## 14. Key User Flows

### 14.1 Candidate — Apply for a Job
```
1. Register / Login  →  role: candidate
2. Careers Portal → Jobs tab
3. Browse jobs, click "Details" on a vacancy
4. JobDetailDrawer opens → read job description + required skills
5. Drag-and-drop PDF resume into upload zone
6. Click "Submit Application"
7. Backend: validates PDF, extracts text (pypdf), saves CandidateApplication record
8. HTTP 201 response returned instantly (<1 s)
9. AI analysis runs as background task (5–30 s asynchronously)
10. Toast: "Application submitted! AI score will appear shortly."
11. Navigate to My Applications → score appears after background task completes
12. Expand row → view strengths, weaknesses, missing skills, interview questions
```

### 14.2 HR — Post Job & Hire a Candidate
```
1. Login  →  role: hr
2. HR Dashboard → Jobs tab → "Post New Job"
3. PostJobModal: enter title, department, description, skills, salary, experience
4. Job saved → visible to all candidates on the Careers Portal immediately
5. HR Dashboard → Jobs tab → "View Applicants" on the new job
6. Job Applicants Drawer opens → ranked list (sorted by AI fit score)
7. Click "Inspect" on top-ranked candidate → AnalysisDrawer
8. Review: fit score, recommendation, strengths, weaknesses, interview prep questions
9. Return to Applicants Drawer → click "Hire" on selected candidate
10. HireModal: enter department, designation, salary, joining date, employee code
11. Backend: creates Employee record + updates Application status to "Hired"
12. Candidate's role can now be updated to "employee" for system access
```

### 14.3 Employee — Daily Attendance & Leave
```
Attendance:
1. Login  →  role: employee
2. Employee Dashboard → Overview tab
3. Click "Check In" → timestamp recorded, status changes to "Checked In"
4. End of day → Click "Check Out" → duration calculated
5. Attendance tab shows today's record with check-in / check-out times

Leave:
1. Employee Dashboard → Leave tab
2. Fill form: leave type, start date, end date, reason
3. Submit → backend checks for duplicate date-range overlap (409 if conflict)
4. Status: Pending
5. HR/Manager Dashboard → Leaves tab shows pending request
6. HR/Manager clicks Approve or Reject, optionally adds a note
7. Employee's Leave tab updates with Approved / Rejected + manager note
```

### 14.4 Manager — Review Recruitment Pipeline
```
1. Login  →  role: manager
2. Manager Dashboard → Pipeline tab
3. Select a job from the dropdown filter
4. View all applications for that job with AI scores
5. Filter by stage: Applied / Under Review / Shortlisted
6. Click "Inspect" on any application card → full AnalysisDrawer
7. View: fit score, recommendation, strengths, weaknesses, interview prep
8. Leave tab: approve or reject employee leave requests with notes
```

### 14.5 Candidate — Mock Interview Practice
```
1. Candidate Dashboard → (Interview section)
2. Choose: target role, difficulty (1–10), training mode, interviewer persona
3. Session starts → interviewer opens with Introduction phase
4. 8-phase structured interview:
   Introduction → Resume Deep Dive → Core Technical →
   Problem Solving → Behavioral → Pressure/Cross-questioning →
   Candidate Questions → Final Evaluation
5. Each answer is evaluated and scored (0–10) by the AI
6. Session auto-advances through phases based on answer count and avg score
7. Final Evaluation phase → summary of performance + improvement plan
8. Session saved → CareerCoachMemory updated with weak areas and score trend
9. Next session: AI automatically targets recurring weaknesses
```

---

## 15. Interview System — Deep Dive

### 15.1 Session Phases

The interview is structured into **8 sequential phases**. Phase advancement is automatic based on answer count and average score:

| # | Phase | Min Turns | Goal |
|---|---|---|---|
| 1 | Introduction | 1 | Establish context, confirm role fit |
| 2 | Resume Deep Dive | 1 | Validate resume claims with concrete examples |
| 3 | Core Technical Round | 2 | Probe depth, tradeoffs, system thinking |
| 4 | Problem Solving | 1 | Structured thinking under constraints |
| 5 | Behavioral Round | 1 | STAR stories, ownership, collaboration |
| 6 | Pressure / Cross-questioning | 1 | Stress-test consistency and clarity |
| 7 | Candidate Questions | 1 | Evaluate curiosity and role understanding |
| 8 | Final Evaluation | 0 | Score summary and improvement plan |

> After **8 answers total**, the session fast-forwards to Final Evaluation regardless of phase.

### 15.2 Training Modes

| Mode | Question Mix | Use Case |
|---|---|---|
| `adaptive` | 60% weak areas, 40% general | Default — balances drilling and coverage |
| `weak_area_only` | 100% weak areas | Targeted remediation |
| `domain_specific` | 70% domain, 30% weak areas | Pre-interview technical prep |
| `behavioral_only` | 100% behavioral | Communication and leadership focus |

### 15.3 Interviewer Personas

| Persona | Pressure | Behavior |
|---|---|---|
| `balanced` | Medium | Professional, direct, coaches through gaps |
| `strict` | High | Interrupts vague answers, demands precision |
| `technical` | Medium-High | Challenges architecture and implementation tradeoffs |
| `friendly` | Low-Medium | Encouraging, normalises mistakes, guided follow-ups |
| `behavioral` | Medium | STAR-narrative focused, evidence-driven |

### 15.4 Scoring & Memory
- Each answer receives a **score 0–10** from the AI
- `avg_score` is maintained per session
- `CareerCoachMemory` (one record per user) tracks:
  - `recurring_weak_areas` — areas that score poorly across multiple sessions
  - `score_trend` — recent per-answer scores
  - `session_history` — compact summaries of all past sessions
  - `daily_plan` — AI-generated improvement plan
  - `preferred_persona` and `preferred_training_mode` — learned over time

### 15.5 Database Tables

| Table | Purpose |
|---|---|
| `interview_sessions` | Full message history, phase state, avg score, status |
| `career_coach_memory` | Long-term cross-session coaching memory (1 row per user) |
| `job_applications` | Bookmarked/tracked external jobs with AI-tailored resume bullets |

---

## 16. CrewAI Agent Architecture

### 16.1 Recruitment Analyst Agent
- **File:** `agents/recruitment_analyst.py`
- **Task:** `tasks/recruitment_task.py`
- **Input:** Resume text + parsed resume + job posting details
- **Output:** Structured JSON with fit score, recommendation, strengths, weaknesses, missing skills, observations, interview questions
- **LLM:** Groq `llama-3.1-8b-instant` via `GROQ_API_KEY`
- **Orchestration:** Single-agent `Crew`, `verbose=False`, one-shot kickoff

### 16.2 AI Analysis Pipeline
```
PDF upload
   │
   ▼
pypdf text extraction  (utils/resume_parser.py)
   │
   ▼
parse_resume()  (src/resume_lab.py)
   │  → structured fields: name, skills, experience, education, contact
   ▼
create_recruitment_analyst()  →  create_application_analysis_task()
   │
   ▼
Crew.kickoff()  →  Groq LLM
   │
   ▼
_extract_json()  →  _normalize_ai_payload()
   │  → validates & clamps fit_score, recommendation, all list fields
   ▼
_upsert_analysis()  →  ApplicationAIAnalysis row saved to DB
```

### 16.3 Fallback Scorer
When the LLM is unavailable (no API key, rate limit, timeout), `_fallback_analysis()` is used:
- Tokenises resume and job description into lowercase term sets
- Calculates **overlap ratio** between resume terms and required skill terms
- Maps overlap ratio → `fit_score` (0–100) using a linear scale
- Derives `recommendation` from score bracket:
  - ≥ 80 → Strongly Recommended
  - ≥ 65 → Recommended
  - ≥ 45 → Consider
  - < 45 → Reject
- Generates deterministic strengths/weaknesses from matched/unmatched skill terms
- `source` field set to `"fallback"` so HR can distinguish AI vs deterministic results

---

## 17. Frontend Component Architecture

### 17.1 State Management
```
Zustand (authStore.js)
  ├── token          — JWT string
  ├── user           — { id, username, role }
  ├── setAuth()      — called on login
  └── clearAuth()    — called on logout / 401
```
Persisted to `localStorage`. On app load, token is rehydrated and validated.

### 17.2 API Layer (`frontend/src/api/`)

| File | Functions |
|---|---|
| `axios.js` | Axios instance, 12s timeout, Bearer interceptor, 30s GET cache, 401 logout handler |
| `auth.js` | `login()`, `register()`, `getMe()` |
| `jobs.js` | `listJobs()`, `createJob()`, `updateJob()`, `deleteJob()` |
| `applications.js` | `applyToJob()` (60s timeout), `getMyApplications()`, `listApplications()`, `hireCandidate()`, `getJobRankings()` |
| `candidates.js` | `listCandidates()` |
| `employees.js` | `getEmployeeDashboard()`, `checkIn()`, `checkOut()`, `requestLeave()`, `getLeaves()`, `decideLeave()`, `analyzeSkillGap()`, `askHRQuestion()` |
| `resume.js` | `uploadResume()`, `getMyResume()`, `analyzeResume()`, `applyFixes()` |
| `dashboard.js` | `getHRDashboardData()`, `getCandidateDashboardData()` |
| `index.js` | Barrel re-exports all above + `invalidateCache` |

### 17.3 Component Map

```
App.jsx  (React Router)
├── /                   → LoginPage
├── /dashboard          → role-based redirect
│   ├── role=candidate  → CandidateDashboard
│   ├── role=hr         → HRDashboard
│   ├── role=manager    → ManagerDashboard
│   └── role=employee   → EmployeeDashboard
│
Layout.jsx
├── Sidebar.jsx         — nav links, role label, logout
└── TopBar.jsx          — page title, user avatar

Shared UI Components:
├── MetricCard          — KPI tile with icon, value, delta
├── StatusPill          — coloured badge for status strings
├── SkeletonCard        — animated loading placeholder
├── EmptyState          — empty list illustration + CTA
└── AIScoreDonut        — circular score ring (0–100)

Charts (Recharts):
├── ApplicationTrend    — area chart of applications over time
├── ScoreDistribution   — donut of score buckets
└── SkillGapRadial      — radar chart for skill coverage

Drawers (slide-in panels, z-50, backdrop):
├── AnalysisDrawer      — full AI analysis for one application
│                         (score, recommendation, strengths, weaknesses,
│                          missing skills, interview prep questions)
└── JobDetailDrawer     — job info + PDF resume upload + submit

Modals:
└── PostJobModal        — create / edit job posting form
```

### 17.4 Routing & Auth Guard
```jsx
// App.jsx
<ProtectedRoute roles={["hr","admin"]}>
  <HRDashboard />
</ProtectedRoute>
```
- `ProtectedRoute` reads role from `authStore`
- Redirects to `/` (login) if no token
- Redirects to role-correct dashboard if accessing wrong role's route

---

## 18. Data Flow Diagrams

### 18.1 Resume Submit Flow
```
Browser                FastAPI               DB              Groq LLM
   │                      │                   │                  │
   │─ POST /apply ────────►│                   │                  │
   │  (multipart PDF)      │                   │                  │
   │                       │─ pypdf extract ──►│                  │
   │                       │─ INSERT app ─────►│                  │
   │                       │◄─ app.id ─────────│                  │
   │◄─ 201 {application} ──│                   │                  │
   │                       │                   │                  │
   │  (response sent)      │── background ─────────────────────►  │
   │                       │   task             │  CrewAI kickoff  │
   │                       │                   │◄── analysis JSON ─│
   │                       │                   │── INSERT analysis ►│
   │                       │                   │                  │
   │─ GET /dashboard/cand ►│                   │                  │
   │◄─ {apps + score} ─────│◄─ SELECT ─────────│                  │
```

### 18.2 Leave Approval Flow
```
Employee              FastAPI             DB            HR/Manager
   │                     │                │                 │
   │─ POST /leave/req ──►│                │                 │
   │                     │─ check dupe ──►│                 │
   │                     │◄─ none ────────│                 │
   │                     │─ INSERT ───────►│                 │
   │◄─ 201 Pending ──────│                │                 │
   │                     │                │                 │
   │                     │                │◄── GET /leave ──│
   │                     │                │─── list ───────►│
   │                     │◄── PUT /decide─────────────────── │
   │                     │─ UPDATE status►│                 │
   │                     │◄─ done ────────│                 │
   │◄─ status updated ───│                │                 │
   │  (on next load)     │                │                 │
```

---

## 19. API — Key Request & Response Shapes

### POST `/api/auth/login`
```json
// Request
{ "username": "alice", "password": "Pass123!" }

// Response 200
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "role": "candidate",
  "username": "alice",
  "user_id": 9
}
```

### POST `/api/applications/apply` (multipart)
```
Form fields:
  job_id = 3
  file   = resume.pdf (binary)

Response 201:
{
  "success": true,
  "message": "Application submitted. AI analysis is running in the background.",
  "application": {
    "id": 17,
    "job_id": 3,
    "job_title": "Senior Backend Engineer",
    "department": "Engineering",
    "status": "Applied",
    "application_date": "2026-06-03T01:37:21",
    "ai_analysis": null        ← populated asynchronously
  }
}

Error 409 (duplicate):
{ "detail": "You have already submitted an application for this job opening." }
```

### GET `/api/dashboard/candidate`
```json
{
  "jobs": [
    {
      "id": 3,
      "title": "Senior Backend Engineer",
      "department": "Engineering",
      "required_skills": "Python, FastAPI, PostgreSQL",
      "salary_range": "₹18–24 LPA",
      "experience_required": "5+ years",
      "description": "..."
    }
  ],
  "applications": [
    {
      "id": 17,
      "job_id": 3,
      "job_title": "Senior Backend Engineer",
      "status": "Applied",
      "application_date": "2026-06-03T01:37:21",
      "ai_analysis": {
        "fit_score": 82,
        "recommendation": "Recommended",
        "summary": "Strong FastAPI background...",
        "strengths": ["Expert in Python", "Solid DB indexing"],
        "weaknesses": ["Limited cloud experience"],
        "missing_skills": ["Kubernetes"],
        "source": "ai"
      }
    }
  ],
  "has_resume": true,
  "resume": { "id": 5, "updated_at": "2026-06-03T01:30:00" }
}
```

### PUT `/api/employees/leave/{id}/decide`
```json
// Request
{ "status": "Approved", "manager_note": "Approved. Enjoy your break." }

// Response 200
{ "id": 12, "status": "Approved", "manager_note": "Approved. Enjoy your break." }

// Error 400 (already decided)
{ "detail": "Leave request already decided." }
```

---

## 20. Testing

### Test Suite — `tests/`

| File | Coverage |
|---|---|
| `tests/test_api.py` | Auth, RBAC, job CRUD, file upload, AI analysis, hire flow, rankings |
| `tests/test_resume_lab.py` | Resume parsing, fix application, scoring logic |

### Running Tests
```bash
# All tests
pytest tests/ -v

# Single module
pytest tests/test_api.py -v

# Single test
pytest tests/test_api.py::test_register_and_login_returns_role -v
```

### Test Environment
- Uses an isolated **SQLite database** (created fresh per test run)
- `DATABASE_URL` is overridden to `sqlite:///data/test_<uuid>.db` before import
- `AUTO_CREATE_DB_SCHEMA=true` — tables created at test startup
- AI analysis calls are **monkeypatched** to return deterministic mock payloads
- No Supabase or Groq API key required to run tests

### Key Test Cases
- `test_register_and_login_returns_role` — token + role in response
- `test_public_registration_rejects_role_escalation` — can't self-assign admin
- `test_job_crud_hr_only` — candidate gets 403 on job creation
- `test_apply_and_duplicate_rejected` — second application returns 409
- `test_hire_creates_employee_record` — hire flow creates Employee row
- `test_resume_parse_extracts_skills` — pypdf + resume_lab extraction
- `test_fallback_scorer_produces_valid_score` — deterministic scorer bounds

---

## 21. Development Workflow

### First-time Setup
```bash
# 1. Clone
git clone https://github.com/Advaith4/HRMS.git
cd HRMS

# 2. Python environment
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 3. Environment config
copy .env.example .env
# Fill in: DATABASE_URL, GROQ_API_KEY, SECRET_KEY

# 4. Frontend
cd frontend
npm install
npm run build                 # builds to ../static/
cd ..

# 5. Run
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Dev Mode (hot reload)
```bash
cd frontend
npm run dev    # runs on :5173, proxies /api/* to :8000
```
> In dev mode, Vite proxies API requests to the FastAPI server. The `isDevServer` flag in `axios.js` detects port 5173 and removes the base URL prefix.

### Rebuilding the Frontend
```bash
cd frontend
npm run build
# Output goes to ../static/assets/
# FastAPI serves static/ at the root path
```

### Adding a New API Route
1. Create `src/api/routes/myroute.py` with a `router = APIRouter(prefix="/api/myroute")`
2. Import and register in `src/main.py`: `app.include_router(myroute.router)`
3. Add corresponding frontend API function in `frontend/src/api/myroute.js`
4. Re-export from `frontend/src/api/index.js`

### Adding a New Database Table
1. Add `SQLModel` class to `src/models/__init__.py`
2. Add `ALTER TABLE` / column check logic to `src/database/connection.py` `_ensure_*` functions (idempotent)
3. The table is created on next server startup (`AUTO_CREATE_DB_SCHEMA=true`)

---

## 22. Dependencies

### Backend (`requirements.txt`)
| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `sqlmodel` | ORM (SQLAlchemy + Pydantic) |
| `psycopg2-binary` | PostgreSQL driver |
| `python-jose` | JWT encode/decode |
| `passlib[bcrypt]` | Password hashing |
| `python-multipart` | Multipart file upload parsing |
| `pypdf` | PDF text extraction |
| `crewai` | Multi-agent AI orchestration |
| `groq` | Groq LLM API client |
| `pydantic-settings` | `.env` config loading |
| `appdirs` | Cross-platform app data paths |

### Frontend (`package.json`)
| Package | Purpose |
|---|---|
| `react` + `react-dom` | UI framework (v19) |
| `react-router-dom` | Client-side routing |
| `zustand` | Lightweight global state |
| `axios` | HTTP client |
| `framer-motion` | Animations and page transitions |
| `recharts` | Chart components |
| `lucide-react` | Icon library |
| `react-dropzone` | Drag-and-drop file upload |
| `react-hot-toast` | Toast notifications |
| `vite` | Build tool and dev server |

---

## 23. Roadmap — Planned Enhancements

| Feature | Priority | Notes |
|---|---|---|
| Email notifications | High | Notify candidates on status change; HR on new applications |
| Real-time updates | High | WebSocket push for leave decisions and AI score completion |
| Resume DOCX support | Medium | Extend `resume_parser.py` with `python-docx` |
| Multi-tenant support | Medium | Company-scoped data isolation |
| Payroll module | Medium | Salary calculation, pay slips, tax deductions |
| Performance reviews | Medium | Periodic employee appraisals with AI scoring |
| Shift management | Low | Rosters, overtime, multi-shift attendance |
| LinkedIn import | Low | Parse LinkedIn PDF export as resume |
| Mobile app | Low | React Native wrapper over the existing API |
| Audit log | Low | Immutable log of all HR decisions (hire, reject, leave) |
