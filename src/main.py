"""
src/main.py
FastAPI application entry point.

Run locally:
    uvicorn src.main:app --reload --port 8000
Docker:
    CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path


def _configure_console_encoding() -> None:
    """
    Prefer UTF-8 output on Windows without replacing pytest/stdout capture objects.
    Reconfiguring the existing streams avoids teardown errors during test runs.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                continue


_configure_console_encoding()


def _disable_broken_local_proxies() -> None:
    """
    Some Windows setups inject dead proxy vars like 127.0.0.1:9, which break
    outbound HTTP for Groq, Jooble, RapidAPI, and related SDKs. Clear only
    those known-bad values and leave legitimate proxy configs untouched.
    """
    proxy_vars = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "GIT_HTTP_PROXY",
        "GIT_HTTPS_PROXY",
    )
    bad_markers = ("127.0.0.1:9", "localhost:9")

    for var in proxy_vars:
        value = os.getenv(var, "")
        if value and any(marker in value for marker in bad_markers):
            os.environ.pop(var, None)


_disable_broken_local_proxies()

from datetime import datetime, timezone
import appdirs
from fastapi import FastAPI
from fastapi import FastAPI, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.routes import (
    admin,
    applications,
    auth,
    candidates,
    dashboard,
    departments,
    designations,
    employees,
    interview,
    jobs,
    lifecycle,
    mock_interview,
    notifications,
    onboarding,
    profile,
    promotions,
    rag,
    resume,
    salary,
    tickets,
    training,
)
from src.config import settings
from src.core.exceptions import http_exception_handler, validation_exception_handler
from src.core.logging_middleware import RequestTracingMiddleware
from src.database.connection import create_db_and_tables
from src.database.connection import create_db_and_tables, engine
from src.services.rag.chroma_service import ChromaService

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── CrewAI storage isolation ──────────────────────────────────────────────────
def _prepare_crewai_storage() -> None:
    os.environ.setdefault("CREWAI_STORAGE_DIR", "talentforge_local")
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
    storage_root = Path.cwd() / "data" / ".crewai_storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    appdirs.user_data_dir = lambda appname=None, appauthor=None, version=None, roaming=False: str(
        storage_root / (appauthor or "CrewAI") / (appname or "talentforge_local")
    )


_prepare_crewai_storage()


# ── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TalentForge AI...")
    create_db_and_tables()
    yield
    logger.info("Shutting down.")


# ── Application factory ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(RequestTracingMiddleware)
# GZip compression for all responses ≥ 512 bytes (JS, JSON, HTML)
app.add_middleware(GZipMiddleware, minimum_size=512)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception Handlers ────────────────────────────────────────────────────────
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


# ── Health & Readiness Probes (Cloud / Kubernetes) ───────────────────────────
@app.get("/health", tags=["system"])
@app.get("/api/health", include_in_schema=False)
def health_check():
    """Liveness probe: fast non-blocking response confirming process is alive."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "talentforge-ai",
        "version": "2.0.0",
    }


@app.get("/ready", tags=["system"])
@app.get("/api/ready", tags=["system"])
def readiness_check(response: Response):
    """Readiness probe: verifies all dependent subsystems (Database, Vector DB, AI Gateway)."""
    components = {
        "database": "unknown",
        "vector_store": "unknown",
        "llm_gateway": "ready" if getattr(settings, "GROQ_API_KEY", None) else "fallback_mode",
    }
    healthy = True

    # 1. Database Ping
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        components["database"] = "connected"
    except Exception as exc:
        logger.error("Readiness check DB error: %s", exc)
        components["database"] = f"error: {exc!s}"
        healthy = False

    # 2. ChromaDB Vector Store Ping
    try:
        chroma = ChromaService()
        chroma.client.heartbeat()
        components["vector_store"] = "connected"
    except Exception as exc:
        logger.warning("Readiness check ChromaDB warning: %s", exc)
        components["vector_store"] = f"warning: {exc!s}"

    status_str = "ready" if healthy else "degraded"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": status_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }


# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(candidates.router)
app.include_router(employees.router)
app.include_router(dashboard.router)
app.include_router(interview.router)
app.include_router(mock_interview.router)
app.include_router(departments.router)
app.include_router(designations.router)
app.include_router(lifecycle.router)
app.include_router(tickets.router)
app.include_router(salary.router)
app.include_router(promotions.router)
app.include_router(notifications.router)
app.include_router(onboarding.router)
app.include_router(training.router)
app.include_router(profile.router)
app.include_router(rag.router)
app.include_router(admin.router)




# ── Static Frontend (must be LAST) ────────────────────────────────────────────
class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not (
                path.startswith("api")
                or path.startswith("docs")
                or path.startswith("health")
                or path.startswith("ready")
            ):
                return await super().get_response("index.html", scope)
            raise exc


os.makedirs("static", exist_ok=True)
app.mount("/", SPAStaticFiles(directory="static", html=True), name="static")
