# TalentForge AI

TalentForge AI is a recruitment intelligence platform for candidates, HR teams, and managers. It combines a FastAPI backend, SQLModel persistence, Supabase PostgreSQL, CrewAI/Groq analysis, and a static HTML/CSS/JavaScript frontend served from the same app.

## Features

- Candidate registration, login, resume upload, and job applications
- JWT authentication with role-based access control
- HR job posting management
- Manager/HR candidate and application review
- PDF resume parsing for applications
- AI recruitment analysis with deterministic fallback scoring
- Fit scores, recommendations, strengths, weaknesses, missing skills, and interview prep
- Per-job candidate rankings
- Supabase PostgreSQL migration helpers
- Docker and Render deployment support

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | HTML, CSS, JavaScript |
| Backend | FastAPI, Uvicorn |
| Database | SQLModel, Supabase PostgreSQL |
| AI orchestration | CrewAI |
| LLM provider | Groq |
| Authentication | JWT, bcrypt |
| Resume parsing | pypdf |
| Deployment | Docker, Render |

## Local Setup

Use Python 3.10.

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` with your Supabase PostgreSQL connection string, `SECRET_KEY`, and `GROQ_API_KEY`.

Initialize the database schema:

```bash
python -m scripts.init_database
```

Run the app:

```bash
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Open the frontend:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/api/docs
```

## Environment Variables

Required:

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres?sslmode=require
PGSSLMODE=require
DATABASE_CONNECT_TIMEOUT=10
AUTO_CREATE_DB_SCHEMA=true
GROQ_API_KEY=your_groq_api_key
MODEL_NAME=llama-3.1-8b-instant
SECRET_KEY=replace-with-a-random-32-plus-character-secret
DEBUG=false
```

Optional Supabase metadata:

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

Keep `.env` private. It is ignored by Git.

## Role-Based Access Control

Public registration always creates a `candidate` account. This prevents users from self-registering as HR or admin.

Supported roles:

| Role | Access |
| --- | --- |
| candidate | Browse jobs, apply with a PDF resume, view own applications |
| hr | Manage jobs, view candidates, review applications, rank applicants |
| manager | View candidates, review applications, rank applicants |
| admin | Bypasses role checks for protected backend routes |
| employee | Reserved for future HRMS features |

Create privileged users from the server:

```bash
python -m scripts.bootstrap_user --username admin --password "CHANGE_ME" --role admin
python -m scripts.bootstrap_user --username hr_user --password "CHANGE_ME" --role hr
```

After changing a user's role, log out and log back in so the frontend receives a new JWT and refreshes the stored user role.

## Data Migration

To migrate legacy SQLite data into Supabase PostgreSQL:

```bash
python -m scripts.migrate_sqlite_to_postgres --source path/to/legacy.db
```

The destination database should be empty before migration.

## Testing

```bash
pytest tests/ -v
```

Run a single test module:

```bash
pytest tests/test_api.py -v
```

## Deployment

Docker:

```bash
docker build -t talentforge-ai .
docker run --env-file .env -p 8000:8000 talentforge-ai
```

Render deployment is supported through `render.yaml`. Configure at least `DATABASE_URL`, `SECRET_KEY`, and `GROQ_API_KEY` in Render.

See [docs/deployment.md](docs/deployment.md) for the full deployment guide.

## AI Reliability

If Groq or CrewAI is unavailable, applications are still saved. TalentForge falls back to deterministic scoring and still returns a recommendation, explainability summary, and interview preparation material.
