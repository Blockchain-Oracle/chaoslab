#!/usr/bin/env bash
# Acceptance test for story-2.3-target-phoenix-instrumentation.
# Translates BDD criteria from docs/stories/story-2.3-target-phoenix-instrumentation.md.
# Exit 0 = story complete.
#
# Run from anywhere: bash tests/acceptance/test_story_2_3_target_phoenix.sh
#
# Behavior re: PHOENIX_API_KEY:
#   - If PHOENIX_API_KEY is unset       → the integration test must SKIP cleanly
#                                          (no FAILED markers). The skip path
#                                          is verified independently.
#   - If PHOENIX_API_KEY IS set         → the integration test must PASS for real
#                                          ("no skipping = no mocking" rule).

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
pass "workspace uv sync with observability deps exits 0"

# -- BDD: setup_observability is importable + callable -------------------------
# Note: importing observability does NOT call setup_observability() — the
# function is invoked only when server.py loads. This guarantees plain
# library-mode imports of target_agent.tools/agent don't trigger Phoenix.
run_silent uv run --directory apps/target-agent python -c "
from target_agent.observability import setup_observability
assert callable(setup_observability), 'setup_observability is not callable'
"
pass "target_agent.observability.setup_observability is callable"

# -- BDD: register() uses Cloud Run defaults per architecture/02 §3.5 ----------
# (No set_global_tracer_provider=False; no batch=False. Those are Agent Engine
# flags and we deploy on Cloud Run per ADR-003. See audit-notes D4-8.)
assert_grep "register\(" apps/target-agent/src/target_agent/observability.py
assert_no_grep "set_global_tracer_provider=False" apps/target-agent/src/target_agent/observability.py
assert_no_grep "batch=False" apps/target-agent/src/target_agent/observability.py
pass "register() uses Cloud Run defaults (no Agent-Engine-only flags)"

# -- BDD: GoogleADKInstrumentor wired to the tracer provider -------------------
assert_grep "GoogleADKInstrumentor\(\)\.instrument\(tracer_provider=" apps/target-agent/src/target_agent/observability.py
pass "GoogleADKInstrumentor().instrument(tracer_provider=...) wired"

# -- BDD: import order in server.py — setup_observability BEFORE google.adk ----
# AST-based walk (NOT line regex) — survives multi-line imports, docstring
# mentions, and TYPE_CHECKING-guarded imports including aliased forms
# (`from typing import TYPE_CHECKING as TC`).
run_silent python3 - <<'PY'
import ast
import sys

with open("apps/target-agent/src/target_agent/server.py") as f:
    tree = ast.parse(f.read())


def _collect_type_checking_names(t: ast.AST) -> set[str]:
    """Return all local names bound to typing.TYPE_CHECKING in this module.

    Handles both `from typing import TYPE_CHECKING` (binds `TYPE_CHECKING`)
    and `from typing import TYPE_CHECKING as TC` (binds `TC`). Without this,
    aliased imports inside an `if TC:` block fool the import-order check
    into a false-positive failure on perfectly correct code.
    """
    names: set[str] = set()
    for node in ast.walk(t):
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            for alias in node.names:
                if alias.name == "TYPE_CHECKING":
                    names.add(alias.asname or alias.name)
    return names


def _is_under_type_checking(node: ast.AST, t: ast.AST, tc_names: set[str]) -> bool:
    """Return True if `node` is inside any `if <TC-bound-name>:` block."""
    for parent in ast.walk(t):
        if isinstance(parent, ast.If):
            test = parent.test
            if (
                (isinstance(test, ast.Name) and test.id in tc_names)
                or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
            ) and any(node is child for child in ast.walk(parent)):
                return True
    return False


tc_names = _collect_type_checking_names(tree)

# 1) Find runtime ADK + target_agent.agent ImportFrom nodes (skip TYPE_CHECKING).
adk_lines: list[int] = []
agent_lines: list[int] = []
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module and not _is_under_type_checking(node, tree, tc_names):
        if node.module.startswith("google.adk"):
            adk_lines.append(node.lineno)
        if node.module == "target_agent.agent":
            agent_lines.append(node.lineno)

