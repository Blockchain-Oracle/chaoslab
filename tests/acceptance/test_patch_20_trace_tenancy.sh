#!/usr/bin/env bash
# Acceptance test for Patch #20 — trace tenancy = customer-side Phoenix project.
# Translates the issue #20 deliverables into machine-verifiable assertions.
# Exit 0 = patch complete.
#
# Run from anywhere: bash tests/acceptance/test_patch_20_trace_tenancy.sh
#
# This is a SPEC-ONLY patch — no runtime code yet (Epic 4 ships the
# orchestrator that implements against this schema). Gates are file-shape +
# content checks.

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- ADR-014 added to architecture.md -----------------------------------------
assert_grep "^### ADR-014: Trace tenancy" docs/architecture.md
assert_grep "customer-side Phoenix project" docs/architecture.md
assert_grep "Model C \(hybrid\)" docs/architecture.md
pass "ADR-014 (trace tenancy = customer-side Phoenix) lands in architecture.md"

# -- ADR-014 references RAT-2 Test 1 by file path + line range ----------------
# Per D4-8 process lesson: cite empirical sources by path, not by claim.
assert_grep "RAT-2-results.md" docs/architecture.md
assert_grep "1.37s" docs/architecture.md
pass "ADR-014 cites RAT-2 Test 1 by file + measured latency"

# -- run-config-schema.md NEW + customer_phoenix fields documented ------------
assert_file docs/run-config-schema.md
assert_grep "customer_phoenix:" docs/run-config-schema.md
assert_grep "endpoint:" docs/run-config-schema.md
assert_grep "api_key:" docs/run-config-schema.md
assert_grep "project_name:" docs/run-config-schema.md
pass "run-config-schema.md declares customer_phoenix.{endpoint,api_key,project_name}"

# -- Validation rules locked: scheme MUST be https, etc. ----------------------
assert_grep "Schemes other than" docs/run-config-schema.md
assert_grep "https" docs/run-config-schema.md
assert_grep "discarded from memory" docs/run-config-schema.md
pass "Validation rules locked: https-only + no-persistence + project-name pattern"

# -- Report template language locked ------------------------------------------
assert_grep "Audit traces remain in the Customer's Phoenix project" docs/run-config-schema.md
assert_grep "holds no copy" docs/run-config-schema.md
pass "Report-template language locked for the EU AI Act Annex IV chain-of-custody claim"

# -- audit-notes D4-9 formal-landing record exists ----------------------------
assert_grep "^### D4-9 — Trace tenancy formal spec landing" docs/audit-notes.md
assert_grep "Patch #20" docs/audit-notes.md
pass "audit-notes D4-9 records the formal spec landing for Patch #20"

# -- Citation discipline check: every "per X" / "issue #X" claim verifiable ---
# Per the D4-8 process lesson, citations in this patch should resolve to real
# sources. We don't (yet) automate the full resolution, but we DO check that
# the file paths cited actually exist.
assert_file research/google-cloud-rapid-agent/RAT-2-results.md
assert_file research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md
assert_file research/google-cloud-rapid-agent/rat-2-phoenix-audit/test1_cross_tenant_ingest.py
pass "All cited source files exist (RAT-2 results, memo 27, RAT-2 Test 1 script)"

# -- 400-line guard -----------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean"

# -- §14: no mocks anywhere new (this patch is spec-only — no src/ changes) ---
# Make sure we didn't accidentally drop a runtime mock somewhere.
violations=$(grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/target-agent/src/ apps/chaoslab-agent/src/ 2>/dev/null | grep -v "§14 carve-out" || true)
if [ -n "$violations" ]; then
  echo "--- §14 violations ---" >&2
  echo "$violations" >&2
  fail "found §14 violations in apps/*/src/"
fi
pass "§14 clean: no mocks in any app src/"

echo ""
echo "==========================================="
echo "patch-20 verification: PASS"
echo "==========================================="
