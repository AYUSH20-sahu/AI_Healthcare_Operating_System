# ==============================================================================
# Production Multi-Stage Dockerfile for AI-HOS Backend (FastAPI + Gunicorn)
# Stage 1: Build virtual environment with C/C++ compilation headers
# Stage 2: Minimal hardened runner image with non-root security isolation
# ==============================================================================

# ── Stage 1: Build Dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compilation and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install production Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Minimal Hardened Production Runner ────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

# Install runtime shared libraries and curl for health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create dedicated non-root application user and group (UID/GID 10001)
RUN groupadd --system --gid 10001 aihos && \
    useradd --system --uid 10001 --gid aihos --create-home --home-dir /app aihos

# Create local secure vaults for audio notes and encrypted recordings
RUN mkdir -p /app/storage/voice_notes /app/storage/telehealth_recordings && \
    chown -R aihos:aihos /app

# Copy application source code with secure non-root ownership
COPY --chown=aihos:aihos . .

# Drop privileges to non-root user
USER aihos

EXPOSE 8000

# Health check probe against root healthcheck endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Launch institutional production server via Gunicorn + Uvicorn workers
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "app.main:app"]
