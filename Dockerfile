# ── Stage 1: Dependency Builder ───────────────────────────────────────────────
FROM python:3.10-slim AS builder
# ==============================================================================
# TalentForge AI — Production Multi-Stage Dockerfile
# Stage 1: Frontend SPA Builder (React 19 + Vite)
# Stage 2: Python Backend Dependency Builder
# Stage 3: Secure Non-Root Runtime Image
# ==============================================================================

# ── Stage 1: Build React 19 Frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Build Python Dependencies ────────────────────────────────────────
FROM python:3.10-slim AS python-builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
# ── Stage 3: Production Runtime ───────────────────────────────────────────────
FROM python:3.10-slim AS runner
WORKDIR /app

# ── Stage 2: Production Runtime ───────────────────────────────────────────────
FROM python:3.10-slim
# Install runtime system libraries (libpq, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN adduser --disabled-password --gecos '' talentforge_user
# Create unprivileged application user
RUN useradd -m -u 1000 appuser

WORKDIR /app
# Copy installed Python packages from builder
COPY --from=python-builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Copy backend application source code
COPY src/ ./src/
COPY agents/ ./agents/
COPY tasks/ ./tasks/
COPY data/ ./data/

# Copy only what's needed (no venv, no .env, no test files)
COPY ./src ./src
COPY ./agents ./agents
COPY ./tasks ./tasks
COPY ./utils ./utils
COPY ./scripts ./scripts
COPY ./crew.py ./crew.py
COPY ./static ./static
# Copy built frontend static assets from Stage 1
COPY --from=frontend-builder /app/static ./static/

# Create writable data directory for resume uploads & crewai storage
RUN mkdir -p /app/data && chown -R talentforge_user:talentforge_user /app
# Configure permissions for non-root user
RUN mkdir -p /app/evidence/logs /app/data/.crewai_storage && \
    chown -R appuser:appuser /app

USER talentforge_user

USER appuser
EXPOSE 8000

# Production: respect the platform-provided PORT, defaulting to 8000 locally.
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
# Container liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
