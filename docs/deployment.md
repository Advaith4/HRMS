# Deployment Guide

This app is a single FastAPI service. The backend serves the API and the static frontend from `static/`, so deploy it as one web service.

## Recommended: Render with Docker

1. Push this repository to GitHub.
2. In Render, create a new Blueprint or Web Service from the repository.
3. Use the included `render.yaml` if Render asks for Blueprint config.
4. Add environment variables:
   - `DATABASE_URL`: a hosted Postgres URL from Supabase, Neon, Render Postgres, or another provider.
   - `GROQ_API_KEY`: required for AI agent features.
   - `JOOBLE_API_KEY`: recommended for real job search.
   - `RAPIDAPI_KEY`: optional fallback for job search.
5. Deploy.

Render provides `PORT` automatically. The Dockerfile now listens on that port.

## Database Notes

For a real deployment, use Postgres. SQLite is fine for local demos, but most hosted containers have ephemeral storage, so `jobify.db` can disappear on redeploy unless you attach a persistent disk.

Set:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DB_NAME
AUTO_CREATE_DB_SCHEMA=true
```

`AUTO_CREATE_DB_SCHEMA=true` lets the app create the SQLModel tables on startup.

## Local Docker Test

```bash
docker build -t jobify .
docker run --env-file .env -p 8000:8000 jobify
```

Then open `http://127.0.0.1:8000`.

## Health Check

The app exposes:

```text
/api/health
```

It should return:

```json
{"status":"ok"}
```
