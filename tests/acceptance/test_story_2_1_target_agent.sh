#!/usr/bin/env bash
# Acceptance test for story-2.1-naive-target-agent.
# Translates BDD criteria from docs/stories/story-2.1-naive-target-agent.md.
# Exit 0 = story complete.
#
# Run from anywhere: bash tests/acceptance/test_story_2_1_target_agent.sh

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- BDD: pyproject.toml exists with google-adk + pytest deps ---------------
assert_file apps/target-agent/pyproject.toml
assert_grep "google-adk" apps/target-agent/pyproject.toml
assert_grep "pytest" apps/target-agent/pyproject.toml
pass "apps/target-agent/pyproject.toml declares google-adk + pytest"

# -- BDD: package layout exists ---------------------------------------------
assert_file apps/target-agent/src/target_agent/__init__.py
assert_file apps/target-agent/src/target_agent/agent.py
assert_file apps/target-agent/src/target_agent/tools.py
assert_file apps/target-agent/src/target_agent/main.py
pass "target_agent package layout in place"

# -- BDD: uv sync succeeds for the new app ---------------------------------
run_silent uv sync
pass "workspace uv sync (including target-agent) exits 0"

# -- BDD: agent import smoke test ------------------------------------------
run_silent uv run python -c "
from target_agent.agent import root_agent
assert root_agent.name == 'target_customer_support', f'name={root_agent.name}'
assert root_agent.model == 'gemini-3.5-flash', f'model={root_agent.model}'
assert len(root_agent.tools) == 3, f'len(tools)={len(root_agent.tools)}'
"
pass "root_agent has correct name + model + tool count"

# -- BDD: lookup_order returns dict with status/items/total -----------------
run_silent uv run python -c "
from target_agent.tools import lookup_order, _seed_orders_db
_seed_orders_db()
r = lookup_order('12345')
assert isinstance(r, dict), 'must return dict'
for k in ('status', 'items', 'total'):
    assert k in r, f'missing key: {k}'
"
pass "lookup_order returns dict with status/items/total"

# -- BDD: refund called twice succeeds twice (no idempotency — naive) -------
run_silent uv run python -c "
from target_agent.tools import refund, _refund_ledger_for_tests, _seed_orders_db
_seed_orders_db()
_refund_ledger_for_tests().clear()
refund('12345', 50.0)
refund('12345', 50.0)
ledger = _refund_ledger_for_tests()
order_entries = [e for e in ledger if e.get('order_id') == '12345']
assert len(order_entries) == 2, f'expected 2 entries, got {len(order_entries)}'
"
pass "refund is deliberately non-idempotent (2 entries on duplicate call)"

# -- BDD: ≥10 pytest unit tests pass ---------------------------------------
echo "Running: uv run pytest apps/target-agent/tests/unit -v ..."
logfile=$(mktemp)
set +e
uv run pytest apps/target-agent/tests/unit -v >"$logfile" 2>&1
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  echo "--- pytest output ---" >&2
  cat "$logfile" >&2
  rm -f "$logfile"
  fail "pytest failed (rc=$rc)"
fi
passed=$(grep -cE "PASSED" "$logfile" || true)
rm -f "$logfile"
if [ "$passed" -lt 10 ]; then
  fail "Expected ≥10 PASSED tests, got $passed"
fi
pass "$passed pytest unit tests passed (≥10 required)"

# -- BDD: no §14 mock/hardcoded violations in src/ -------------------------
violations=$(grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/target-agent/src/ 2>/dev/null | grep -v "§14 carve-out" || true)
if [ -n "$violations" ]; then
  echo "--- §14 violations ---" >&2
  echo "$violations" >&2
  fail "found §14 violations in apps/target-agent/src/"
fi
pass "no §14 mock/fake/dummy/hardcoded/simulated violations in src/"

# -- BDD: 400-line guard passes -------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard passes on full repo (incl. apps/target-agent/src/)"

# -- BDD: ruff + ty pass on target-agent ----------------------------------
run_silent bash -c "cd apps/target-agent && uv run ruff check . && uv run ruff format . --check"
pass "ruff lint + format check pass on apps/target-agent"
# ty is currently disabled per IF-8 (schema in flux). Re-enable when ty 1.0 lands.

# -- BDD: trace-as-assertion fixture works (in-memory OTel) ---------------
run_silent uv run python -c "
import sys
sys.path.insert(0, 'apps/target-agent/src')
from target_agent.tools import lookup_order, _seed_orders_db
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)

_seed_orders_db()
lookup_order('12345')

spans = exporter.get_finished_spans()
tool_spans = [s for s in spans if s.attributes and s.attributes.get('openinference.span.kind') == 'TOOL']
assert len(tool_spans) >= 1, f'expected at least 1 TOOL span, got {len(tool_spans)} (total: {len(spans)})'
ok_spans = [s for s in tool_spans if s.status.is_ok]
assert len(ok_spans) >= 1, 'expected at least 1 TOOL span with status OK'
"
pass "in-memory OTel fixture captures a TOOL span with status OK"

echo
echo "==========================================="
echo "story-2.1 verification: PASS"
echo "==========================================="
