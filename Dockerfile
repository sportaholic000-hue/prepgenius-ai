# ===========================================================================
# PrepGenius AI — Render-Optimized Dockerfile
# ===========================================================================
# Secure, minimal production image for Render free-tier deployment.
# Uses non-root user, multi-stage-friendly structure, and $PORT passthrough.
# ===========================================================================

FROM python:3.11-slim AS base

# ------- System config -------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# ------- Install OS dependencies (if any needed later) -------
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ------- Install Python dependencies (layer caching) -------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------- Copy application code -------
COPY . .

# ------- Create non-root user for security -------
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

# ------- Expose port -------
EXPOSE 8000

# ------- Health check for container orchestrators -------
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# ------- Start uvicorn — uses $PORT env var from Render -------
# Shell form so $PORT is expanded at runtime
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT} --workers 1 --log-level info
