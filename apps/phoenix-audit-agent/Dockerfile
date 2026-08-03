# syntax=docker/dockerfile:1.7
#
# Multi-stage Docker image for the phoenix-audit-agent service (Phoenix Audit orchestrator).
#
# IMPORTANT — build context: this is a uv workspace project. The lockfile
# (`uv.lock`) lives at the workspace root, not in apps/phoenix-audit-agent/.
# So the build context MUST be the workspace root:
#
#     docker build -t phoenix-audit-agent:dev -f apps/phoenix-audit-agent/Dockerfile .
#
# Cloud Run reads $PORT (default 8080) and ignores EXPOSE entirely; the CMD
# respects $PORT via main.py's run_uvicorn (see _PORT/_HOST env resolution).
#
# Architecture: deps -> build -> runtime (slim, non-root, signal-safe).

# Pin uv as a named stage so downstream COPY --from=uv-source references work
# under all BuildKit parsers (the inline `COPY --from=img:${ARG}` form was
# silently broken by a buildx parse regression).
FROM ghcr.io/astral-sh/uv:0.12.0 AS uv-source

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
# to resolve the workspace graph, even though we only install phoenix-audit-agent.
# The .dockerignore prevents target-agent's source from being COPYed in.
COPY pyproject.toml uv.lock ./
COPY apps/phoenix-audit-agent/pyproject.toml apps/phoenix-audit-agent/
COPY apps/target-agent/pyproject.toml apps/target-agent/

# --frozen: fail loud if uv.lock disagrees with pyproject.toml (reproducible builds, ADR-008).
# --no-install-project: just resolve dependencies; project source comes next stage.
# --no-dev: skip pytest, ruff, ty — runtime image stays slim.
# --package phoenix-audit-agent: select the workspace member to install for.
RUN uv sync --frozen --no-install-project --no-dev --package phoenix-audit-agent

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
COPY apps/phoenix-audit-agent/pyproject.toml apps/phoenix-audit-agent/
COPY apps/target-agent/pyproject.toml apps/target-agent/
COPY apps/phoenix-audit-agent/src/ apps/phoenix-audit-agent/src/
COPY apps/phoenix-audit-agent/README.md apps/phoenix-audit-agent/README.md

# --no-editable: install phoenix-audit-agent as a regular wheel rather than a .pth
# pointing at /workspace/apps/phoenix-audit-agent/src — the runtime stage relocates
# the venv to /opt/venv and drops the /workspace layout.
RUN uv sync --frozen --no-dev --package phoenix-audit-agent --no-editable

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

# ca-certificates for outbound TLS (Phoenix Cloud, Gemini API). Pango trio
# for WeasyPrint's PDF renderer (the signed audit report, story-6.7) —
# ~19 MB measured on python:3.12-slim; cairo is NOT needed since WeasyPrint 53.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-source /uv /uvx /usr/local/bin/

COPY --from=build --chown=appuser:appuser /workspace/.venv /opt/venv
# Rewrite console-script shebangs from the build-stage path to the runtime
# path. uv bakes /workspace/.venv/bin/python3 into every entry-point at
# install time; without this fix the kernel raises ENOENT on Cloud Run.
RUN find /opt/venv/bin -maxdepth 1 -type f -executable -print0 \
    | xargs -0 sed -i '1s|#!/workspace/.venv|#!/opt/venv|'

# Import smoke — a dependency missing from THIS image (dev env has extras the
# image doesn't) must fail the BUILD, not crashloop the Cloud Run revision.
# story-9.10 root cause: EmailStr needed email-validator; every staging deploy
# since S9.3 silently parked as an unpromoted candidate while traffic stayed
# pinned to a 4-day-old revision.
RUN GEMINI_API_KEY=docker-import-smoke GCS_PROBE_AT_STARTUP=false ENVIRONMENT=dev \
    python -c "import phoenix_audit_agent.main"

COPY --from=build --chown=appuser:appuser /workspace/apps/phoenix-audit-agent/src /app/src
COPY --from=build --chown=appuser:appuser /workspace/apps/phoenix-audit-agent/pyproject.toml /app/pyproject.toml

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
# Invoke the console script directly; `uv run` re-resolves the workspace at
# startup which fails because the runtime image omits pyproject.toml / README.
# The venv is already on PATH via /opt/venv/bin (see ENV PATH above).
CMD ["phoenix-audit-agent"]
