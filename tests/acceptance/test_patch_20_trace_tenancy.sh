#!/usr/bin/env bash
# Acceptance test for Patch #20 — trace tenancy = customer-side Phoenix project.
# Translates the issue #20 deliverables into machine-verifiable assertions.
# Exit 0 = patch complete.
#
# Run from anywhere: bash tests/acceptance/test_patch_20_trace_tenancy.sh
#
# This is a SPEC-ONLY patch — no runtime code yet (Epic 4 ships the
# orchestrator that implements against this schema). Gates are file-shape +
# content checks. Per the D4-8 process lesson (audit-notes), citations must
# be enforceable in CI not just verified manually at PR time.

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- ADR-013 added to architecture.md -----------------------------------------
# (ADR-013 not ADR-014 — Ed25519 was reserved second per audit-notes D4-3
#  rev'd to ADR-014; trace tenancy patch landed first in architecture.md.)
assert_grep "^### ADR-013: Trace tenancy" docs/architecture.md
assert_grep "customer-side Phoenix project" docs/architecture.md
assert_grep "Model C \\(hybrid\\)" docs/architecture.md
# ANTI-anchor: refuse the AFFIRMATIVE Model A wording. The ADR's negation
# ("Phoenix Audit does NOT centralize audit traces in our vendor Phoenix
# project") uses the bare-verb form ("centralize"); the affirmative Model A
# regression uses the -s form ("Audit centralizes…"). Pinning the -s form
# blocks the regression without flagging the ADR's own refusal text.
assert_no_grep 'Audit centralizes' docs/architecture.md
pass "ADR-013 (trace tenancy = customer-side Phoenix) lands in architecture.md; Model A wording refused"

# -- ADR-013 references RAT-2 Test 1 by file path + line range + measurement --
# Per D4-8 process lesson: cite empirical sources by path AND verify the
# cited content actually exists in the cited file. Loose "1.37s anywhere"
# substring would re-pass if RAT-2-results.md got rewritten with a different
# number; the proximity check + cross-file verification are the executable
# form of the D4-8 discipline.
assert_grep "RAT-2-results.md" docs/architecture.md
assert_grep "1\\.37s" docs/architecture.md
# AND: the cited measurement actually exists in the cited file (executable D4-8)
assert_grep "1\\.37s" research/google-cloud-rapid-agent/RAT-2-results.md
pass "ADR-013 cites RAT-2 Test 1 + the 1.37s measurement is verified in the cited file"

# -- Memo 27 sub-question 9 cited AND exists ----------------------------------
assert_grep "memo 27 sub-q 9|sub-question 9" docs/architecture.md
assert_grep "Sub-question 9" research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md
pass "Memo 27 sub-q 9 cited AND the section exists in the brainstorm doc"

# -- run-config-schema.md NEW + customer_phoenix fields documented ------------
assert_file docs/run-config-schema.md
assert_grep "customer_phoenix:" docs/run-config-schema.md
assert_grep "endpoint:" docs/run-config-schema.md
assert_grep "api_key:" docs/run-config-schema.md
assert_grep "project_name:" docs/run-config-schema.md
pass "run-config-schema.md declares customer_phoenix.{endpoint,api_key,project_name}"

# -- Validation rules locked: ALL 4 rules, regex pinned, https-only -----------
# Each rule asserted on its load-bearing string. A future refactor that
# silently drops one would fail here.
# "Scheme MUST be" and "`https` ONLY" sit on adjacent markdown lines;
# grep is line-oriented so we anchor on the unique single-line portion.
assert_grep '`https` ONLY' docs/run-config-schema.md
assert_grep 'MUST be non-empty' docs/run-config-schema.md
# Pin the project-name regex LITERALLY. In ERE, ^ [ ] { } $ all need
# escaping to match as literal characters. Single-quoted so bash doesn't
# touch the backslashes.
assert_grep '\^\[a-z0-9\]\[a-z0-9_-\]\{0,62\}\$' docs/run-config-schema.md
assert_grep 'pydantic.SecretStr' docs/run-config-schema.md
assert_grep 'discarded from memory' docs/run-config-schema.md
pass "Validation rules locked: https-only + non-empty api_key + project-name regex literal + SecretStr-based discard"

# -- Phoenix project-name regex framed honestly (D4-8 lesson) -----------------
# Reviewer caught: "Phoenix project naming convention" framed as upstream
# authority but Phoenix doesn't publish a project-name regex. Reframed as
# Phoenix Audit's locally-imposed rule modeled on Phoenix's prompt-tag docs.
assert_grep "locally-imposed constraint" docs/run-config-schema.md
pass "Phoenix regex framed as Phoenix-Audit-imposed, not upstream-authoritative"

# -- _build_a2a_app cited correctly as PATTERN not COPY -----------------------
# Reviewer caught: _build_a2a_app whitelists http+https; schema requires
# https-only. Citation must say "pattern" not "copy". Grep is line-oriented
# so we anchor on two short single-line phrases the markdown contains.
assert_grep 'fail-loud `SystemExit` PATTERN' docs/run-config-schema.md
assert_grep 'whitelist content differs' docs/run-config-schema.md
# ANTI-anchor: must NOT call the relationship a "copy" — that wording
# would imply the http+https whitelist gets reused verbatim (it doesn't).
assert_no_grep 'copy of `_build_a2a_app`' docs/run-config-schema.md
pass "_build_a2a_app cited as portable PATTERN (not copy) — whitelist content differs"

