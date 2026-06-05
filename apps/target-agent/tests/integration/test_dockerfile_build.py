"""Integration test: target-agent Dockerfile builds + runs as non-root.

Marked @pytest.mark.integration and @pytest.mark.slow because the `docker build`
can take 60-180 seconds on a cold cache. Skipped if docker isn't in PATH so
local-dev contributors without docker can still run the unit suite.

What this test proves:
  - The multi-stage Dockerfile builds successfully against the workspace-root
    context (not the app-dir context the original story spec assumed).
  - The resulting image is under the 500 MB budget per the BDD criterion.
  - The runtime user is uid 10001 (non-root enforcement).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_IMAGE_TAG = "target-agent:pytest-s2-4"
_SIZE_CAP_BYTES = 500 * 1024 * 1024  # 500 MB per the BDD criterion.
_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_DOCKERFILE_PATH = Path("apps/target-agent/Dockerfile")


@pytest.fixture(scope="module")
def docker_cli() -> str:
    """Return path to docker CLI, or skip the test module if absent."""
    cli = shutil.which("docker")
    if cli is None:
        pytest.skip("docker not in PATH — skipping container build integration tests")
    return cli


@pytest.fixture(scope="module")
def built_image(docker_cli: str) -> str:
    """Build the image once per module (slow); subsequent tests reuse it."""
    result = subprocess.run(  # noqa: S603 — docker_cli is shutil.which() resolved
        [
            docker_cli,
            "build",
            "-t",
            _IMAGE_TAG,
            "-f",
            str(_DOCKERFILE_PATH),
            ".",
        ],
        cwd=_WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"docker build returned {result.returncode}:\n"
            f"--- stdout (last 2000 chars) ---\n{result.stdout[-2000:]}\n"
            f"--- stderr (last 2000 chars) ---\n{result.stderr[-2000:]}"
        )
    return _IMAGE_TAG


def test_dockerfile_builds_from_workspace_root_context(built_image: str) -> None:
    """The built_image fixture is the test: if build fails, fixture fails."""
    assert built_image == _IMAGE_TAG


def test_image_size_under_500mb(docker_cli: str, built_image: str) -> None:
    """Image stays under the BDD-mandated 500 MB cap."""
    result = subprocess.run(  # noqa: S603
        [docker_cli, "image", "inspect", "--format={{.Size}}", built_image],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    size_bytes = int(result.stdout.strip())
    size_mb = size_bytes // (1024 * 1024)
    assert size_bytes < _SIZE_CAP_BYTES, (
        f"image size {size_mb} MB exceeds 500 MB cap; inspect "
        f"`docker history {built_image} --no-trunc` to find the bloat"
    )


def test_container_runs_as_uid_10001(docker_cli: str, built_image: str) -> None:
    """Non-root enforcement: container runs as appuser (uid 10001)."""
    result = subprocess.run(  # noqa: S603
        [docker_cli, "run", "--rm", built_image, "id", "-u"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, f"id -u failed: {result.stderr}"
    assert result.stdout.strip() == "10001", (
        f"container uid {result.stdout.strip()!r} != 10001 — non-root enforcement broken"
    )


def test_container_path_starts_with_venv(docker_cli: str, built_image: str) -> None:
    """The /opt/venv/bin is first in $PATH so `uv run target-agent` finds the venv."""
    result = subprocess.run(  # noqa: S603
        [docker_cli, "run", "--rm", built_image, "sh", "-c", "echo $PATH"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("/opt/venv/bin:"), (
        f"PATH should start with /opt/venv/bin: but got: {result.stdout.strip()!r}"
    )


def test_target_agent_module_imports_in_container(docker_cli: str, built_image: str) -> None:
    """Python can import target_agent inside the container.

    `PHOENIX_OBSERVABILITY_OPTIONAL=1` is set because the container has no
    Phoenix creds + no K_SERVICE; without the opt-in the import would log
    but still succeed since the degraded path returns DegradedTracerProvider.
    Setting it explicitly makes the test deterministic across environments.
    """
    result = subprocess.run(  # noqa: S603
        [
            docker_cli,
            "run",
            "--rm",
            "-e",
            "PHOENIX_OBSERVABILITY_OPTIONAL=1",
            built_image,
            "python",
            "-c",
            "import target_agent; print(target_agent.__name__)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"import failed inside container:\n--- stderr ---\n{result.stderr[-1500:]}"
    )
    assert "target_agent" in result.stdout, f"unexpected stdout: {result.stdout!r}"
