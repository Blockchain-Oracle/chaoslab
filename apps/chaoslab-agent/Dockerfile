# syntax=docker/dockerfile:1.7
#
# Multi-stage Docker image for the chaoslab-agent service (Phoenix Audit orchestrator).
#
# IMPORTANT — build context: this is a uv workspace project. The lockfile
# (`uv.lock`) lives at the workspace root, not in apps/chaoslab-agent/.
# So the build context MUST be the workspace root:
#
#     docker build -t chaoslab-agent:dev -f apps/chaoslab-agent/Dockerfile .
#
# Cloud Run reads $PORT (default 8080) and ignores EXPOSE entirely; the CMD
# respects $PORT via main.py's run_uvicorn (see _PORT/_HOST env resolution).
#
# Architecture: deps -> build -> runtime (slim, non-root, signal-safe).

# Pin uv as a named stage so downstream COPY --from=uv-source references work
# under all BuildKit parsers (the inline `COPY --from=img:${ARG}` form was
# silently broken by a buildx parse regression).
FROM ghcr.io/astral-sh/uv:0.11.18 AS uv-source

# -----------------------------------------------------------------------------
# Stage 1: deps — install workspace dependencies into a virtualenv
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS deps

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ca-certificates: httpx + grpcio TLS to Phoenix / Gemini APIs.
# curl: ad-hoc health debugging (HEALTHCHECK uses Python httpx instead).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-source /uv /uvx /usr/local/bin/

WORKDIR /workspace

# Workspace metadata. Bringing in BOTH app pyproject.tomls is necessary for uv
# to resolve the workspace graph, even though we only install chaoslab-agent.
# The .dockerignore prevents target-agent's source from being COPYed in.
COPY pyproject.toml uv.lock ./
COPY apps/chaoslab-agent/pyproject.toml apps/chaoslab-agent/
COPY apps/target-agent/pyproject.toml apps/target-agent/

# --frozen: fail loud if uv.lock disagrees with pyproject.toml (reproducible builds, ADR-008).
# --no-install-project: just resolve dependencies; project source comes next stage.
# --no-dev: skip pytest, ruff, ty — runtime image stays slim.
# --package chaoslab-agent: select the workspace member to install for.
RUN uv sync --frozen --no-install-project --no-dev --package chaoslab-agent

# -----------------------------------------------------------------------------
# Stage 2: build — copy project source + install the project itself
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS build

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY --from=uv-source /uv /uvx /usr/local/bin/

WORKDIR /workspace

COPY --from=deps /workspace/.venv /workspace/.venv
COPY pyproject.toml uv.lock ./
COPY apps/chaoslab-agent/pyproject.toml apps/chaoslab-agent/
COPY apps/target-agent/pyproject.toml apps/target-agent/
COPY apps/chaoslab-agent/src/ apps/chaoslab-agent/src/
COPY apps/chaoslab-agent/README.md apps/chaoslab-agent/README.md

# --no-editable: install chaoslab-agent as a regular wheel rather than a .pth
# pointing at /workspace/apps/chaoslab-agent/src — the runtime stage relocates
# the venv to /opt/venv and drops the /workspace layout.
RUN uv sync --frozen --no-dev --package chaoslab-agent --no-editable

# -----------------------------------------------------------------------------
# Stage 3: runtime — slim, non-root, signal-safe
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/usr/local/bin:/usr/bin:/bin"

# Non-root user. uid 10001 is out of the common-collision range (uids <1000 are
# system; 1000-9999 commonly used for host users; >=10000 leaves a clean buffer
# above typical host-user collisions in bind-mount scenarios). Direct /etc/passwd
# write — python:3.12-slim lacks groupadd/useradd by default (they're in the
# `passwd` package we don't want to pull in just for one user).
RUN echo 'appuser:x:10001:10001::/app:/bin/sh' >> /etc/passwd \
    && echo 'appuser:x:10001:' >> /etc/group \
    && mkdir -p /app \
    && chown 10001:10001 /app

# ca-certificates for outbound TLS (Phoenix Cloud, Gemini API). Without these
# the runtime stage cannot verify https.
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-source /uv /uvx /usr/local/bin/

COPY --from=build --chown=appuser:appuser /workspace/.venv /opt/venv
COPY --from=build --chown=appuser:appuser /workspace/apps/chaoslab-agent/src /app/src
COPY --from=build --chown=appuser:appuser /workspace/apps/chaoslab-agent/pyproject.toml /app/pyproject.toml

WORKDIR /app
USER appuser

# EXPOSE 8080 documents the FastAPI port — Cloud Run rebinds via $PORT regardless.
EXPOSE 8080

# Local `docker run` health probe only. Cloud Run uses its own configured
# liveness check via the service's `--liveness-probe=httpGet.path=/health,...`
# args (or the equivalent YAML); the HEALTHCHECK here is debugging convenience.
# Writes the underlying exception to stderr on failure so `docker logs` /
# `docker inspect` show WHY the probe failed (httpx.ConnectError vs.
# HTTPStatusError vs. ImportError) instead of an opaque exit 1.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, httpx;\nimport traceback\ntry:\n    httpx.get('http://localhost:8080/health', timeout=2).raise_for_status()\nexcept Exception as e:\n    sys.stderr.write(f'healthcheck failed: {e!r}\\n')\n    traceback.print_exc()\n    sys.exit(1)"]

# Exec form (JSON array) — important for SIGTERM forwarding on Cloud Run scale-down.
# `uv run` activates the venv; `chaoslab-agent` is the console script
# resolving to chaoslab_agent.main:run_uvicorn (reads $PORT/$HOST env vars).
CMD ["uv", "run", "chaoslab-agent"]
