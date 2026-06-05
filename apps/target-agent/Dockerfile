# syntax=docker/dockerfile:1.7
#
# Multi-stage Docker image for the target-agent service.
#
# IMPORTANT — build context: this is a uv workspace project. The lockfile
# (`uv.lock`) lives at the workspace root, not in apps/target-agent/.
# So the build context MUST be the workspace root:
#
#     docker build -t target-agent:dev -f apps/target-agent/Dockerfile .
#
# Building from inside apps/target-agent (the story spec's original
# example) will fail with "uv.lock not found". The Cloud Run deploy
# workflow (S1.6) passes the right context automatically.
#
# Architecture: deps → build → runtime (slim, non-root, signal-safe).

ARG UV_VERSION=0.11.18

# -----------------------------------------------------------------------------
# Stage 1: deps — install workspace dependencies into a virtualenv
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS deps

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ca-certificates needed for httpx/grpcio TLS to google APIs at runtime;
# curl handy for ad-hoc health checks. Both fit in the slim image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /usr/local/bin/

WORKDIR /workspace

# Workspace metadata. Bringing in chaoslab-agent's pyproject is necessary
# for uv to resolve the workspace graph, even though we only install
# target-agent. The .dockerignore prevents that app's source from coming.
COPY pyproject.toml uv.lock ./
COPY apps/target-agent/pyproject.toml apps/target-agent/
COPY apps/chaoslab-agent/pyproject.toml apps/chaoslab-agent/

# --frozen: fail loud if uv.lock disagrees with pyproject.toml.
# --no-install-project: just resolve dependencies; project source comes next stage.
# --no-dev: skip pytest, ruff, ty — runtime image stays slim.
# --package target-agent: select the workspace member to install for.
RUN uv sync --frozen --no-install-project --no-dev --package target-agent

# -----------------------------------------------------------------------------
# Stage 2: build — copy project source + install the project itself
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS build

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /usr/local/bin/

WORKDIR /workspace

COPY --from=deps /workspace/.venv /workspace/.venv
COPY pyproject.toml uv.lock ./
COPY apps/target-agent/pyproject.toml apps/target-agent/
COPY apps/chaoslab-agent/pyproject.toml apps/chaoslab-agent/
COPY apps/target-agent/src/ apps/target-agent/src/
COPY apps/target-agent/README.md apps/target-agent/README.md

# --no-editable: install target-agent as a regular wheel into site-packages
# instead of a .pth pointing at /workspace/apps/target-agent/src. The
# runtime stage relocates the venv to /opt/venv and drops the /workspace
# layout, which would break editable install paths.
RUN uv sync --frozen --no-dev --package target-agent --no-editable

# -----------------------------------------------------------------------------
# Stage 3: runtime — slim, non-root, signal-safe
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/usr/local/bin:/usr/bin:/bin"

# Non-root user. uid 10001 is out of the common-collision range; matches the
# 2026 Cloud Run best-practice for containers that might bind-mount into hosts.
# Direct /etc/passwd write — python:3.12-slim lacks groupadd/useradd by
# default (they're in the `passwd` package which we don't want to pull in
# just for one user). This single-line pattern works in any minimal base.
RUN echo 'appuser:x:10001:10001::/app:/bin/sh' >> /etc/passwd \
    && echo 'appuser:x:10001:' >> /etc/group \
    && mkdir -p /app \
    && chown 10001:10001 /app

COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /usr/local/bin/

# Copy the venv to a stable /opt/venv path (independent of WORKDIR).
COPY --from=build --chown=appuser:appuser /workspace/.venv /opt/venv
COPY --from=build --chown=appuser:appuser /workspace/apps/target-agent/src /app/src
COPY --from=build --chown=appuser:appuser /workspace/apps/target-agent/pyproject.toml /app/pyproject.toml

WORKDIR /app
USER appuser

# Cloud Run reads $PORT (default 8080) and ignores EXPOSE. The CMD respects
# $PORT via server.py's main(). EXPOSE is documentary only.
EXPOSE 8001

# Exec form (JSON array) — important for SIGTERM forwarding on Cloud Run scale-down.
# Shell form would not forward signals to the Python process.
# `uv run` activates the venv; equivalent to /opt/venv/bin/target-agent.
CMD ["uv", "run", "target-agent"]
