"""
src/core/logging_middleware.py
Unified Request Context, Tracing, and Structured Logging Middleware for TalentForge AI.
"""
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("talentforge.audit")

EVIDENCE_LOGS_DIR = Path("evidence/logs")
AUDIT_LOG_FILE = EVIDENCE_LOGS_DIR / "audit_trace.jsonl"


def log_agent_execution(
    request_id: str,
    user_id: int | str | None,
    agent: str,
    tool: str | list[str] | None = None,
    latency_ms: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    status: str = "SUCCESS",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Standardized logger for Agent and Tool executions.
    Emits structured JSON to both the logger and evidence/logs/audit_trace.jsonl.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "user_id": user_id,
        "agent": agent,
        "tool": tool,
        "latency_ms": round(latency_ms, 2),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "status": status,
        "details": details or {},
    }
    
    # Ensure directory exists
    try:
        EVIDENCE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("Failed to write to audit log file: %s", exc)

    logger.info("AUDIT_TRACE: %s", json.dumps(entry))
    return entry


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that assigns a UUID X-Request-ID to every incoming request
    and tracks HTTP latency.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{latency_ms:.2f}"

        # Only audit relevant API endpoints to avoid bloating logs
        if request.url.path.startswith("/api/"):
            log_agent_execution(
                request_id=request_id,
                user_id=getattr(request.state, "user_id", None),
                agent="HttpGateway",
                tool=f"{request.method} {request.url.path}",
                latency_ms=latency_ms,
                status=f"HTTP_{response.status_code}",
                details={"status_code": response.status_code},
            )

        return response

