# Story — Target Agent Containerization (Multi-stage Dockerfile)

**ID:** story-2.4-target-cloud-run-deploy
**Epic:** Epic 2 — Target agent (the victim)
**Depends on:** story-2.3-target-phoenix-instrumentation
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** Cloud Run deploy pipeline (the workflows from Epic 1)
**I want to** build a slim, non-root, multi-stage Docker image of the target-agent service
**So that** the staging-deploy workflow from S1.6 can push `target-agent:${SHA}` to Artifact Registry and `gcloud run deploy target-agent --image=...` lands a working container — closing Epic 2 and unlocking Epic 3 (cross-framework adapter layer that talks to this deployed target via A2A)

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/target-agent/Dockerfile` — NEW — multi-stage build:
  - Stage 1 (`deps`): `python:3.12-slim`, install `uv`, copy `pyproject.toml` + `uv.lock`, run `uv sync --frozen --no-install-project --no-dev` to install deps into a virtualenv at `/opt/venv`.
  - Stage 2 (`build`): `python:3.12-slim`, copy venv from `deps`, copy `src/` + `pyproject.toml`, run `uv sync --frozen --no-dev` to install the project itself.
  - Stage 3 (`runtime`): `python:3.12-slim`, create non-root user `appuser` (uid 10001, gid 10001), copy `/opt/venv` + `/app` from `build`, set `WORKDIR /app`, `USER appuser`, `ENV PATH="/opt/venv/bin:$PATH"`, `EXPOSE 8001`, `CMD ["uv", "run", "target-agent"]`.
  - ~90 lines.
- `apps/target-agent/.dockerignore` — NEW — excludes `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.ty_cache/`, `.venv/`, `tests/`, `*.md`, `.env*`, `htmlcov/`, `.coverage*`, `dist/`, `build/`, `*.egg-info/`, `.DS_Store`, `.git/`. ~40 lines.
- `apps/target-agent/README.md` — UPDATE — add "Container build" section: `docker build -t target-agent:dev apps/target-agent`, `docker run --rm -p 8001:8001 -e PHOENIX_API_KEY=... target-agent:dev`.
- `apps/target-agent/tests/integration/test_dockerfile_build.py` — NEW — pytest test marked `@pytest.mark.integration @pytest.mark.slow` that:
  1. Skips if `docker` not in `PATH` (use `shutil.which("docker")`).
  2. Runs `docker build -t target-agent:test .` from `apps/target-agent/`.
  3. Captures exit code, asserts it equals 0.
  4. Runs `docker image inspect --format='{{.Size}}' target-agent:test` and asserts size < 500 * 1024 * 1024 (500 MB).
  5. Optional: runs `docker run --rm target-agent:test python -c "import target_agent; print('OK')"` to smoke the image.
  ~120 lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

NOTE: actual Cloud Run deploy (i.e. `gcloud run deploy target-agent --image=...`) happens via the `.github/workflows/staging-deploy.yaml` workflow from Story 1.6 — this story does NOT call gcloud. It only verifies the image builds and meets size + non-root constraints.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/target-agent/Dockerfile exists with multi-stage build
When  `docker build -t target-agent:test apps/target-agent` runs
Then  the exit code is 0

Given the built image exists locally
When  `docker image inspect --format='{{.Size}}' target-agent:test` runs
Then  the size (in bytes) is < 500_000_000 (500 MB)

Given the built image exists locally
When  `docker run --rm target-agent:test id -u` runs
Then  the printed uid is "10001" (non-root user enforced)

Given the built image exists locally
When  `docker run --rm target-agent:test sh -c 'echo $PATH'` runs
Then  the printed PATH starts with "/opt/venv/bin:"

Given the built image exists locally
When  `docker run --rm target-agent:test python -c "import target_agent; print(target_agent.__name__)"` runs
Then  stdout contains "target_agent" and exit code is 0

Given apps/target-agent/Dockerfile uses CMD ["uv", "run", "target-agent"]
When  `grep -E '^CMD \\["uv", "run", "target-agent"\\]' apps/target-agent/Dockerfile` runs
Then  exactly one match appears

Given apps/target-agent/Dockerfile creates non-root user appuser
When  `grep -E 'USER appuser' apps/target-agent/Dockerfile` runs
Then  at least one match appears in the final (runtime) stage

Given apps/target-agent/.dockerignore exists
When  the file is read
Then  it contains entries for ".git", ".venv", "tests", "__pycache__"

Given pytest runs the dockerfile-build integration test
When  `cd apps/target-agent && uv run pytest tests/integration/test_dockerfile_build.py -v -m "integration and slow"` runs
Then  the test passes (assuming docker daemon available)
And   in environments without docker, it skips (not fails)

Given the 400-line guard runs
When  `python3 scripts/check_max_lines.py --strict apps/target-agent/` runs
Then  exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# 1) Dockerfile + .dockerignore exist
test -f apps/target-agent/Dockerfile && test -f apps/target-agent/.dockerignore && echo "OK"
# Must print OK

# 2) Build the image (this is the load-bearing verification step)
docker build -t target-agent:test apps/target-agent
# Must exit 0

# 3) Image size < 500 MB
SIZE=$(docker image inspect --format='{{.Size}}' target-agent:test)
echo "Image size: $SIZE bytes ($((SIZE / 1024 / 1024)) MB)"
test "$SIZE" -lt 500000000 && echo "OK size" || (echo "FAIL: image too large"; exit 1)

# 4) Non-root user
UID_OUT=$(docker run --rm target-agent:test id -u)
echo "Runtime uid: $UID_OUT"
test "$UID_OUT" = "10001" && echo "OK non-root" || (echo "FAIL: expected uid 10001"; exit 1)

# 5) PATH precedence
PATH_OUT=$(docker run --rm target-agent:test sh -c 'echo $PATH')
echo "PATH: $PATH_OUT"
echo "$PATH_OUT" | grep -q "^/opt/venv/bin:" && echo "OK PATH" || (echo "FAIL: venv not first in PATH"; exit 1)

# 6) Module import smoke
docker run --rm target-agent:test python -c "import target_agent; print(target_agent.__name__)"
# Must print "target_agent" with exit 0

# 7) CMD shape
grep -E '^CMD \["uv", "run", "target-agent"\]' apps/target-agent/Dockerfile
# Must output exactly one match

# 8) USER directive
grep -E 'USER appuser' apps/target-agent/Dockerfile
# Must output ≥ 1 match (final stage)

# 9) .dockerignore key entries
grep -E '^\.git$|^\.venv$|^tests$|^__pycache__$' apps/target-agent/.dockerignore
# Must output ≥ 4 matches

# 10) Integration test (slow — runs docker build a second time, can be expensive)
if command -v docker >/dev/null 2>&1; then
  cd apps/target-agent && uv run pytest tests/integration/test_dockerfile_build.py -v -m "integration and slow" 2>&1 | tee /tmp/target-docker-test.log
  grep -E "PASSED" /tmp/target-docker-test.log | wc -l
  # Must output ≥ 1
fi

# 11) §14 + 400-line + lint
git diff main...HEAD -- 'apps/target-agent/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing
python3 scripts/check_max_lines.py --strict apps/target-agent/
# Must exit 0

# 12) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Cloud Run deploy is OUT OF SCOPE.** This story only produces a buildable, runnable Docker image. The actual `gcloud run deploy target-agent --image=$IMAGE_URL ...` invocation lives in `.github/workflows/staging-deploy.yaml` from Story 1.6 — it discovers `apps/target-agent/Dockerfile` and ships the image. Do NOT add any `gcloud` calls in this story.
- **Reference Dockerfile shape (paste-ready starting point):**
  ```dockerfile
  # syntax=docker/dockerfile:1.7

  # ---- Stage 1: deps ----
  FROM python:3.12-slim AS deps
  ENV UV_LINK_MODE=copy \
      UV_COMPILE_BYTECODE=1 \
      UV_PYTHON_DOWNLOADS=never \
      PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1
  RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
      && rm -rf /var/lib/apt/lists/*
  COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /usr/local/bin/
  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen --no-install-project --no-dev

  # ---- Stage 2: build ----
  FROM python:3.12-slim AS build
  ENV UV_LINK_MODE=copy \
      UV_COMPILE_BYTECODE=1 \
      UV_PYTHON_DOWNLOADS=never
  COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /usr/local/bin/
  WORKDIR /app
  COPY --from=deps /app/.venv /app/.venv
  COPY pyproject.toml uv.lock ./
  COPY src/ ./src/
  RUN uv sync --frozen --no-dev

  # ---- Stage 3: runtime ----
  FROM python:3.12-slim AS runtime
  ENV PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1 \
      PATH="/opt/venv/bin:/usr/local/bin:$PATH"
  RUN groupadd --gid 10001 appuser \
      && useradd --uid 10001 --gid 10001 --no-create-home --shell /bin/sh appuser \
      && mkdir -p /app \
      && chown -R appuser:appuser /app
  COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /usr/local/bin/
  COPY --from=build --chown=appuser:appuser /app/.venv /opt/venv
  COPY --from=build --chown=appuser:appuser /app/src /app/src
  COPY --from=build --chown=appuser:appuser /app/pyproject.toml /app/pyproject.toml
  COPY --from=build --chown=appuser:appuser /app/uv.lock /app/uv.lock
  WORKDIR /app
  USER appuser
  EXPOSE 8001
  CMD ["uv", "run", "target-agent"]
  ```
  Adjust the uv version pin to match the workspace's `uv` version from S1.1.
- **Why `--no-dev`.** The runtime image must not include pytest, ruff, ty, or test fixtures. Saves ~80 MB and tightens the supply chain.
- **Why `uv sync --frozen`.** Reproducible builds. `--frozen` fails if `uv.lock` doesn't match `pyproject.toml`, catching dependency drift at build time rather than at runtime.
- **Why `UV_COMPILE_BYTECODE=1`.** Precompiles `.py` → `.pyc` during install. Adds ~5 seconds to build, saves ~200ms from every Cloud Run cold start.
- **Why `UV_PYTHON_DOWNLOADS=never`.** Forces uv to use the system Python from the base image; prevents uv from downloading a second interpreter copy.
- **Non-root user (uid 10001).** Cloud Run runs containers as the user specified in the image. Using uid 10001 (out of common-range to avoid colliding with host users in the rare case of bind-mounts) is the 2026 best practice. The `--chown=appuser:appuser` on every COPY ensures the venv + source are owned by the runtime user.
- **`CMD ["uv", "run", "target-agent"]`.** Exec form (JSON array) — important for proper signal handling on Cloud Run (SIGTERM during scale-down). The shell form `CMD uv run target-agent` would not forward signals to the python process.
- **`uv run target-agent`.** Invokes the `[project.scripts] target-agent = "target_agent.server:main"` entry from S2.2. `uv run` ensures the venv is activated; equivalent to `/opt/venv/bin/target-agent` but more portable.
- **`EXPOSE 8001`.** Documentary only; Cloud Run reads the `PORT` env var (default 8080) and ignores `EXPOSE`. The container must respect `$PORT` (already handled by S2.2's `main()` reading `os.environ.get("PORT", "8001")`).
- **`uv.lock` must exist before this story runs.** S2.1 + S2.2 + S2.3 all run `uv sync` which generates/updates `uv.lock`. Verify `apps/target-agent/uv.lock` is committed before opening this story's PR. If absent, the `--frozen` flag will fail the build.
- **Image size budget.** Target ≤ 400 MB. `python:3.12-slim` is ~150 MB. Phoenix + OpenInference + ADK + Google Cloud SDKs add ~200-250 MB combined. The 500 MB cap in the BDD criterion has a 100 MB buffer — if the build exceeds 450 MB, investigate which dep pulled in unexpected bloat (`docker history target-agent:test --no-trunc`).
- **`.dockerignore` is load-bearing.** Without it, `docker build` will COPY the entire `.venv/`, `tests/`, `.git/`, and `__pycache__/` directories into the build context, slowing builds and risking secret leakage from `.env` files. The provided list covers the common cases; add project-specific entries as needed.
- **Integration test pattern.** The test must:
  ```python
  import shutil
  import subprocess
  from pathlib import Path
  import pytest

  pytestmark = [pytest.mark.integration, pytest.mark.slow]

  @pytest.fixture(scope="module")
  def docker_cli() -> str:
      cli = shutil.which("docker")
      if cli is None:
          pytest.skip("docker not in PATH")
      return cli

  def test_dockerfile_builds(docker_cli: str, tmp_path: Path) -> None:
      app_dir = Path(__file__).resolve().parents[2]  # apps/target-agent/
      result = subprocess.run(
          [docker_cli, "build", "-t", "target-agent:pytest", "."],
          cwd=app_dir, capture_output=True, text=True, timeout=600,
      )
      assert result.returncode == 0, f"docker build failed:\n{result.stderr}"

  def test_image_size_under_500mb(docker_cli: str) -> None:
      result = subprocess.run(
          [docker_cli, "image", "inspect", "--format={{.Size}}", "target-agent:pytest"],
          capture_output=True, text=True, check=True,
      )
      size_bytes = int(result.stdout.strip())
      assert size_bytes < 500 * 1024 * 1024, f"image size {size_bytes} bytes exceeds 500MB"
  ```
  Mark `slow` because `docker build` can take 60-180 seconds on a cold cache.
- **Skip behavior in CI without docker.** PR CI runs on `ubuntu-latest` which has docker pre-installed, but local dev machines may not. The `pytest.skip("docker not in PATH")` path keeps unit-only test runs green for contributors without docker.
- **No Cloud Run deploy verification in this story.** The next story to verify a real deploy is the staging-deploy workflow (which is already covered by S1.6's BDD). When Epic 3 or Epic 4 stories start calling the deployed target, they'll discover any runtime issues — that's the right place to catch them, not here.
- **400-line vigilance.** `Dockerfile` ~90 lines, `.dockerignore` ~40 lines, `test_dockerfile_build.py` ~120 lines — all well under 400. The 400-line guard is configured for `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.md` per ADR-010; Dockerfile and .dockerignore are not in scope but stay short anyway.
- **Cross-reference docs:** `architecture.md` ADR-003 (3 Cloud Run services), ADR-008 ("build once, promote everywhere"). `coding-standards.md` `Definition of Done`. `research/.../best-practices/01-python-project-layout.md` §3 (canonical Python project layout for Cloud Run). `research/.../architecture/03-multi-agent-patterns.md` §9.A Dockerfile sample (note our multi-stage variant supersedes that single-stage example).
