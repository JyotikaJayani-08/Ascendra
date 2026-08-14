# ============================================================
# Ascendra Backend — Production Dockerfile
# Multi-stage build for smaller image, non-root user for security.
# ============================================================

# --- Stage 1: Build dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /app

# System dependencies required by asyncpg (C extension), pymupdf, and argon2-cffi
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Production runtime ---
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install only runtime system libraries (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder stage
COPY --from=builder /install /usr/local

# Create non-root user for security (Render runs containers as root by default,
# but this is best practice for portability)
RUN groupadd -r ascendra && useradd -r -g ascendra -d /app -s /sbin/nologin ascendra

# Copy application code
COPY . .

# Create logs directory with correct ownership
RUN mkdir -p /app/logs && chown -R ascendra:ascendra /app

# Switch to non-root user
USER ascendra

# Render injects $PORT at runtime. Default to 8000 for local Docker usage.
ENV PORT=8000
EXPOSE ${PORT}

# Health check — Render uses this + /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use shell form so $PORT is expanded at runtime by the shell
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --timeout-keep-alive 120
