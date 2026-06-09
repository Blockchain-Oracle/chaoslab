"""Dockerfile integration tests — marked `@pytest.mark.slow`.

Skipped by default. Run via `uv run pytest -m slow` on a host with Docker
installed; CI invokes them on a labeled runner. The build is ~3-5 min on a
clean cache so these are NOT part of the standard PR loop.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3].parent
APP_DIR = REPO_ROOT / "apps" / "chaoslab-agent"
DOCKERFILE = APP_DIR / "Dockerfile"
IMAGE_TAG = "chaoslab-agent:test"
SMOKE_CONTAINER = "chaoslab-smoke-test"

# Image size cap. Multi-stage with --no-dev + non-root + slim base usually
# lands ~550-650MB; 800MB is the hard ceiling.
_MAX_IMAGE_MB = 800

# Non-root uid baked into the runtime stage. The /etc/passwd write in the
# Dockerfile sets `appuser` to uid 10001.
_RUNTIME_UID = 10001
_RUNTIME_USER = "appuser"

# Host port to publish the smoke-test container on (avoid clashing with any
# real local 8080 server).
_SMOKE_HOST_PORT = 18080


def _docker_available() -> bool:
    """True iff `docker` binary is on PATH AND a `docker info` succeeds."""
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="docker not available on PATH (skip Dockerfile integration suite)",
)


@pytest.fixture(scope="module")
def built_image() -> Iterator[str]:
    """Build the runtime image once per test module; tear down at the end."""
    assert DOCKERFILE.exists(), f"Dockerfile missing at {DOCKERFILE}"
    # Build context = workspace root (per Dockerfile header).
    result = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            str(DOCKERFILE),
            "-t",
            IMAGE_TAG,
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,  # 10 min cap
    )
    if result.returncode != 0:
        pytest.fail(
            f"docker build failed (rc={result.returncode}):\n"
            f"--- stdout ---\n{result.stdout[-2000:]}\n"
            f"--- stderr ---\n{result.stderr[-2000:]}"
        )
    yield IMAGE_TAG
    # Cleanup: remove the image so successive test runs aren't sharing cache state.
    subprocess.run(
        ["docker", "rmi", "-f", IMAGE_TAG],
        capture_output=True,
        check=False,
    )


@pytest.mark.slow
@pytest.mark.integration
def test_dockerfile_exists_and_targets_python_312_slim() -> None:
    """The Dockerfile lives at the expected path and starts from python:3.12-slim."""
    assert DOCKERFILE.exists()
    body = DOCKERFILE.read_text(encoding="utf-8")
    assert "python:3.12-slim" in body, "runtime base must be python:3.12-slim"
    assert body.lstrip().startswith("# syntax="), "BuildKit syntax directive required"


@pytest.mark.slow
@pytest.mark.integration
def test_image_builds_and_is_under_size_cap(built_image: str) -> None:
    """Built image size must be < 800MB (multi-stage + --no-dev + slim base)."""
    result = subprocess.run(
        ["docker", "images", "--format", "{{.Size}}", built_image],
        capture_output=True,
        text=True,
        check=True,
    )
    raw = result.stdout.strip()
    match = re.match(r"([\d.]+)(GB|MB|kB|B)", raw)
    assert match, f"could not parse image size: {raw!r}"
    value, unit = float(match.group(1)), match.group(2)
    mb = {
        "GB": value * 1024,
        "MB": value,
        "kB": value / 1024,
        "B": value / (1024 * 1024),
    }[unit]
    assert mb < _MAX_IMAGE_MB, (
        f"image is {mb:.1f}MB > {_MAX_IMAGE_MB}MB cap — check .dockerignore + --no-dev"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_image_runs_as_non_root_user(built_image: str) -> None:
    """The runtime container must NOT run as root — security gate."""
    result = subprocess.run(
        ["docker", "inspect", built_image, "--format", "{{.Config.User}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == _RUNTIME_USER, (
        f"Config.User must be {_RUNTIME_USER!r}, got {result.stdout.strip()!r}"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_image_exposes_port_8080(built_image: str) -> None:
    """The image must declare EXPOSE 8080 (matches Cloud Run + the run_uvicorn default)."""
    result = subprocess.run(
        [
            "docker",
            "inspect",
            built_image,
            "--format",
            "{{json .Config.ExposedPorts}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    exposed = json.loads(result.stdout.strip() or "{}")
    assert "8080/tcp" in exposed, f"missing 8080/tcp in {exposed!r}"


@pytest.mark.slow
@pytest.mark.integration
def test_container_health_endpoint_returns_ok(built_image: str) -> None:
    """End-to-end: container starts, /health responds 200 with status=ok within 15s."""
    # Tear down any prior leftover container.
    subprocess.run(["docker", "rm", "-f", SMOKE_CONTAINER], capture_output=True, check=False)
    run_result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            SMOKE_CONTAINER,
            "-p",
            f"{_SMOKE_HOST_PORT}:8080",
            "-e",
            "PHOENIX_API_KEY=dummy",
            "-e",
            "GEMINI_API_KEY=dummy",
            "-e",
            "JUDGE_LLM=gemini-3.5-flash",
            "-e",
            "SERVICE_VERSION=test",
            # Dockerfile smoke test has no real GCS bucket; disable the boot-time
            # probe (lifespan logs a WARNING naming this var). Production NEVER
            # sets this — round-3 silent-failure-hunter requires fail-loud at boot.
            "-e",
            "GCS_PROBE_AT_STARTUP=false",
            built_image,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if run_result.returncode != 0:
        pytest.fail(f"docker run failed: {run_result.stderr}")
    try:
        # Wait up to 15s for the server to bind. Retry every 1s.
        deadline = time.monotonic() + 15
        last_err: str = "(no attempt yet)"
        while time.monotonic() < deadline:
            try:
                resp = httpx.get(f"http://localhost:{_SMOKE_HOST_PORT}/health", timeout=2.0)
                if resp.status_code == 200:
                    payload = resp.json()
                    assert payload.get("status") == "ok", payload
                    assert payload.get("judge_llm") == "gemini-3.5-flash", payload
                    # SERVICE_VERSION threading: the env var must reach
                    # `Settings.service_version` and surface in /health JSON.
                    # Without this assertion, a refactor that drops the env
                    # var plumbing silently breaks the deployed-sha display.
                    assert payload.get("version") == "test", payload
                    return
                last_err = f"status={resp.status_code} body={resp.text[:200]}"
            except (httpx.HTTPError, ConnectionError) as e:
                last_err = repr(e)
            time.sleep(1)
        logs = subprocess.run(
            ["docker", "logs", SMOKE_CONTAINER],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        pytest.fail(
            f"container /health never returned 200 within 15s.\n"
            f"last error: {last_err}\n"
            f"--- container logs ---\n{logs[-2000:]}"
        )
    finally:
        subprocess.run(["docker", "rm", "-f", SMOKE_CONTAINER], capture_output=True, check=False)


@pytest.mark.slow
@pytest.mark.integration
def test_running_container_uid_is_10001(built_image: str) -> None:
    """`docker exec id -u` returns 10001 (the non-root chaoslab uid)."""
    subprocess.run(["docker", "rm", "-f", SMOKE_CONTAINER], capture_output=True, check=False)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            SMOKE_CONTAINER,
            "-p",
            f"{_SMOKE_HOST_PORT + 1}:8080",
            "-e",
            "PHOENIX_API_KEY=dummy",
            "-e",
            "GEMINI_API_KEY=dummy",
            built_image,
        ],
        capture_output=True,
        check=True,
    )
    try:
        # Poll Running=true (up to 5s) instead of a flat sleep. Guards against
        # `docker exec` hitting a container that's already exited (e.g.,
        # Settings validation crash); failure path dumps logs for diagnosis.
        deadline = time.monotonic() + 5
        running = False
        while time.monotonic() < deadline:
            inspect = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", SMOKE_CONTAINER],
                capture_output=True,
                text=True,
                check=False,
            )
            if inspect.returncode == 0 and inspect.stdout.strip() == "true":
                running = True
                break
            time.sleep(0.2)
        if not running:
            logs = subprocess.run(
                ["docker", "logs", SMOKE_CONTAINER],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            pytest.fail(
                f"container never reached Running=true within 5s.\n"
                f"--- container logs ---\n{logs[-2000:]}"
            )
        result = subprocess.run(
            ["docker", "exec", SMOKE_CONTAINER, "id", "-u"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == str(_RUNTIME_UID), (
            f"runtime uid must be {_RUNTIME_UID}, got {result.stdout.strip()!r}"
        )
    finally:
        subprocess.run(["docker", "rm", "-f", SMOKE_CONTAINER], capture_output=True, check=False)


# --- Static config gates (always run, no Docker required) -------------------


@pytest.mark.integration
def test_dockerignore_excludes_secrets_and_caches() -> None:
    """`.dockerignore` MUST exclude .env*, .venv/, tests/, __pycache__/, .git/.

    Parses line-by-line, strips comments + whitespace, then checks the
    resulting active-pattern set. Substring `in body` would be fooled by a
    commented-out entry (e.g. `# .env`).
    """
    ignore_file = APP_DIR / ".dockerignore"
    assert ignore_file.exists(), f"missing {ignore_file}"
    active_patterns: set[str] = set()
    for raw in ignore_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        active_patterns.add(line)
    for required in (".env", ".venv/", "tests/", "__pycache__/"):
        assert required in active_patterns, (
            f".dockerignore missing active entry: {required!r} (saw {sorted(active_patterns)})"
        )


@pytest.mark.integration
def test_workflow_has_required_safety_gates() -> None:
    """`.github/workflows/staging-deploy.yaml` ships the ADR-required gates + Round-2 guards."""
    workflow_file = REPO_ROOT / ".github" / "workflows" / "staging-deploy.yaml"
    assert workflow_file.exists(), f"missing {workflow_file}"
    body = workflow_file.read_text(encoding="utf-8")
    # ADR-007: judge LLM locked.
    assert "JUDGE_LLM=gemini-3.5-flash" in body, "JUDGE_LLM lock missing"
    # ADR-008 blue/green: candidate tag + no-traffic + smoke + promote.
    assert "--tag=candidate" in body, "blue/green --tag=candidate missing"
    assert "--no-traffic" in body, "blue/green --no-traffic missing"
    assert "update-traffic" in body, "promote step missing"
    # ADR-009: secrets sourced from Secret Manager, never literal.
    assert "PHOENIX_API_KEY=phoenix-api-key:latest" in body, "secrets binding missing"
    assert "GEMINI_API_KEY=gemini-api-key:latest" in body, "secrets binding missing"
    # Non-public.
    assert "--no-allow-unauthenticated" in body, "public traffic not blocked"
    # Round-2 silent-failure-hunter findings:
    assert "Guard required repo variables" in body, "PROJECT_HASH guard step missing"
    assert "Pre-flight Secret Manager check" in body, "pre-flight secret check missing"
    assert "Cleanup candidate revision on failure" in body, (
        "if: failure() cleanup step missing — failed deploys accumulate revisions"
    )
    assert "if: failure()" in body, "failure-conditional cleanup trigger missing"
