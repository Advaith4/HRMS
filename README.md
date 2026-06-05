# TalentForge AI

TalentForge AI is a full-cycle HRMS + recruitment intelligence platform for candidates, HR teams, managers, and employees. It combines a **FastAPI** backend, **SQLModel** persistence (SQLite/PostgreSQL), **CrewAI + Groq** AI orchestration, and a **React 19 + Vite SPA** frontend (with legacy static fallback).

## Features

### Recruitment
- Candidate registration, login, resume upload (PDF), and job applications
- JWT authentication with role-based access control (candidate, hr, manager, admin, employee)
- HR job posting management (CRUD)
- Manager/HR candidate and application review
- AI recruitment analysis with deterministic fallback scoring
- Fit scores, recommendations, strengths, weaknesses, missing skills, interview prep
- Per-job candidate rankings
- Resume Lab: AI-powered analysis, fix suggestions, and section rewriting

### AI Interview Engine
- 5-agent CrewAI interview orchestration with Groq LLM
- Adaptive difficulty, coaching memory, 4 training modes
- Start interview from scratch or from uploaded resume
- Audio transcription via Groq Whisper
- Credibility reports (cross-reference resume claims vs interview answers)
- Leaderboard, candidate comparison, top-candidate ranking
- HR intelligence: advance/reject, follow-up questions, detailed reports

### Employee Lifecycle
- Employee directory, profiles, and document management
- Attendance tracking: check-in, check-out, records
- Leave management: apply, approve/reject, history
- Skill gap analysis with AI recommendations
- Promotions and salary revision history
- Employee lifecycle event tracking
- Onboarding: templates, tasks, plans, required documents

### HR Tools
- Department and designation management
- Employee ticket/grievance system (create, assign, track)
- Notification center
- Training programs and assignments
- Document verification queue
- AI HR assistant chat
- Dashboard: HR, manager, candidate, and employee views

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend (SPA) | React 19, Vite, TailwindCSS 4, Framer Motion, Zustand, Recharts, React Router 7, Axios, Lucide Icons |
| Frontend (legacy) | HTML, CSS, JavaScript |
| Backend | FastAPI, Uvicorn |
| Database | SQLModel, SQLite (dev), PostgreSQL/Supabase (prod) |
| AI orchestration | CrewAI |
| LLM provider | Groq (llama-3.1-8b-instant) |
| Audio transcription | Groq Whisper (whisper-large-v3) |
| Authentication | JWT, bcrypt |
| Resume parsing | pypdf |
| Deployment | Docker, Render |

## Quickstart

### Backend

```bash
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
# .\.venv\Scripts\activate    # Windows
pip install -r requirements.txt
cp .env.example .env          # fill in GROQ_API_KEY at minimum
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### React Frontend (optional)

```bash
cd frontend
npm install
npm run dev                   # starts Vite dev server on port 5173
```

### Access Points

| URL | Description |
| --- | --- |
| http://127.0.0.1:8000 | Legacy static frontend |
| http://127.0.0.1:8000/api/docs | Swagger API docs |
| http://127.0.0.1:5173 | React SPA (Vite dev server) |

### Build React Frontend (deploy to `static/`)

```bash
cd frontend && npm run build
# Output goes to ../static/ — served by FastAPI at /
```

## Environment Variables

Required:

```env
DATABASE_URL=sqlite:///./data/app.db         # SQLite (dev) or PostgreSQL (prod)
GROQ_API_KEY=your_groq_api_key
MODEL_NAME=llama-3.1-8b-instant
SECRET_KEY=replace-with-a-random-32-plus-character-secret
DEBUG=false
```

PostgreSQL/Supabase:

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres?sslmode=require
PGSSLMODE=require
DATABASE_CONNECT_TIMEOUT=10
AUTO_CREATE_DB_SCHEMA=true
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

Keep `.env` private. It is ignored by Git.

## Role-Based Access Control

Public registration always creates a `candidate` account.

| Role | Access |
| --- | --- |
| candidate | Browse jobs, apply with PDF resume, view own applications, interview, profile |
| hr | Manage jobs, view candidates, review applications, rank applicants, manage departments/designations |
| manager | View candidates, review applications, rank applicants |
| admin | Bypasses role checks for all protected backend routes |
| employee | View dashboard, attendance, leave, skill gap, tickets, training, onboarding, profile |

Create privileged users:

```bash
python -m scripts.bootstrap_user --username admin --password "CHANGE_ME" --role admin
python -m scripts.bootstrap_user --username hr_user --password "CHANGE_ME" --role hr
```

After changing a user's role, log out and log back in so the frontend receives a new JWT and refreshes the stored user role.

## API Routes

| Router | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/auth` | Register, Login |
| Resume | `/api/resume` | Upload PDF, get parsed resume, lab analyze/fix/rewrite |
| Jobs | `/api/jobs` | Job CRUD (HR creates, candidate reads) |
| Applications | `/api/applications` | Apply, list, AI analyze, rank candidates |
| Candidates | `/api/candidates` | List/get candidates |
| Employees | `/api/employees` | List/get, dashboard, attendance, leave, skill gap, AI assistant |
| Dashboard | `/api/dashboard` | HR, candidate, employee, manager aggregated data |
| Interview | `/api/interview` | 18 endpoints: start, answer, sessions, coaching, leaderboard, credibility, compare |
| Training | `/api/training` | Programs, assignments, progress tracking |
| Profile | `/api/profile` | Candidate/employee profiles, document upload/review |
| Onboarding | `/api/onboarding` | Templates, tasks, plans, required documents |
| Lifecycle | `/api/lifecycle` | Employee lifecycle events |
| Attendance | `/api/employees/attendance` | Check-in, check-out, records |
| Leave | `/api/employees/leave` | Apply, approve/reject, list |
| Notifications | `/api/notifications` | List, mark read |
| Tickets | `/api/tickets` | Create, assign, track employee tickets |
| Departments | `/api/departments` | CRUD departments |
| Designations | `/api/designations` | CRUD designations |
| Salary | `/api/salary` | Salary revisions, history |
| Promotions | `/api/promotions` | Promotion history |

## Data Migration

To migrate legacy SQLite data into Supabase PostgreSQL:

```bash
python -m scripts.migrate_sqlite_to_postgres --source path/to/legacy.db
```

The destination database should be empty before migration.

## Testing

```bash
pytest tests/ -v
pytest tests/test_api.py -v
```

## Deployment

### Docker

```bash
docker build -t talentforge-ai .
docker run --env-file .env -p 8000:8000 talentforge-ai
```

### Render

Render deployment is supported through `render.yaml`. Configure at least `DATABASE_URL`, `SECRET_KEY`, and `GROQ_API_KEY` in Render.

See [docs/deployment.md](docs/deployment.md) for the full deployment guide.

## AI Reliability

If Groq or CrewAI is unavailable, applications are still saved. TalentForge falls back to deterministic scoring and still returns a recommendation, explainability summary, and interview preparation material.
