#!/usr/bin/env bash
# Acceptance test for story-2.3-target-phoenix-instrumentation.
# Translates BDD criteria from docs/stories/story-2.3-target-phoenix-instrumentation.md.
# Exit 0 = story complete.
#
# Run from anywhere: bash tests/acceptance/test_story_2_3_target_phoenix.sh

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- BDD: observability.py + unit test + integration test files exist ----------
assert_file apps/target-agent/src/target_agent/observability.py
assert_file apps/target-agent/tests/unit/test_observability.py
assert_file apps/target-agent/tests/integration/test_phoenix_instrumentation.py
assert_file apps/target-agent/.env.example
pass "S2.3 file map present"

# -- BDD: required Phoenix deps declared in pyproject ---------------------------
assert_grep "arize-phoenix-otel" apps/target-agent/pyproject.toml
assert_grep "arize-phoenix-client" apps/target-agent/pyproject.toml
assert_grep "openinference-instrumentation-google-adk" apps/target-agent/pyproject.toml
assert_grep "google-cloud-secret-manager" apps/target-agent/pyproject.toml
pass "Phoenix observability deps declared"

# -- BDD: uv sync resolves the new deps cleanly --------------------------------
run_silent uv sync
pass "workspace uv sync with new observability deps exits 0"

# -- BDD: setup_observability is importable + callable -------------------------
# Note: importing observability does NOT call setup_observability() — the
# function is invoked only when server.py loads. This guarantees plain
# library-mode imports of target_agent.tools/agent don't trigger Phoenix.
run_silent uv run --directory apps/target-agent python -c "
from target_agent.observability import setup_observability
assert callable(setup_observability), 'setup_observability is not callable'
"
pass "target_agent.observability.setup_observability is callable"

# -- BDD: register() called with mandatory ADR-005 flags -----------------------
# Either flag order: both must appear inside the same register() call.
assert_grep "register\(" apps/target-agent/src/target_agent/observability.py
assert_grep "set_global_tracer_provider=False" apps/target-agent/src/target_agent/observability.py
assert_grep "batch=False" apps/target-agent/src/target_agent/observability.py
pass "register() declares set_global_tracer_provider=False + batch=False"

# -- BDD: GoogleADKInstrumentor wired to the tracer provider -------------------
assert_grep "GoogleADKInstrumentor\(\)\.instrument\(tracer_provider=" apps/target-agent/src/target_agent/observability.py
pass "GoogleADKInstrumentor().instrument(tracer_provider=...) wired"

# -- BDD: import order in server.py — setup_observability BEFORE google.adk ----
# Per ADR-005: instrumentation must patch ADK module attributes before any
# consumer code holds pre-patch references, or spans silently disappear.
run_silent python3 - <<'PY'
import re
import sys

with open("apps/target-agent/src/target_agent/server.py") as f:
    lines = f.readlines()

setup_ln = None
adk_ln = None
agent_ln = None
for i, line in enumerate(lines, 1):
    # Match the CALL (not just the import) of setup_observability().
    if setup_ln is None and "setup_observability(" in line and "import" not in line:
        setup_ln = i
    if adk_ln is None and re.match(r"\s*from google\.adk", line):
        adk_ln = i
    if agent_ln is None and re.match(r"\s*from target_agent\.agent", line):
        agent_ln = i

assert setup_ln is not None, "setup_observability() call not found in server.py"
if adk_ln is not None and setup_ln >= adk_ln:
    sys.exit(
        f"ADR-005 violation: setup_observability() at line {setup_ln} "
        f"must come BEFORE 'from google.adk' import at line {adk_ln}"
    )
if agent_ln is not None and setup_ln >= agent_ln:
    sys.exit(
        f"ADR-005 violation: setup_observability() at line {setup_ln} "
        f"must come BEFORE 'from target_agent.agent' import at line {agent_ln}"
    )
PY
pass "import order: setup_observability() called BEFORE google.adk + target_agent.agent imports"

# -- BDD: unit test exercises setup_observability + skips integration without key
ALL_LOG="$(mktemp)"
(cd apps/target-agent && uv run pytest tests/unit -v) >"$ALL_LOG" 2>&1 || {
  echo "--- pytest unit output ---" >&2
  cat "$ALL_LOG" >&2
  rm -f "$ALL_LOG"
  fail "pytest unit suite failed"
}
UNIT_PASSED=$(grep_count "PASSED" "$ALL_LOG")
rm -f "$ALL_LOG"
if [ "$UNIT_PASSED" -lt 12 ]; then
  fail "expected ≥12 unit tests PASSED (10 from S2.1 + ≥2 new), got $UNIT_PASSED"
fi
pass "unit tests pass ($UNIT_PASSED tests green)"

# -- BDD: integration test SKIPS without PHOENIX_API_KEY (no failure) ----------
# Run the integration test explicitly; expect SKIPPED or PASSED, never FAILED.
INT_LOG="$(mktemp)"
(
  cd apps/target-agent
  # Explicitly UNSET PHOENIX_API_KEY so the @skipif fires deterministically.
  env -u PHOENIX_API_KEY uv run pytest tests/integration/test_phoenix_instrumentation.py -v
) >"$INT_LOG" 2>&1 || {
  echo "--- pytest integration output ---" >&2
  cat "$INT_LOG" >&2
  rm -f "$INT_LOG"
  fail "integration test errored without PHOENIX_API_KEY (should have SKIPPED)"
}
INT_FAILED=$(grep_count "FAILED" "$INT_LOG")
rm -f "$INT_LOG"
if [ "$INT_FAILED" -gt 0 ]; then
  fail "integration test FAILED without PHOENIX_API_KEY (should have SKIPPED): $INT_FAILED failures"
fi
pass "integration test skips gracefully without PHOENIX_API_KEY"

# -- §14: no mocks/fake/dummy/hardcoded in src ---------------------------------
violations=$(grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/target-agent/src/ 2>/dev/null | grep -v "§14 carve-out" || true)
if [ -n "$violations" ]; then
  echo "--- §14 violations ---" >&2
  echo "$violations" >&2
  fail "found §14 violations in apps/target-agent/src/"
fi
pass "§14 clean: no mocks in apps/target-agent/src/"

# -- 400-line guard ------------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean (repo-wide scan)"

# -- ruff + format (target-agent isolated env) ---------------------------------
run_silent bash -c "cd apps/target-agent && uv run ruff check ."
run_silent bash -c "cd apps/target-agent && uv run ruff format . --check"
pass "ruff check + format clean on target-agent"

echo ""
echo "==========================================="
echo "story-2.3 verification: PASS"
echo "==========================================="
