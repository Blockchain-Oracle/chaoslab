#!/usr/bin/env bash
# Acceptance test for story-5.1.
#
# Locks the AMENDED criteria in docs/stories/story-5.1-vendor-agent-chaos.md
# (attribution-only — no vendoring of deepankarm/agent-chaos sources, per
# audit A5 and ADR-006 amendment 2026-06-03). The story file's original
# ## Shell verification section is historical context only.

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# NOTICE is the single source of truth for the pinned upstream SHA. Extract
# it here so a future repin only edits NOTICE; the test follows automatically
# and the __init__.py docstring does not duplicate the literal.
NOTICE_SHA="$(grep -oE '[0-9a-f]{40}' NOTICE | head -n 1 || true)"
[ -n "$NOTICE_SHA" ] || fail "no 40-char upstream SHA found in NOTICE"

# -- BDD-1: NOTICE attributes deepankarm/agent-chaos + has a pinned SHA ------
assert_file NOTICE
assert_grep "deepankarm/agent-chaos" NOTICE
# Lock the SHA's position to the attribution line, not just any 40-char hex
# that happens to be elsewhere in NOTICE.
assert_grep "(Reference commit|Pinned commit):.*${NOTICE_SHA}" NOTICE
pass "NOTICE attributes deepankarm/agent-chaos with pinned SHA ${NOTICE_SHA}"

# -- BDD-2: no _vendored/ directory across the repo --------------------------
# ADR-006 amendment forbids vendoring repo-wide, not just under one app.
scan_roots=(apps)
[ -d packages ] && scan_roots+=(packages)
[ -d scripts ] && scan_roots+=(scripts)
[ -d tests ] && scan_roots+=(tests)
[ -d infra ] && scan_roots+=(infra)
for r in "${scan_roots[@]}"; do
  assert_dir "$r"
done
set +e
vendored_hits="$(find "${scan_roots[@]}" -type d -name '_vendored' -print)"
rc=$?
set -e
[ "$rc" -eq 0 ] || fail "find tool error scanning ${scan_roots[*]} (rc=$rc)"
if [ -n "$vendored_hits" ]; then
  echo "$vendored_hits" >&2
  fail "_vendored/ directory found (ADR-006 amendment forbids vendoring)"
fi
pass "no _vendored/ directory under ${scan_roots[*]} (ADR-006 amended)"

# -- BDD-3: NOTICE explicitly disclaims code-copy ----------------------------
# Audit-locked: future readers must not treat the attribution block as a
# permission slip to start vendoring later.
assert_grep "[Nn]o source code is copied" NOTICE
pass "NOTICE explicitly disclaims code-copy"

# -- BDD-4: LICENSE is Apache-2.0 (compat precondition) ----------------------
# NOTICE attribution here is courtesy, not a redistribution requirement —
# we do not redistribute upstream source. LICENSE assertion is kept so any
# future copy would start license-compatible.
assert_first_nonblank_contains LICENSE "Apache License"
pass "LICENSE is Apache-2.0 (compat precondition)"

# -- BDD-5: faults/__init__.py marker + attribution --------------------------
faults_dir="apps/chaoslab-agent/src/chaoslab_agent/injector/faults"
assert_dir "$faults_dir"
assert_file "${faults_dir}/__init__.py"
assert_grep "deepankarm/agent-chaos" "${faults_dir}/__init__.py"
assert_grep "Apache-2.0" "${faults_dir}/__init__.py"
pass "faults/__init__.py credits deepankarm/agent-chaos + Apache-2.0"

# -- BDD-6: every fault module in faults/ credits upstream -------------------
# Inclusive default: ANY .py landed under injector/faults/ (other than
# __init__.py) must carry the attribution. Glob-by-filename-convention was
# too narrow — the planned F1-F4 modules use semantic names
# (malformed_tool_output.py, prompt_injection.py, context_poisoning.py,
# latency_spike.py per S5.2-S5.5) and a shared helper / base.py could land
# alongside them. Catch them all and let an explicit allowlist carve out
# legitimately-native modules later if needed.
# `shopt -p nullglob` exits 1 when the option is off (its default), which
# would trip `set -e` during the capture below. The `|| true` is necessary,
# not noise — it lets us snapshot the prior state for later restore.
prev_nullglob="$(shopt -p nullglob || true)"
shopt -s nullglob
fault_modules=("$faults_dir"/*.py)
eval "$prev_nullglob"
filtered=()
for m in "${fault_modules[@]}"; do
  [ "$(basename "$m")" = "__init__.py" ] && continue
  filtered+=("$m")
done
if [ "${#filtered[@]}" -gt 0 ]; then
  for m in "${filtered[@]}"; do
    assert_grep "deepankarm/agent-chaos" "$m"
    assert_grep "Apache-2.0" "$m"
  done
  pass "all ${#filtered[@]} non-__init__ fault modules credit deepankarm/agent-chaos + Apache-2.0"
else
  pass "no F1-F4 fault modules present yet (S5.2-S5.5 will populate)"
fi

echo "story-5.1 verification: PASS"
