# TalentForge AI — AGENTS.md

## Overview
FastAPI 2.0 app (`src.main:app`) for full-cycle HRMS: resume analysis, job matching, recruitment, employee lifecycle, attendance, leave, skill gap, tickets, notifications, and mock interviews. Uses CrewAI + Groq LLM, SQLModel (SQLite/PostgreSQL), and a **React 19 + Vite SPA frontend**. Legacy static HTML/JS frontend at `static/` served as fallback.

## Quickstart
```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in GROQ_API_KEY at minimum
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (optional — React SPA)
cd frontend && npm install && npm run dev
```
- **API docs**: `http://127.0.0.1:8000/api/docs`
- **Backend frontend**: `http://127.0.0.1:8000/` (serves `static/`)
- **React frontend**: `http://127.0.0.1:5173/` (Vite dev server)

## Project Structure
```
src/
  main.py              # FastAPI entry point, lifespan, routing
  config.py            # Pydantic Settings (reads .env)
  resume_lab.py        # Resume parsing, analysis, fix logic (pure functions)
  database/connection.py # SQLModel engine + migration helpers
  models/              # SQLModel tables (users, jobs, resumes, applications, AI analyses,
                       #   employees, attendance, leave, skill_gap, lifecycle, tickets,
                       #   notifications, departments, designations, salary)
  api/routes/          # Auth, resume, jobs, applications, candidates, employees, dashboard,
                       #   interview, lifecycle, attendance, leave, notifications, tickets,
                       #   departments, designations, salary
  api/dependencies.py  # JWT guards (candidate_required, hr_admin_required, etc.)
  core/security.py     # JWT + bcrypt
  core/exceptions.py   # HTTP exception handlers
  services/recruitment_ai.py # CrewAI recruitment analysis orchestration
agents/                # CrewAI agent definitions (calls into crew.py)
tasks/                 # CrewAI task definitions
utils/                 # Resume parser, job search, scorers
scripts/               # DB bootstrap, init, migration utilities
crew.py                # Legacy Crew orchestration
frontend/              # React 19 + Vite SPA
  src/                 # Components, pages, API clients, assets
  public/              # Static assets
static/                # Legacy built frontend (fallback)
tests/                 # pytest suite
```

## Backend Routes (`src/api/routes/`)
| Router | Registered? | Description |
|--------|-------------|-------------|
| `auth` | ✅ | Register, Login |
| `resume` | ✅ | Upload PDF, get parsed resume |
| `jobs` | ✅ | Job CRUD (HR creates, candidate reads) |
| `applications` | ✅ | Apply, list, AI analyze, rank candidates |
| `candidates` | ✅ | List/get candidates |
| `employees` | ✅ | List/get employees |
| `dashboard` | ✅ | HR & Candidate dashboard aggregated data |
| `interview` | ✅ **Now Registered!** | 9 endpoints: start, answer, sessions, coaching memory, daily plan |
| `lifecycle` | ✅ | Employee lifecycle events, promotions |
| `attendance` | ✅ | Check-in/out, records |
| `leave` | ✅ | Apply, approve/reject, list |
| `notifications` | ✅ | List, mark read |
| `tickets` | ✅ | Create, assign, track employee tickets |
| `departments` | ✅ | CRUD departments |
| `designations` | ✅ | CRUD designations |
| `salary` | ✅ | Salary revisions, history |

## Frontend Architecture
- **React 19** with **Vite** bundler
- **Framer Motion** for animations
- API clients per domain: `auth.js`, `jobs.js`, `applications.js`, `employees.js`, `departments.js`, `tickets.js`, etc.
- Component structure: `Dashboard`, `EmployeeDashboard`, `HRDashboard`, `CandidateDashboard`, auth views, etc.
- Dev server: `cd frontend && npm run dev` (port 5173)
- Build: `cd frontend && npm run build` (outputs to `static/`)

## Backend Models (new since Day 3)
| Model | Key Fields |
|-------|-----------|
| `AttendanceRecord` | user_id, date, check_in, check_out, status |
| `LeaveRequest` | user_id, type, start_date, end_date, status, approved_by |
| `SkillGapAnalysis` | user_id, current_skills, required_skills, gaps, recommendations |
| `EmployeeLifecycleEvent` | employee_id, event_type, old_value, new_value, performed_by |
| `HRNotification` | user_id, type, message, is_read, created_at |
| `Ticket` | user_id, subject, description, priority, status, assigned_to |
| `Department` | name, description, head_id, is_active |
| `Designation` | title, department_id, rank, is_active |
| `SalaryRevision` | employee_id, old_salary, new_salary, effective_date, approved_by |

## Auth & RBAC
- **JWT + bcrypt**: Tokens from `/api/auth/register` or `/api/auth/login`
- **Guards** in `src/api/dependencies.py`:
  - `candidate_required` — candidates only
  - `management_required` — hr, manager, admin
  - `hr_admin_required` — hr, admin
  - `employee_required` — employee role
- Roles: `candidate | employee | hr | manager | admin`

## Testing
```bash
pytest tests/ -v
pytest tests/test_api.py::test_register_and_login -v
```

## Key Conventions
- **Imports**: Use absolute `from src.config ...` style
- **Database**: SQLite locally, PostgreSQL in production via `DATABASE_URL`
- **Migrations**: `SQLModel.metadata.create_all(engine)` on startup + `_ensure_*` idempotent ALTER TABLE functions
- **Auth**: JWT via `HTTPBearer` in `src/api/dependencies.py`

## Important Gotchas
- Interview routes (`1362` lines) are now registered — make sure they remain wired after any `src/main.py` refactors
- Interview uses 5-agent CrewAI flow with adaptive difficulty, coaching memory, and 4 training modes — frontend integration still pending
- `src/resume_lab.py` validates + repairs LLM output to match `ResumeAnalysisResult` schema
- `data/` dir for temp DB files (tests) and CrewAI storage — should be in `.gitignore`
- `src/main.py` strips bad `127.0.0.1:9` proxy vars at import time (Windows fix for Groq/Jooble API)

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
