# Cleanup Verification Report

Generated: 2026-06-07

Scope: `C:\Users\ADVAITH G\Documents\HRMS`

No files were deleted. No source code, deployment config, or application files were modified.

## Verification Summary

The previous cleanup report is mostly directionally correct, but the safest classification needs tightening because the application is currently working and multiple runtime/deployment paths depend on `static/` and `data/`.

Key findings:

- `static/` is actively used by FastAPI, Docker, and Vercel. Do not delete it from the current working app unless the frontend is rebuilt immediately afterward.
- `data/` is active runtime storage for uploads, temporary resume extraction, and CrewAI storage. Do not blanket-delete it.
- `.venv/` and `frontend/node_modules/` are dependency folders, not source, but deleting them affects local ability to run/build until dependencies are recreated.
- `graphify-out/cache/`, `graphify-out/.graphify_old.json`, Python caches, pytest cache, duplicate ZIP reports, and temporary logs have no app runtime dependency.
- `audit_reports/`, `phase2_reports/`, and `artifacts/` are report/documentation evidence, not app runtime dependencies. Treat them as archive/manual-review, not automatic deletion.

## Reference Search Results

Searched for:

- `static/`
- `graphify-out/`
- `data/`
- `audit_reports/`
- `phase2_reports/`
- `artifacts/`

Important references found:

| Path | Reference | Impact |
|---|---|---|
| `src/main.py` | Creates `data/.crewai_storage`, creates `static`, mounts `SPAStaticFiles(directory="static")` at `/` | `data/` and `static/` are runtime paths |
| `src/api/routes/applications.py` | Writes temporary uploaded resumes to `data/application_resume_<uuid>.pdf`, then deletes them | `data/` directory must exist or be creatable |
| `src/api/routes/resume.py` | Writes temporary uploaded resumes to `data/resume_<uuid>.pdf`, then deletes them | `data/` directory must exist or be creatable |
| `src/api/routes/profile.py` | `UPLOAD_ROOT = Path("data") / "profile_documents"` and serves uploaded files | `data/profile_documents` is persistent runtime data |
| `frontend/vite.config.js` | `build.outDir = "../static"` | `static/` is rebuild output |
| `Dockerfile` | `COPY ./static ./static` | Docker production image expects committed/built `static/` |
| `vercel.json` | Builds and routes `static/**` | Vercel config depends on `static/` |
| `README.md`, `AGENTS.md`, `docs/deployment.md` | Document `static/` build/serving and `data/` runtime usage | Confirms expected architecture |
| `AGENTS.md` | Recommends `graphify-out/` for codebase questions | Useful developer artifact, but cache is not runtime |

## Deployment Verification

### `render.yaml`

Render uses Docker:

- `runtime: docker`
- `dockerfilePath: ./Dockerfile`
- `dockerContext: .`

No direct `static/` path is named in `render.yaml`, but Docker build includes `static/`.

### `Dockerfile`

Docker copies only selected runtime folders:

- `src/`
- `agents/`
- `tasks/`
- `utils/`
- `scripts/`
- `crew.py`
- `static/`

It creates `/app/data` inside the image. It does not copy `.venv`, `frontend/node_modules`, graphify cache, audit reports, phase reports, or artifacts.

Conclusion: `.venv/`, `frontend/node_modules/`, `graphify-out/cache/`, reports, and scratch files are not Docker runtime dependencies. `static/` is a Docker runtime dependency unless rebuilt and present before Docker build.

### `docker-compose.yml`

Only defines PostgreSQL. It does not mount or depend on:

- `static/`
- `graphify-out/`
- `audit_reports/`
- `phase2_reports/`
- `artifacts/`

### `vercel.json`

Vercel is configured entirely around `static/**`:

- build source: `static/**`
- `/` routes to `/static/index.html`
- asset routes resolve to `/static/$1`

Conclusion: do not delete `static/` if Vercel deployment is still used.

## FastAPI Static File Serving Verification

`src/main.py` defines `SPAStaticFiles` and mounts it last:

- `os.makedirs("static", exist_ok=True)`
- `app.mount("/", SPAStaticFiles(directory="static", html=True), name="static")`
- SPA fallback serves `index.html` for non-API, non-docs 404s.

Conclusion:

- Backend APIs can still import if `static/` is empty because `src/main.py` creates the directory.
- The working web UI will break if `static/index.html` and assets are removed without rebuilding.
- Therefore `static/` is **SAFE_TO_DELETE_AFTER_REBUILD**, not safe to delete now for a working app.

## SAFE_TO_DELETE_NOW

These have no runtime dependency in the app and can be removed from local disk when no tooling process is actively using them.

| Path | Verification |
|---|---|
| `graphify-out/cache/` | Generated graphify cache only. `graphify-out/graph.json`, `graph.html`, and `GRAPH_REPORT.md` can remain. |
| `graphify-out/.graphify_old.json` | Old graph backup, not referenced by app runtime or deployment. |
| `__pycache__/` | Python bytecode cache. |
| `.pytest_cache/` | Test cache only. |
| `audit_reports.zip` | Duplicate report archive, not runtime. |
| `phase2_reports.zip` | Duplicate report archive, not runtime. |
| `script_errors.txt` | Temporary log/output file, not runtime. |

## SAFE_TO_DELETE_AFTER_REBUILD

These are safe only after recreating dependencies or rebuilding outputs.

| Path | Required follow-up |
|---|---|
| `.venv/` | Recreate with `python -m venv .venv` and reinstall with `pip install -r requirements.txt`. Stop local backend processes first. |
| `frontend/node_modules/` | Recreate with `npm install` in `frontend/`. Needed for frontend dev/build/test commands. |
| `static/` | Recreate with `cd frontend; npm install; npm run build`. Required by FastAPI SPA serving, Docker image build, and Vercel config. |

## DO_NOT_DELETE

Do not delete these as part of automatic cleanup for the currently working app.

| Path | Reason |
|---|---|
| `src/`, `agents/`, `tasks/`, `utils/`, `scripts/`, `crew.py` | Runtime/source code copied into Docker or imported by the app. |
| `frontend/src/`, `frontend/public/`, frontend config/package files | Source needed to rebuild `static/`. |
| `requirements.txt`, `frontend/package-lock.json` | Dependency manifests required to recreate environments. |
| `Dockerfile`, `docker-compose.yml`, `render.yaml`, `vercel.json` | Deployment configuration. |
| `data/profile_documents/` | Persistent uploaded candidate/employee documents. |
| `data/.crewai_storage/` | CrewAI local storage. Can be reset only if losing local CrewAI state is acceptable. |
| `.env` | Local secrets/config. Not tracked, but required for local app configuration. |
| `audit_reports/`, `phase2_reports/`, `artifacts/` | Generated evidence/reports. Archive or inspect manually before deletion. |
| `docs/screenshots/` | Documentation screenshots. Keep unless docs no longer need them. |
| `graphify-out/graph.json`, `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/manifest.json` | Current graphify outputs useful for codebase navigation. Not runtime, but intentionally kept per project guidance. |

## Final Recommendation

For the current working app, the safest immediate cleanup set is limited to caches and duplicate archives:

```powershell
graphify-out\cache
graphify-out\.graphify_old.json
__pycache__
.pytest_cache
audit_reports.zip
phase2_reports.zip
script_errors.txt
```

Delay deletion of `.venv/`, `frontend/node_modules/`, and `static/` until you are ready to recreate dependencies and rebuild the frontend.

Do not blanket-delete `data/`.
