# TalentForge AI Deployment Guide

TalentForge runs as one FastAPI service. The backend serves the API and the static frontend from `static/`.

## Supabase PostgreSQL Setup

1. Create a Supabase project.
2. Click **Connect** in the Supabase dashboard.
3. Copy the **Session pooler** PostgreSQL connection string.
4. URL-encode special characters in the database password.
5. Set `DATABASE_URL` with `sslmode=require`.

Example:

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres?sslmode=require
PGSSLMODE=require
AUTO_CREATE_DB_SCHEMA=true
```

The backend uses SQLModel directly over PostgreSQL. Session pooler mode is the default because this is a persistent API service and the pooler supports both IPv4 and IPv6. A direct connection is also suitable when the deployment host supports IPv6. Supabase API keys are not currently required by application logic, but may be stored as project metadata for future Supabase client features.

## Required Environment Variables

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

Keep `SUPABASE_SERVICE_ROLE_KEY` server-side only. Never expose it to browser code.

## Initialize Schema

After configuring `.env`, run:

```bash
python -m scripts.init_database
```

The script creates the SQLModel tables and applies the existing lightweight compatibility migrations.

## Bootstrap Privileged Users

Public registration creates candidate accounts only. Create HR, manager, and admin users from the server:

```bash
python -m scripts.bootstrap_user --username admin --password "CHANGE_ME" --role admin
python -m scripts.bootstrap_user --username hr_user --password "CHANGE_ME" --role hr
```

## Copy Existing SQLite Data

If local SQLite data must be retained, point `.env` at Supabase PostgreSQL and run:

```bash
python -m scripts.migrate_sqlite_to_postgres --source path/to/legacy.db
```

The destination must be empty. The script creates tables, copies available source tables in foreign-key order, and resets PostgreSQL identity sequences.

## Render Deployment

1. Push the repository to GitHub.
2. Create a Render Blueprint or web service using `render.yaml`.
3. Add the Supabase `DATABASE_URL`.
4. Add `GROQ_API_KEY`.
5. Add optional Supabase metadata only if you intend to use it later.
6. Deploy.

Render provides `PORT` automatically. The Dockerfile listens on that port.

## Local Run Against Supabase

```bash
pip install -r requirements.txt
python -m scripts.init_database
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Health check:

```text
GET /api/health
```