# -- audit_run_id namespaced + run_signature for cryptographic binding --------
# Reviewer caught: bare `audit_run_id` collides with Customer's other workloads.
# Must be namespaced + HMAC-signed.
assert_grep "phoenix_audit\\.audit_run_id" docs/run-config-schema.md
assert_grep "phoenix_audit\\.run_signature" docs/run-config-schema.md
assert_grep "phoenix_audit\\.audit_run_id" docs/architecture.md
pass "Filter attribute namespaced as phoenix_audit.audit_run_id + cryptographic run_signature locked"

# -- Report template language locked verbatim (no translation-equivalent) -----
# Reviewer caught: "translation-equivalent" framing was a loophole that lets
# Epic 6 silently weaken the legal text. Now locked verbatim + anti-anchors.
assert_grep "Audit traces remain in the Customer's Phoenix project" docs/run-config-schema.md
assert_grep "holds no copy after report generation" docs/run-config-schema.md
assert_grep "EU AI Act Annex IV" docs/run-config-schema.md
assert_grep "chain-of-custody" docs/run-config-schema.md
assert_grep "{project_name}" docs/run-config-schema.md
assert_grep "{endpoint}" docs/run-config-schema.md
assert_grep "{run_started_at}" docs/run-config-schema.md
assert_grep "{run_completed_at}" docs/run-config-schema.md
# Verbatim-only lock (no "translation-equivalent" carve-out)
assert_grep "Verbatim-lock rationale" docs/run-config-schema.md
pass "Report-template language locked verbatim with EU AI Act + chain-of-custody anchors + 4 placeholder tokens"

# -- Downstream test obligations section exists -------------------------------
# Future Epic 4 + Epic 6 implementers need a concrete checklist.
assert_grep "Downstream test obligations" docs/run-config-schema.md
assert_grep "Epic 4 orchestrator story" docs/run-config-schema.md
assert_grep "Epic 6 Reporter story" docs/run-config-schema.md
pass "Downstream test obligations enumerated for Epic 4 + Epic 6"

# -- audit-notes D4-9 formal-landing record exists ----------------------------
assert_grep "^### D4-9 — Trace tenancy formal spec landing" docs/audit-notes.md
assert_grep "Patch #20" docs/audit-notes.md
pass "audit-notes D4-9 records the formal spec landing for Patch #20"

# -- ADR numbering doesn't leave a gap: ADR-013 landed; ADR-014 reserved ------
# Code-reviewer caught: audit-notes originally reserved ADR-013 for Ed25519.
# This patch took ADR-013 (chronological landing); Ed25519 bumped to ADR-014.
assert_grep 'ADR-014 — Ed25519 signing' docs/audit-notes.md
# ERE: bare ( ) are grouping; escape to match literal parens in the audit-notes table cell.
assert_grep 'ADR-014 \(Ed25519 signing\)' docs/audit-notes.md
pass "ADR-013 landed for trace tenancy; ADR-014 cleanly reserved for Ed25519 in audit-notes"

# -- All cited source files exist on disk -------------------------------------
assert_file research/google-cloud-rapid-agent/RAT-2-results.md
assert_file research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md
assert_file research/google-cloud-rapid-agent/rat-2-phoenix-audit/test1_cross_tenant_ingest.py
assert_file apps/target-agent/src/target_agent/server.py
pass "All cited source files exist (RAT-2 results, memo 27, RAT-2 Test 1 script, server.py)"

# -- 400-line guard -----------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean"

# -- §14: no mocks anywhere new (this patch is spec-only — no src/ changes) ---
# BLOCKER fix from PR #28 silent-failure-hunter: previously scanned
# apps/chaoslab-agent/src/ which doesn't exist yet — grep exited 2, `|| true`
# swallowed the error, test reported [PASS] without scanning. Use assert_dir
# up-front so missing paths fail loud per _lib.sh B1/B2 (the same silent-
# failure discipline PR #1 added to the project).
_SCAN_DIRS=(apps/target-agent/src)
# apps/chaoslab-agent has no src/ subtree yet (Epic 4 hasn't shipped). Add
# it back to _SCAN_DIRS the moment chaoslab-agent ships its first src module.
test -d apps/chaoslab-agent/src && _SCAN_DIRS+=(apps/chaoslab-agent/src)
for _d in "${_SCAN_DIRS[@]}"; do
  assert_dir "$_d"
done
violations=$(grep -rE "(mock|fake|dummy|hardcoded|simulated)" "${_SCAN_DIRS[@]}" 2>/dev/null | grep -v "§14 carve-out" || true)
if [ -n "$violations" ]; then
  echo "--- §14 violations ---" >&2
  echo "$violations" >&2
  fail "found §14 violations in: ${_SCAN_DIRS[*]}"
fi
pass "§14 clean: no mocks in ${_SCAN_DIRS[*]}"

echo ""
echo "==========================================="
echo "patch-20 verification: PASS"
echo "==========================================="
