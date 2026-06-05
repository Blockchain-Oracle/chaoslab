#!/usr/bin/env bash
# Acceptance test for story-2.4-target-cloud-run-deploy.
# Translates BDD criteria from docs/stories/story-2.4-target-cloud-run-deploy.md.
# Exit 0 = story complete.
#
# Run from anywhere: bash tests/acceptance/test_story_2_4_target_docker.sh
#
# NOTE: docker is required for the image-build gates. Without docker, only
# the file-shape + dockerfile-content checks fire; the live build is skipped.

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- BDD: Dockerfile + Dockerfile.dockerignore exist --------------------------
# NOTE: the dockerignore file is named `Dockerfile.dockerignore` (NOT plain
# `.dockerignore`) so BuildKit 1.7+ auto-discovers it under the workspace-
# root-context build pattern. A subdirectory `.dockerignore` is silently
# ignored by docker. See PR #27 W1 finding + Dockerfile.dockerignore preamble.
assert_file apps/target-agent/Dockerfile
assert_file apps/target-agent/Dockerfile.dockerignore
pass "S2.4 file map present (Dockerfile + Dockerfile.dockerignore)"

# -- BDD: Dockerfile.dockerignore has key entries -----------------------------
assert_grep "^\.git$" apps/target-agent/Dockerfile.dockerignore
assert_grep "^\.venv$" apps/target-agent/Dockerfile.dockerignore
assert_grep "^tests$" apps/target-agent/Dockerfile.dockerignore
assert_grep "^__pycache__$" apps/target-agent/Dockerfile.dockerignore
pass "Dockerfile.dockerignore excludes .git / .venv / tests / __pycache__"

# -- BDD: Dockerfile uses multi-stage build (deps, build, runtime) ------------
assert_grep "FROM python:3\\.12-slim AS deps" apps/target-agent/Dockerfile
assert_grep "FROM python:3\\.12-slim AS build" apps/target-agent/Dockerfile
assert_grep "FROM python:3\\.12-slim AS runtime" apps/target-agent/Dockerfile
pass "Dockerfile uses multi-stage build (deps → build → runtime)"

# -- BDD: Non-root user (uid 10001) -------------------------------------------
assert_grep "appuser" apps/target-agent/Dockerfile
assert_grep "10001" apps/target-agent/Dockerfile
assert_grep "USER appuser" apps/target-agent/Dockerfile
pass "Dockerfile creates non-root user appuser (uid 10001)"

# -- BDD: CMD uses exec-form for proper signal handling -----------------------
assert_grep "CMD \\[\"uv\", \"run\", \"target-agent\"\\]" apps/target-agent/Dockerfile
pass "Dockerfile uses CMD exec form for signal handling"

# -- BDD: server.py wires PUBLIC_URL for Cloud Run agent-card URL (issue #22) -
# The hardcoded localhost:8001 in to_a2a() means the deployed Cloud Run
# container would serve an unreachable agent-card URL. Verify the fix is
# present (PUBLIC_URL env var used to parameterize to_a2a()).
assert_grep "PUBLIC_URL" apps/target-agent/src/target_agent/server.py
pass "server.py honors PUBLIC_URL env var for agent-card URL (issue #22)"

# -- BDD: 400-line guard (regressed if the new files break it) ----------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean (repo-wide scan)"

# -- BDD: live docker build (if docker daemon is reachable) -------------------
# H-3 from PR #27 silent-failure review: `command -v docker` only checks the
# binary's presence in PATH, NOT the daemon's reachability. A CI runner with
# docker CLI installed but daemon stopped (or wrong DOCKER_HOST, or no socket
# perms) would enter this branch and fail late. The `docker info` probe catches
# the daemon-not-reachable case loud + early. The skip path uses [SKIP] (not
# [PASS]) so a misconfigured CI doesn't ring a false green.
if ! command -v docker >/dev/null 2>&1; then
  echo "[SKIP] docker not in PATH — live-build gates SKIPPED."
  echo "[SKIP] If this is CI for S2.4, the runner is misconfigured — docker is required."
elif ! docker info >/dev/null 2>&1; then
  fail "docker CLI present but daemon unreachable. \`docker info\` failed. Start docker (e.g. \`colima start\`) or fix DOCKER_HOST."
else
  echo "[INFO] docker found; running live build (~60-180s on cold cache)"
  BUILD_LOG="$(mktemp)"
  # Build context = workspace root (uv workspace requires lockfile at root).
  # -f points at the app's Dockerfile.
  if ! docker build -t target-agent:s2-4-test -f apps/target-agent/Dockerfile . >"$BUILD_LOG" 2>&1; then
    echo "--- docker build output ---" >&2
    cat "$BUILD_LOG" >&2
    rm -f "$BUILD_LOG"
    fail "docker build target-agent failed"
  fi
  rm -f "$BUILD_LOG"
  pass "docker build target-agent:s2-4-test exits 0"

  # -- BDD: image size < 500 MB --------------------------------------------
  SIZE=$(docker image inspect --format='{{.Size}}' target-agent:s2-4-test)
  if [ "$SIZE" -ge 500000000 ]; then
    fail "image size $SIZE bytes ≥ 500MB (cap is 500MB)"
  fi
  echo "[INFO] image size: $((SIZE / 1024 / 1024)) MB"
  pass "docker image size $((SIZE / 1024 / 1024)) MB < 500 MB cap"

  # -- BDD: container runs as non-root uid 10001 ----------------------------
  UID_OUT=$(docker run --rm target-agent:s2-4-test id -u 2>&1)
  if [ "$UID_OUT" != "10001" ]; then
    fail "container uid $UID_OUT != 10001 (non-root enforcement broken)"
  fi
  pass "container runs as uid 10001 (non-root)"

  # -- BDD: PATH precedence is /opt/venv/bin first --------------------------
  PATH_OUT=$(docker run --rm target-agent:s2-4-test sh -c 'echo $PATH' 2>&1)
  case "$PATH_OUT" in
    /opt/venv/bin:*) ;;
    *) fail "PATH does not start with /opt/venv/bin: got $PATH_OUT" ;;
  esac
  pass "container PATH starts with /opt/venv/bin"

  # -- BDD: target_agent module imports inside the container ----------------
  # Set PHOENIX_OBSERVABILITY_OPTIONAL=1 because the container starts with
  # NO Phoenix creds AND inherits no K_SERVICE — but in some test envs
  # _should_fail_loud could fire. The opt-in makes the test deterministic.
  IMPORT_OUT=$(docker run --rm -e PHOENIX_OBSERVABILITY_OPTIONAL=1 target-agent:s2-4-test python -c "import target_agent; print(target_agent.__name__)" 2>&1)
  case "$IMPORT_OUT" in
    *target_agent*) ;;
    *) fail "target_agent module import failed inside container; output: $IMPORT_OUT" ;;
  esac
  pass "target_agent module imports cleanly inside container"
fi

# -- §14: no mocks/fake/dummy/hardcoded in src --------------------------------
violations=$(grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/target-agent/src/ 2>/dev/null | grep -v "§14 carve-out" || true)
if [ -n "$violations" ]; then
  echo "--- §14 violations ---" >&2
  echo "$violations" >&2
  fail "found §14 violations in apps/target-agent/src/"
fi
pass "§14 clean: no mocks in apps/target-agent/src/"

echo ""
echo "==========================================="
echo "story-2.4 verification: PASS"
echo "==========================================="
