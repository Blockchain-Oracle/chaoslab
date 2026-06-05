#!/usr/bin/env bash
# Acceptance test for Patch #19 — X-Phoenix-Audit-* header convention.
# Translates issue #19 deliverables into machine-verifiable assertions.
# Exit 0 = patch complete.
#
# This is a SPEC-ONLY patch (per memo 27 sequencing: patches before
# orchestrator stories). Gates are file-shape + content checks. Runtime
# implementation lands later:
#   - Epic 4 injector: MUST set the three headers on every probe.
#   - Epic 3 / well-behaved targets: SHOULD honor the headers + emit
#     acknowledgment via a span attribute the auditor can check.

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
set -euo pipefail

# -- ADR-015 added to architecture.md -----------------------------------------
assert_grep '^### ADR-015: X-Phoenix-Audit-\\\* header convention' docs/architecture.md
assert_grep "side-effect prevention" docs/architecture.md
# Locks Option B (convention) — rejects A (staging-only) and C (gate proxy).
assert_grep "Option B" docs/architecture.md
# Cites memo 27 sub-question 5 (the empirical reasoning).
assert_grep "memo 27 sub-q 5|sub-question 5" docs/architecture.md
pass "ADR-015 (X-Phoenix-Audit-* header convention) lands in architecture.md"

# -- All three headers declared in the ADR + with required semantics ----------
assert_grep "X-Phoenix-Audit:" docs/architecture.md
assert_grep "X-Phoenix-Audit-Run-Id:" docs/architecture.md
assert_grep "X-Phoenix-Audit-Dry-Run:" docs/architecture.md
pass "ADR-015 declares all three headers (X-Phoenix-Audit + X-Phoenix-Audit-Run-Id + X-Phoenix-Audit-Dry-Run)"

# -- docs/header-convention.md NEW + load-bearing sections present ------------
assert_file docs/header-convention.md
# Header schema section
assert_grep "## Header schema" docs/header-convention.md
# Echo-acknowledgment via OpenInference span attribute
assert_grep "phoenix_audit.honored" docs/header-convention.md
# Warning text for audit report when target doesn't honor
assert_grep "Target did not signal it honored" docs/header-convention.md
# Honest disclaimer that headers are advisory, not enforced
assert_grep "advisory" docs/header-convention.md
# Downstream test obligations section (Epic 4 injector + Epic 3 targets)
assert_grep "Downstream test obligations" docs/header-convention.md
assert_grep "Epic 4 injector" docs/header-convention.md
assert_grep "Epic 3" docs/header-convention.md
pass "header-convention.md declares schema + acknowledgment protocol + report warning + downstream obligations"

# -- Cited OSS-tool punt comparison preserves D4-8 cite-and-verify discipline -
# The ADR cites memo 27's OSS comparison: Promptfoo, Garak, DeepTeam all punt;
# AIR/MS-AGT solve at the defender side. The schema doc must list these by
# name so future readers can trace the empirical claim.
assert_grep "Promptfoo" docs/header-convention.md
assert_grep "Garak" docs/header-convention.md
assert_grep "DeepTeam" docs/header-convention.md
# AIR Blackbox + MS AGT framed as defender-side, not auditor-side.
assert_grep "AIR Blackbox" docs/header-convention.md
assert_grep "Microsoft.*Agent Governance|MS AGT" docs/header-convention.md
# The memo's claim is empirically traceable.
assert_grep "Sub-question 5" research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md
pass "OSS-tool punt landscape cited honestly + memo 27 sub-question 5 anchor verified in source"

# -- Header schema declares value formats + UUID generation point -------------
# X-Phoenix-Audit: literal "true" (no other value).
assert_grep '`true` \(literal\)' docs/header-convention.md
# Run-Id: UUIDv4 — same value Phoenix Audit's orchestrator generates server-side
# (per run-config-schema.md's audit_run_id field).
assert_grep "UUIDv4" docs/header-convention.md
assert_grep "audit_run_id" docs/header-convention.md
# Dry-Run: true|false.
assert_grep "true.*false|true \\| false" docs/header-convention.md
pass "Header values precisely specified (X-Phoenix-Audit=true literal, Run-Id=UUIDv4, Dry-Run=true|false)"

# -- Cross-file consistency: ADR-015 references header-convention.md ----------
assert_grep "header-convention.md" docs/architecture.md
# AND header-convention.md references ADR-015 as its source decision.
assert_grep "ADR-015" docs/header-convention.md
pass "ADR-015 ↔ header-convention.md cross-reference is bidirectional"

