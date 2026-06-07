# TalentForge AI Supabase Migration Report

## Scope

This stabilization pass prepares TalentForge AI for Supabase PostgreSQL without starting Day 3 features. Existing SQLModel models, APIs, recruitment services, and CrewAI integration remain in place.

## Day 2 Architecture Review

The Day 2 implementation remains the right fit for the current delivery stage:

- Recruitment AI logic lives in `src/services/recruitment_ai.py`, outside route handlers.
- The CrewAI recruitment analyst is loaded only when analysis runs, avoiding startup failures when the AI runtime is unavailable.
- Application data is committed before analysis begins.
- A deterministic fallback persists an explainable score, recommendation, strengths, weaknesses, missing skills, and interview questions when the AI provider fails.
- Rankings use persisted analysis outputs and remain easy to explain.

This keeps the primary demo flow reliable without adding queues or additional infrastructure prematurely.

## Database Configuration

Normal operation now requires an explicit `DATABASE_URL`. The recommended Supabase value is the Session pooler connection string with TLS enabled:

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres?sslmode=require
PGSSLMODE=require
DATABASE_CONNECT_TIMEOUT=10
AUTO_CREATE_DB_SCHEMA=true
```

SQLite remains supported only when explicitly configured for isolated regression tests and one-time legacy data migration.

The preserved local migration source is `talentforge.db` (renamed from `jobify.db`). It currently contains 7 users, 1 job posting, and 1 candidate application.

## Current Tables

- `users`
- `resumes`
- `job_applications`
- `interview_sessions`
- `career_coach_memory`
- `job_postings`
- `candidate_applications`
- `application_ai_analyses`
- `employees`

The legacy tables remain available as reusable infrastructure but are not exposed by TalentForge navigation or route registration.

## Operational Scripts

Initialize a configured Supabase database:

```bash
python -m scripts.init_database
```

Create controlled privileged accounts:

```bash
python -m scripts.bootstrap_user --username admin --password "CHANGE_ME" --role admin
python -m scripts.bootstrap_user --username hr_user --password "CHANGE_ME" --role hr
```

Copy an existing SQLite database into an empty configured PostgreSQL database:

```bash
python -m scripts.migrate_sqlite_to_postgres --source path/to/legacy.db
```

## Stability Fixes

- Public registration is candidate-only and rejects attempted role injection.
- Login no longer creates accounts implicitly or repairs malformed password records.
- PostgreSQL connections use TLS normalization, connection timeout, pre-ping, and pool recycling.
- Standalone schema initialization explicitly registers all SQLModel definitions before creating tables.
- Deleting a job with existing applications returns `409 Conflict` instead of surfacing a PostgreSQL foreign-key error.
- Remaining active local `jobify.db`, `jobify_user`, and SQLite-default naming was removed.

## Validation Completed

Validated locally with an explicit temporary SQLite regression adapter:

- Candidate registration and login.
- HR, manager, admin, and employee login after controlled role setup.
- JWT role payloads.
- Candidate, employee, HR, manager, and admin RBAC behavior.
- Job creation, listing, detail, editing, and deletion.
- Protected deletion for jobs with candidate applications.
- PDF upload path and parsed resume-text persistence.
- Candidate application persistence with default `Applied` status.
- AI analysis persistence, recruiter review, re-analysis, and ranking.
- AI-provider failure fallback with application preservation.
- Candidate listing and detail endpoints.
- Employee listing and detail endpoints.
- Schema initialization script.
- Privileged-user bootstrap script.
- PostgreSQL URL normalization and TLS configuration.
- Migration guard that refuses non-PostgreSQL targets.
- Python compilation and frontend JavaScript syntax checks.

## Manual Supabase Step Still Required

An actual Supabase connection and data copy could not be executed because this workspace does not contain a configured `.env` or Supabase credentials.

After adding credentials:

1. Run `python -m scripts.init_database`.
2. Run `python -m scripts.migrate_sqlite_to_postgres --source path/to/legacy.db` only if legacy SQLite data must be retained.
3. Bootstrap HR and admin users with `python -m scripts.bootstrap_user`.
4. Start the app and repeat the candidate and recruiter workflows against Supabase.

## Remaining Technical Debt

- Lightweight startup migrations are still used instead of Alembic.
- Legacy Jobify source modules remain in the repository as disabled reusable infrastructure.
- Duplicate applications for the same candidate and job are currently allowed.
- Resume text normalization can over-separate some acronym plurals, such as `APIs` becoming `AP Is`.
- Supabase API metadata keys are reserved for future Supabase client features; SQLModel currently connects through `DATABASE_URL` directly.
- The optional `graphify update .` repository hook currently fails on this Windows workspace with `Access is denied`.
- Docker packaging still needs a local build confirmation after the Docker Desktop Linux engine is started.
