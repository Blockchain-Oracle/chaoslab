#!/usr/bin/env bash
# Acceptance test for story-5.1-vendor-agent-chaos.
#
# Story was AMENDED 2026-06-03 per audit A5: no vendoring, attribution-only.
# This test codifies the AMENDED BDD criteria; the ORIGINAL vendor-flow shell
# verification at lines 132-168 of the story is superseded.
#
# Run from anywhere: bash tests/acceptance/test_story_5_1_attribute_agent_chaos.sh
# Online SHA check: PHOENIX_AUDIT_ONLINE=1 bash <this script>

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# Pinned SHA from audit A5 / story-5.1 AMENDED section.
EXPECTED_SHA="32beff46a28ca043e252095e6cc62ffe2010e645"

# -- BDD-1: NOTICE has the attribution + the pinned SHA ----------------------
# Both anchors live in one block — the audit-locked attribution paragraph
# under "## Attributions / ### deepankarm/agent-chaos" in NOTICE.
assert_file NOTICE
assert_grep "deepankarm/agent-chaos" NOTICE
assert_grep "${EXPECTED_SHA}" NOTICE
pass "NOTICE attributes deepankarm/agent-chaos with pinned SHA ${EXPECTED_SHA}"

# -- BDD-2: no _vendored/ directory anywhere under chaoslab-agent/src/ -------
# ADR-006 amendment: the F1-F4 fault primitives are native; vendoring would
# be dead weight because upstream chaos/llm.py hardcodes anthropic.* exceptions
# and patch/providers/gemini.py is a NotImplementedError stub.
# Use find -quit-on-first-match for a clean "did we hit anything?" check.
found_vendored="$(find apps/chaoslab-agent/src -type d -name '_vendored' -print -quit 2>/dev/null || true)"
if [ -n "$found_vendored" ]; then
  fail "_vendored/ directory found at $found_vendored (ADR-006 amendment forbids vendoring)"
fi
pass "no _vendored/ directory under apps/chaoslab-agent/src/ (ADR-006 amended)"

# -- BDD-3: NOTICE explicitly disclaims code-copy (not just attribution) ----
# Audit lock: the attribution paragraph must read "no source code is copied"
# (or equivalent) so a future reader can't accidentally treat this as a
# permission slip to start vendoring later.
assert_grep "[Nn]o source code is copied" NOTICE
pass "NOTICE explicitly disclaims code-copy"

# -- BDD-4: LICENSE precondition (Apache-2.0 compat) -------------------------
# Apache-2.0 § 4 doesn't require attribution for non-copy use, but we keep
# the LICENSE assertion so that if anyone ever DOES decide to copy a file,
# they're starting from a license-compatible base.
assert_first_nonblank_contains LICENSE "Apache License"
pass "LICENSE is Apache-2.0 (license-compat precondition)"

# -- BDD-5: F1-F4 docstring discipline (forward-looking gate) ----------------
# S5.2-S5.5 will create the F1-F4 fault modules. THIS story locks the rule
# that each such module's docstring credits the architectural inspiration
# with the "deepankarm/agent-chaos" + "Apache-2.0" string pair.
# - If the faults/ directory has F1-F4 modules: assert each contains both
#   strings.
# - If it does NOT yet have them (S5.1 lands first): just verify the
#   directory exists as the future home; the docstring assertion becomes
#   active once S5.2-S5.5 land.
faults_dir="apps/chaoslab-agent/src/chaoslab_agent/injector/faults"
# S5.1 lays the package marker so S5.2-S5.5 can land their F<N> modules
# under a regular Python package (not an implicit namespace one).
assert_file "${faults_dir}/__init__.py"
assert_grep "deepankarm/agent-chaos" "${faults_dir}/__init__.py"
assert_grep "Apache-2.0" "${faults_dir}/__init__.py"
pass "faults/__init__.py present + credits deepankarm/agent-chaos + Apache-2.0"

if [ -d "$faults_dir" ]; then
  # Count fault modules (anything matching f<digit>_*.py per the planned naming).
  shopt -s nullglob
  fault_modules=("$faults_dir"/f[0-9]_*.py "$faults_dir"/f[0-9][0-9]_*.py)
  shopt -u nullglob
  if [ "${#fault_modules[@]}" -gt 0 ]; then
    for m in "${fault_modules[@]}"; do
      assert_grep "deepankarm/agent-chaos" "$m"
      assert_grep "Apache-2.0" "$m"
    done
    pass "all ${#fault_modules[@]} fault modules under $faults_dir credit deepankarm/agent-chaos + Apache-2.0"
  else
    pass "faults/ directory present but no F1-F4 modules yet (deferred to S5.2-S5.5)"
  fi
else
  pass "faults/ directory not yet created (S5.2-S5.5 will create it; docstring check defers)"
fi

# -- BDD-6: optional online SHA verification ---------------------------------
# Online check confirms the pinned SHA refers to a real commit on the upstream
# repo. Gated behind PHOENIX_AUDIT_ONLINE=1 to avoid network dependency on
# every PR (cost-discipline per CLAUDE.md). Nightly CI should set the var.
if [ "${PHOENIX_AUDIT_ONLINE:-0}" = "1" ]; then
  if ! command -v gh >/dev/null 2>&1; then
    fail "PHOENIX_AUDIT_ONLINE=1 set but gh CLI not installed"
  fi
  echo "Online check: verifying SHA on github.com/deepankarm/agent-chaos..."
  set +e
  actual_sha="$(gh api "repos/deepankarm/agent-chaos/commits/${EXPECTED_SHA}" --jq .sha 2>&1)"
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    fail "gh api call failed (rc=$rc): $actual_sha"
  fi
  if [ "$actual_sha" != "$EXPECTED_SHA" ]; then
    fail "upstream returned SHA '$actual_sha' but NOTICE pins '$EXPECTED_SHA'"
  fi
  pass "online: SHA ${EXPECTED_SHA} verified against upstream repo"
else
  echo "[skip] online SHA verification (set PHOENIX_AUDIT_ONLINE=1 to enable)"
fi

echo "story-5.1 verification: PASS"
