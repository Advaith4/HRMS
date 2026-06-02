# Jobify AGENTS.md

## Overview
Jobify is a FastAPI backend app for resume analysis, job feed, and mock interviews. It uses CrewAI agents, SQLModel (SQLite/PostgreSQL), and static HTML/JS frontend. App entry is `src/main.py`.

## Dev Environment
- **Python**: 3.10 (-repo uses `requirements.txt`, not `pyproject.toml`)
- **Venv**: Create `python -m venv .venv && source .venv/bin/activate` then `pip install -r requirements.txt`
- **Run**: `uvicorn src.main:app --reload --host 127.0.0.1 --port 8000`
- **Alternative**: `python app.py` (compatibility wrapper around `src.main`)
- **API Docs**: `http://127.0.0.1:8000/api/docs`
- **Frontend**: `http://127.0.0.1:8000/` (served from `static/`)

## Project Structure
```
src/
  main.py              # FastAPI entry point, lifespan, routing
  config.py            # Pydantic Settings (reads .env)
  resume_lab.py        # Resume parsing, analysis, fix logic (pure functions)
  database/connection.py # SQLModel engine + lightweight migration helpers
  models/              # SQLModel tables: User, Resume, JobApplication, InterviewSession, CareerCoachMemory
  api/routes/          # Auth, Resume, Jobs, Interview (FastAPI routers)
  core/security.py     # JWT + bcrypt
agents/                # CrewAI agent definitions (calls into crew.py)
tasks/                 # CrewAI task definitions
utils/                 # Resume parser, job search, scorers
crew.py                # Crew orchestration: job pipeline, resume analyzer, interview coach
```

## Key Conventions
- **Imports**: Use absolute `from src.config ...` style (not `from .config`).
- **Database**: SQLite by default (`DATABASE_URL=sqlite:///./jobify.db`). Postgres via `postgresql://`.
- **Migrations**: Not Alembic. `src/database/connection.py` runs lightweight `ALTER TABLE` migrations at startup (idempotent).
- **Auth**: JWT via `HTTPBearer` in `src/api/dependencies.py`. Tokens from `/api/auth/register` or `/api/auth/login`.
- **Environment**: Load via `.env` (copied from `.env.example`).

## Testing
- **Command**: `pytest tests/ -v` (from repo root)
- **Key test files**:
  - `tests/test_api.py`: Auth, file upload, feed integration tests (uses `TestClient`).
  - `tests/test_resume_lab.py`: Resume parsing, fix application, scoring logic.
- Tests depend on FastAPI’s `TestClient` and a temporary DB.

## Running One-Off Tests
- Single module: `pytest tests/test_api.py -v`
- Single test: `pytest tests/test_api.py::test_register_and_login -v`

## Sending API Requests
Most endpoints (besides auth and health) require the `Authorization: Bearer <token>` header. Example:

```bash
curl -X POST http://127.0.0.1:8000/api/resume/analyze \
  -H "Authorization: Bearer <your_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"target_role": "Backend Developer"}'
```

## CrewAI / LLM Flow
- **Resume**: `analyze_resume` → `crew.py run_resume_analyzer` → uses `create_resume_optimizer` agent + `create_resume_analysis_task`.
- **Jobs**: `run_job_crew` → infers roles from resume, fetches live jobs via `fetch_jobs_for_roles`, ranks them via CrewAI against the resume.
- **Interview**: `run_interview_start` / `run_interview_answer` → orchestrates interviewer, evaluator, difficulty controller, and followup coach agents/tasks.
- **Tailor**: `run_tailored_resume_rewriter` runs in a FastAPI `BackgroundTask` when a job is tracked.

## Environment Variables (from .env.example)
```
GROQ_API_KEY=
JOOBLE_API_KEY=
JOOBLE_API_BASE_URL=https://in.jooble.org/api/{api_key}
RAPIDAPI_KEY=
DATABASE_URL=sqlite:///./jobify.db
SECRET_KEY=
AUTO_CREATE_DB_SCHEMA=true
DEBUG=false
MODEL_NAME=llama-3.1-8b-instant
```

## Deployment
- **Docker**: `docker build -t jobifyai .` then `docker run --env-file .env -p 8000:8000 jobifyai`
- **Render**: `render.yaml` is provided. Sets `AUTO_CREATE_DB_SCHEMA=true` and pulls `DATABASE_URL` from a Render Postgres instance.
- **Vercel**: `vercel.json` for static frontend (`static/`). Backend runs elsewhere (e.g. Render).

## Important Gotchas
- `crew.py` agents/tasks are imported dynamically; if you rename modules in `agents/` or `tasks/`, update the corresponding `from tasks...` / `from agents...` imports.
- The database uses lightweight migrations at startup (`_ensure_*` functions). If you add new fields to `models/__init__.py`, also update the `_ensure_*` migration logic for SQLite/Postgres.
- `src/resume_lab.py` contains deterministic validation and repair logic for LLM analysis. LLM output is expected to match `ResumeAnalysisResult` schema.
- `src/main.py` clears Windows-broken proxy variables (`127.0.0.1:9`) that can break Groq/Jooble APIs.

## Tech Stack
- FastAPI + Uvicorn
- SQLModel (SQLite / PostgreSQL)
- CrewAI (agents in `agents/`, tasks in `tasks/`)
- Groq LLM for inference
- JWT & bcrypt for auth
- pypdf for PDF resume parsing

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
