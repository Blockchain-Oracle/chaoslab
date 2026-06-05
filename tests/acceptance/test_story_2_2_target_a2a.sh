#!/usr/bin/env bash
# Acceptance test for story-2.2-target-a2a-exposure.
# Translates BDD criteria from docs/stories/story-2.2-target-a2a-exposure.md.
# Exit 0 = story complete.
#
# Run from anywhere: bash tests/acceptance/test_story_2_2_target_a2a.sh

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- BDD: server.py + tests/integration/ exist ----------------------------------
assert_file apps/target-agent/src/target_agent/server.py
assert_file apps/target-agent/tests/integration/__init__.py
assert_file apps/target-agent/tests/integration/test_a2a_card.py
pass "S2.2 file map present (server.py + tests/integration/)"

# -- BDD: pyproject [project.scripts] declares target-agent entry ---------------
assert_toml_key apps/target-agent/pyproject.toml project.scripts
assert_toml_value_contains apps/target-agent/pyproject.toml project.scripts "target_agent.server:main"
pass "[project.scripts] target-agent = 'target_agent.server:main' declared"

# -- BDD: uvicorn[standard] declared in dependencies ----------------------------
assert_grep "uvicorn" apps/target-agent/pyproject.toml
pass "uvicorn dependency declared"

# -- BDD: uv sync still works for workspace -------------------------------------
run_silent uv sync
pass "workspace uv sync (with new uvicorn dep) exits 0"

# -- BDD: server module imports cleanly, exposes a2a_app + main -----------------
run_silent uv run --directory apps/target-agent python -c "
import target_agent.server as s
assert s.a2a_app is not None, 'a2a_app is None'
assert callable(s.main), 'main is not callable'
"
pass "target_agent.server.a2a_app present and main is callable"

# -- BDD: target_agent package re-exports root_agent; a2a_app via server module --
# (Deliberate: dropping a2a_app from __init__ avoids forcing all S2.1 unit tests
# to instantiate the A2A machinery + emit 4 EXPERIMENTAL warnings per import.)
run_silent uv run --directory apps/target-agent python -c "
from target_agent import root_agent
from target_agent.server import a2a_app
assert a2a_app is not None
assert root_agent.name == 'target_customer_support'
"
pass "target_agent re-exports root_agent; a2a_app importable via target_agent.server"

# -- BDD: server module starts cleanly without PHOENIX_API_KEY ------------------
# (Phoenix wiring is S2.3; agent card must resolve without any Phoenix env var.)
run_silent env -u PHOENIX_API_KEY -u PHOENIX_COLLECTOR_ENDPOINT \
  uv run --directory apps/target-agent python -c "
import target_agent.server as s
assert s.a2a_app is not None
"
pass "server.py imports cleanly with no Phoenix env vars set"

# -- BDD: background-launch + curl agent-card.json -----------------------------
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()")
LOGFILE="$(mktemp)"
(
  cd apps/target-agent
  PORT="$PORT" uv run target-agent
) >"$LOGFILE" 2>&1 &
SERVER_PID=$!

# Cleanup on any exit (including failures from set -e below).
cleanup_server() {
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -f "$LOGFILE"
}
trap cleanup_server EXIT

# Poll the agent card endpoint with bounded retries (cold-start window).
CARD_URL="http://127.0.0.1:${PORT}/.well-known/agent-card.json"
CARD_PAYLOAD="$(mktemp)"
ATTEMPTS=0
MAX_ATTEMPTS=60   # ~30s at 500ms intervals
while [ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]; do
  if curl -sf "$CARD_URL" -o "$CARD_PAYLOAD" 2>/dev/null; then
    break
  fi
  # If the server died, print its log and fail fast.
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "--- server log (PID $SERVER_PID died) ---" >&2
    cat "$LOGFILE" >&2
    echo "--- end log ---" >&2
    fail "target-agent server exited before agent-card became reachable"
  fi
  ATTEMPTS=$((ATTEMPTS + 1))
  sleep 0.5
done

if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
  echo "--- server log (never bound to $CARD_URL) ---" >&2
  cat "$LOGFILE" >&2
  echo "--- end log ---" >&2
  fail "agent-card.json never reachable after $((MAX_ATTEMPTS / 2))s"
fi
pass "background-launched target-agent serves /.well-known/agent-card.json (HTTP 200)"

# -- BDD: agent card JSON has name + skills -------------------------------------
python3 -c "
import json, sys
with open('$CARD_PAYLOAD') as f:
    d = json.load(f)
assert d.get('name') == 'target_customer_support', f\"name={d.get('name')}\"
skills = {s.get('name') for s in d.get('skills', []) if isinstance(s, dict)}
expected = {'lookup_order', 'refund', 'escalate'}
missing = expected - skills
assert not missing, f'missing skills: {missing}; got: {skills}'
" || {
  echo "--- captured agent card ---" >&2
  cat "$CARD_PAYLOAD" >&2 || true
  echo "--- end card ---" >&2
  fail "agent-card.json missing expected name or skills"
}
rm -f "$CARD_PAYLOAD"
pass "agent-card.json has name=target_customer_support + skills {lookup_order,refund,escalate}"

# Kill server now (the trap also handles it, but we want explicit teardown
# before running pytest so resources are clean).
cleanup_server
trap - EXIT

# -- BDD: integration test passes -----------------------------------------------
INT_LOG="$(mktemp)"
(cd apps/target-agent && uv run pytest tests/integration -v) >"$INT_LOG" 2>&1 || {
  echo "--- pytest integration output ---" >&2
  cat "$INT_LOG" >&2
  echo "--- end ---" >&2
  rm -f "$INT_LOG"
  fail "pytest tests/integration failed"
}
INT_PASSED=$(grep_count "PASSED" "$INT_LOG")
rm -f "$INT_LOG"
if [ "$INT_PASSED" -lt 2 ]; then
  fail "expected ≥2 integration tests PASSED, got $INT_PASSED"
fi
pass "tests/integration passes ($INT_PASSED tests green)"

# -- BDD: full target-agent suite (unit + integration) still ≥12 ----------------
ALL_LOG="$(mktemp)"
(cd apps/target-agent && uv run pytest tests/ -v) >"$ALL_LOG" 2>&1 || {
  echo "--- pytest full output ---" >&2
  cat "$ALL_LOG" >&2
  echo "--- end ---" >&2
  rm -f "$ALL_LOG"
  fail "full pytest suite failed"
}
ALL_PASSED=$(grep_count "PASSED" "$ALL_LOG")
rm -f "$ALL_LOG"
if [ "$ALL_PASSED" -lt 12 ]; then
  fail "expected ≥12 tests PASSED total (unit + integration), got $ALL_PASSED"
fi
pass "full pytest suite passes ($ALL_PASSED tests green)"

# -- §14: no mocks/fake/dummy/hardcoded/simulated in src ----------------------
violations=$(grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/target-agent/src/ 2>/dev/null | grep -v "§14 carve-out" || true)
if [ -n "$violations" ]; then
  echo "--- §14 violations ---" >&2
  echo "$violations" >&2
  fail "found §14 violations in apps/target-agent/src/"
fi
pass "§14 clean: no mocks in apps/target-agent/src/"

# -- 400-line guard -------------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean (repo-wide scan)"

# -- ruff + format + ty (target-agent isolated env) -----------------------------
run_silent bash -c "cd apps/target-agent && uv run ruff check ."
run_silent bash -c "cd apps/target-agent && uv run ruff format . --check"
pass "ruff check + format clean on target-agent"

echo ""
echo "==========================================="
echo "story-2.2 verification: PASS"
echo "==========================================="