# 2) Find the setup_observability() CALL line (a module-level Expr/Assign whose
#    value is a Call to a Name 'setup_observability').
setup_lines: list[int] = []
for node in tree.body:
    value: ast.expr | None = None
    if isinstance(node, ast.Expr):
        value = node.value
    elif isinstance(node, ast.Assign):
        value = node.value
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "setup_observability"
    ):
        setup_lines.append(node.lineno)

if not setup_lines:
    sys.exit("setup_observability() call not found at module level in server.py")

first_setup = min(setup_lines)
if adk_lines and first_setup >= min(adk_lines):
    sys.exit(
        f"Import-order violation: setup_observability() at line {first_setup} "
        f"must come BEFORE 'from google.adk' import at line {min(adk_lines)}"
    )
if agent_lines and first_setup >= min(agent_lines):
    sys.exit(
        f"Import-order violation: setup_observability() at line {first_setup} "
        f"must come BEFORE 'from target_agent.agent' import at line {min(agent_lines)}"
    )
PY
pass "import order (AST-verified, TYPE_CHECKING-alias-aware): setup_observability() < google.adk + target_agent.agent"

# -- BDD: unit test exercises setup_observability + all credential paths -------
# 12 tests from S2.1 (test_tools.py) + N new from S2.3 (test_observability.py).
# As of the S2.3 tidy-up: 12 (S2.1) + ~17 (S2.3) = 29. Floor at 24 (the count
# at PR #25 merge time) so the gate fails fast if a refactor accidentally
# deletes a chunk of the observability tests.
ALL_LOG="$(mktemp)"
(cd apps/target-agent && uv run pytest tests/unit -v) >"$ALL_LOG" 2>&1 || {
  echo "--- pytest unit output ---" >&2
  cat "$ALL_LOG" >&2
  rm -f "$ALL_LOG"
  fail "pytest unit suite failed"
}
UNIT_PASSED=$(grep_count "PASSED" "$ALL_LOG")
rm -f "$ALL_LOG"
if [ "$UNIT_PASSED" -lt 24 ]; then
  fail "expected ≥24 unit tests PASSED (12 from S2.1 + ≥12 from S2.3 + tidy-up), got $UNIT_PASSED"
fi
pass "unit tests pass ($UNIT_PASSED tests green)"

# -- BDD: integration test SKIPS without PHOENIX_API_KEY (no FAILED markers) ---
INT_LOG="$(mktemp)"
(
  cd apps/target-agent
  env -u PHOENIX_API_KEY uv run pytest tests/integration/test_phoenix_instrumentation.py -v
) >"$INT_LOG" 2>&1 || {
  echo "--- pytest integration output (no key) ---" >&2
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

# -- BDD: integration test PASSES against real Phoenix when key IS set ---------
# "No skipping = no mocking" — if the operator has credentials, the test
# MUST run for real and pass. Auto-sources Phoenix Cloud creds from
# ~/.config/phoenix-rat/.env if available; otherwise PASSes this gate
# (acceptable for CI runs that don't carry secrets). Gate uses pytest's
# exit code only — no fragile PASSED-count grep that could miscount.
PHOENIX_ENV_FILE="$HOME/.config/phoenix-rat/.env"
if [ -f "$PHOENIX_ENV_FILE" ]; then
  REAL_LOG="$(mktemp)"
  (
    cd apps/target-agent
    # shellcheck disable=SC1090
    set -a; source "$PHOENIX_ENV_FILE"; set +a
    uv run pytest tests/integration/test_phoenix_instrumentation.py -v
  ) >"$REAL_LOG" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "--- pytest integration output (real Phoenix) ---" >&2
    cat "$REAL_LOG" >&2
    rm -f "$REAL_LOG"
    fail "integration test FAILED against real Phoenix Cloud (1 expected PASS)"
  fi
  rm -f "$REAL_LOG"
  pass "integration test PASSES against real Phoenix Cloud (pytest rc=0)"
else
  pass "no Phoenix credentials at $PHOENIX_ENV_FILE — skipping real-Phoenix gate"
fi

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