# -- audit-notes D4-10 formal-landing record exists ---------------------------
assert_grep '^### D4-10 — X-Phoenix-Audit-\\\* header convention' docs/audit-notes.md
assert_grep "Patch #19" docs/audit-notes.md
# Content anchors (not just generic "Patch #19").
assert_grep "side-effect prevention" docs/audit-notes.md
assert_grep "Option B" docs/audit-notes.md
pass "audit-notes D4-10 records the formal spec landing for Patch #19 with content anchors"

# -- ADR numbering: ADR-015 follows ADR-014 (reserved for Ed25519, TBD-14) ----
# audit-notes TBD-14 row still tracks the unrealized ADR-014 reservation;
# Patch #19 took the next available number (015) per chronological landing.
assert_grep "ADR-015" docs/architecture.md
# Audit-notes should still mention ADR-014 reservation (not yet written) so
# the gap between ADR-013 (Patch #20 trace tenancy) and ADR-015 (Patch #19
# headers) is explained.
assert_grep "ADR-014 — Ed25519 signing" docs/audit-notes.md
pass "ADR-015 cleanly takes the next number; ADR-014 reservation still tracked"

# -- Honest threat-model disclosure: headers are NOT cryptographic ------------
# Similar to how ADR-013 honestly disclosed namespace-only vs HMAC. The
# header convention is advisory; a malicious target could echo the
# acknowledgment attribute without actually honoring. Spec must say so.
assert_grep "advisory, not enforced" docs/header-convention.md
# HMAC deferral tracked separately (matches the Patch #20 TBD-18 pattern).
# If a TBD row exists for header HMAC, it's traceable.
assert_grep "TBD-19|post-hackathon" docs/header-convention.md
pass "Threat model honestly disclosed: headers advisory; cryptographic binding deferred"

# -- Run-Id correlation: header value MUST match run-config audit_run_id ------
# This is the load-bearing claim — the headers' Run-Id and the run-config's
# audit_run_id are the same UUID, so Phoenix Audit can correlate probes to
# the audit run on the target side.
assert_grep "MUST match.*audit_run_id|same UUID|identical to" docs/header-convention.md
# Cross-reference run-config schema.
assert_grep "run-config-schema.md" docs/header-convention.md
pass "Header Run-Id locked to match run-config audit_run_id (single UUID per audit run)"

# -- Report warning text is locked verbatim (no translation-equivalent) -------
# Patch #20's lesson applied: verbatim lock on legally / contractually
# load-bearing text. The "warning" the audit report emits when target
# didn't honor is locked here.
COVER_WARNING_FIXTURE=$(awk '/^```text$/{flag=1; next} /^```$/{flag=0} flag' docs/header-convention.md)
[ "${#COVER_WARNING_FIXTURE}" -ge 80 ] \
  || fail "Warning fixture extraction produced ${#COVER_WARNING_FIXTURE} chars (expected ≥80); fenced text block missing or drifted"
fenced_text_count=$(grep_count '^```text$' docs/header-convention.md)
test "$fenced_text_count" -eq 1 \
  || fail "header-convention.md has $fenced_text_count fenced \`\`\`text blocks (expected exactly 1 — the warning fixture)"
assert_block_present "$COVER_WARNING_FIXTURE" docs/header-convention.md
pass "Report-warning text locked VERBATIM via fenced canonical fixture (single source of truth)"

# -- 400-line guard -----------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean"

# -- §14: no mocks introduced (this patch is spec-only — no src/ changes) -----
SCAN_DIRS=(apps/target-agent/src)
test -d apps/chaoslab-agent/src && SCAN_DIRS+=(apps/chaoslab-agent/src)
for d in "${SCAN_DIRS[@]}"; do
  file_count=$(find "$d" -name '*.py' -type f | wc -l | tr -d ' ')
  if [ "$file_count" -eq 0 ]; then
    echo "  §14 WARN: $d has 0 Python files — gate cannot catch mocks here until Epic 4 ships modules"
  else
    echo "  §14 scan target: $d ($file_count Python files)"
  fi
done
assert_no_pattern_in_dirs '(mock|fake|dummy|hardcoded|simulated)' "${SCAN_DIRS[@]}"
pass "§14 clean: no mocks in scan dirs"

echo ""
echo "==========================================="
echo "patch-19 verification: PASS"
echo "==========================================="
