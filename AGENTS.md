# TalentForge AI — AGENTS.md

## Stack & Entrypoints
- **Backend:** FastAPI at `src.main:app` (uvicorn). 20 routers registered in `src/main.py:144-162`.
- **Frontend:** React 19 + Vite SPA at `frontend/`, `npm run dev` (port 5173), `npm run build` (outputs to `../static/`).
- **Database:** SQLModel (SQLite dev, PostgreSQL prod). Tables auto-created on startup via `SQLModel.metadata.create_all` + idempotent `_ensure_*` ALTER TABLE functions in `src/database/connection.py`.
- **AI:** CrewAI + Groq (`llama-3.1-8b-instant`). Deterministic fallback if LLM unavailable.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill GROQ_API_KEY at minimum
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
# Frontend (optional):
cd frontend && npm install && npm run dev
```

## Testing
- **Isolated SQLite DB per run:** `DATABASE_URL` is overridden to `sqlite:///data/test_<uuid>.db` *before* importing `src.main` (see `tests/test_api.py:8`).
- No Groq API key or external services needed — AI calls are monkeypatched in tests.
```bash
pytest tests/ -v
pytest tests/test_api.py::test_register_and_login_returns_role -v
```

## Auth & RBAC
- JWT (HS256, 7-day expiry) via `HTTPBearer`. Guards in `src/api/dependencies.py`:
  - `candidate_required`, `management_required` (hr/manager/admin), `hr_admin_required` (hr/admin), `employee_required`
  - `require_roles()` dependency — admin bypasses all role checks.
- Roles: `candidate | employee | hr | manager | admin`. Public registration always creates `candidate`.
- Bootstrap privileged users: `python -m scripts.bootstrap_user --username admin --role admin`

## Architecture
```
src/
  main.py              # FastAPI factory, lifespan, 20 router includes, SPAStaticFiles fallback
  config.py            # Pydantic Settings from .env (extra="allow")
  resume_lab.py        # PDF text repair, section parsing, LLM analysis validation (pure functions)
  database/connection.py # Engine + idempotent migration functions (_ensure_*)
  models/__init__.py   # 30+ SQLModel tables (User, Resume, CandidateApplication, InterviewSession, etc.)
  api/routes/          # 20 routers: auth, resume, jobs, applications, candidates, employees,
                       #   dashboard, interview, mock_interview, departments, designations,
                       #   lifecycle, tickets, salary, promotions, notifications,
                       #   onboarding, training, profile
  api/dependencies.py  # JWT guards (get_current_user, require_roles)
  core/security.py     # JWT encode/decode, bcrypt hash/verify
  services/
    recruitment_ai.py  # CrewAI orchestration + fallback scorer for application analysis
    employee_ai.py     # Skill gap analysis + AI HR chatbot (policy-aware)
agents/                # CrewAI agent definitions
tasks/                 # CrewAI task definitions
crew.py                # Legacy — do not reference
static/                # Built frontend assets (served by FastAPI at /)
```

## Key Gotchas
- **`src/main.py` strips bad `127.0.0.1:9` proxy vars** at import time (Windows breakage for Groq/Jooble API).
- **CrewAI storage isolation:** `CREAI_STORAGE_DIR=talentforge_local`, `appdirs` monkeypatched to `data/.crewai_storage/` (see `src/main.py:88-99`).
- **DB migrations** are all at startup via `_ensure_*` functions (idempotent ALTER TABLE). Add new ones in `create_db_and_tables()` in `src/database/connection.py`.
- **AI analysis runs as FastAPI `BackgroundTasks`** — HTTP response returns <1s, score appears asynchronously.
- **No Python lint/typecheck tools** (no ruff, mypy, flake8). Only pytest.
- **Frontend `npm run lint`** runs eslint. No pre-commit hooks.
- **CORS** allows `["http://localhost:8000", "http://127.0.0.1:8000"]` by default.
- **Axios** has 30s GET cache, 60s timeout, 401 auto-logout (`frontend/src/api/axios.js`).
- **`.gitignore` excludes `.opencode/`, `.agents/`, `.codex/`** — local tool configs not committed.
- **`InterviewSession`** and **`MockInterviewSession`** are separate models with separate routers.

## graphify

This project has a knowledge graph at graphify-out/. Use it for codebase questions:
- `graphify query "<question>"` — scoped subgraph (preferred over raw grep)
- `graphify path "<A>" "<B>"` — file relationships
- `graphify explain "<concept>"` — focused concept
- After modifying code: `graphify update .` (AST-only, no API cost)
