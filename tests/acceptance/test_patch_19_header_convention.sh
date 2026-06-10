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
# Round-1 test-analyzer MED-4: anchor that BOTH rejected options are
# present-AND-rejected, not just Option B mentioned.
assert_grep "Option B" docs/architecture.md
assert_grep 'Option A.*(AIUC-1|staging)' docs/architecture.md
assert_grep "Option C.*gate proxy|Option C.*proxy" docs/architecture.md
assert_grep "[Rr]ejected" docs/architecture.md
# Cites memo 27 sub-question 5 (the empirical reasoning).
# Round-1 comment-analyzer LOW-4: doc uses 3 different anchor forms;
# the regex accepts the two most common in-doc shapes.
assert_grep "memo 27 sub-q 5|sub-question 5|Sub-question 5" docs/architecture.md
pass "ADR-015 (X-Phoenix-Audit-* header convention) lands in architecture.md + Options A/C rejection anchored"

# -- All three headers declared in the ADR + with required semantics ----------
assert_grep "X-Phoenix-Audit:" docs/architecture.md
assert_grep "X-Phoenix-Audit-Run-Id:" docs/architecture.md
assert_grep "X-Phoenix-Audit-Dry-Run:" docs/architecture.md
pass "ADR-015 declares all three headers (X-Phoenix-Audit + X-Phoenix-Audit-Run-Id + X-Phoenix-Audit-Dry-Run)"

# -- docs/header-convention.md NEW + load-bearing sections present ------------
assert_file docs/header-convention.md
# Header schema section
assert_grep "## Header schema" docs/header-convention.md
# Round-1 silent-failure HIGH-1+HIGH-2 + test-analyzer HIGH-2:
# `phoenix_audit.honored` is the load-bearing acknowledgment attribute.
# Anchor with escaped dot (so drift to phoenix_auditXhonored fails) AND
# count ≥8 occurrences (so partial-drift attack fails) AND anti-anchor
# typo/case variants.
assert_grep 'phoenix_audit\.honored' docs/header-convention.md
# Also anchor the attribute in architecture.md (HIGH-2 from round-1 silent-failure).
assert_grep 'phoenix_audit\.honored' docs/architecture.md
honored_canonical=$(grep_count 'phoenix_audit\.honored' docs/header-convention.md)
test "$honored_canonical" -ge 8 \
  || fail "header-convention.md has only $honored_canonical 'phoenix_audit.honored' occurrences (expected ≥8 — partial-drift suspected)"
# Anti-anchor: refuse typo/case variants of the attribute name.
# grep -c exits 1 on zero matches; || true so set -e doesn't kill the script
# (the count of 0 is the desired clean state).
honored_drift=$(grep -cE 'phoenix-audit\.honored|phoenixAudit\.honored|phoenix_audit_honored|phoenix\.audit\.honored' docs/header-convention.md || true)
test "$honored_drift" -eq 0 \
  || fail "header-convention.md contains $honored_drift typo/drift variant(s) of phoenix_audit.honored"
# Warning text for audit report when target doesn't honor — round-1 MED-2:
# the phrase MUST appear in BOTH the human blockquote AND the fenced
# canonical fixture (drift between human-doc and machine-lock goes uncaught
# if we only assert ≥1).
assert_grep_at_least "Target did not signal it honored" docs/header-convention.md 2
# Honest disclaimer that headers are advisory, not enforced
assert_grep "advisory" docs/header-convention.md
# Downstream test obligations section (Epic 4 injector + Epic 3 targets)
assert_grep "Downstream test obligations" docs/header-convention.md
assert_grep "Epic 4 injector" docs/header-convention.md
assert_grep "Epic 3" docs/header-convention.md
pass "header-convention.md declares schema + acknowledgment (count≥8, escaped, no typo/drift, cross-file) + warning (≥2 occurrences) + downstream obligations"

# -- Cited OSS-tool punt comparison preserves D4-8 cite-and-verify discipline -
# The ADR cites memo 27's OSS comparison: Promptfoo, Garak, DeepTeam all punt;
# AIR/MS-AGT solve at the defender side. The schema doc must list these by
# name so future readers can trace the empirical claim.
assert_grep "Promptfoo" docs/header-convention.md
assert_grep "Garak" docs/header-convention.md
assert_grep "DeepTeam" docs/header-convention.md
# Round-1 test-analyzer negative-space gap #2: anchor the "punt" framing
# (not just the tool name) — a future PR could silently rewrite cells.
assert_grep "punt" docs/header-convention.md
# AIR Blackbox + MS AGT framed as defender-side, not auditor-side.
assert_grep "AIR Blackbox" docs/header-convention.md
assert_grep "Microsoft.*Agent Governance|MS AGT" docs/header-convention.md
# Round-1 comment-analyzer LOW-1: Inspect AI listed in table — should also
# be in summary prose for consistency.
assert_grep "Inspect AI" docs/header-convention.md
# The memo's claim is empirically traceable.
# Round-1 silent-failure LOW: anchor on header form (^## Sub-question 5)
# to prevent substring matches in cross-reference prose.
assert_grep '^## Sub-question 5' research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md
pass "OSS-tool punt landscape cited honestly (incl. Inspect AI + punt framing) + memo 27 Sub-question 5 header anchor verified"

# -- Header schema declares value formats + UUID generation point -------------
# X-Phoenix-Audit: literal "true" (no other value).
assert_grep '`true` \(literal\)' docs/header-convention.md
# Run-Id: UUIDv4 — same value Phoenix Audit's orchestrator generates server-side
# (per run-config-schema.md's audit_run_id field).
assert_grep "UUIDv4" docs/header-convention.md
assert_grep "audit_run_id" docs/header-convention.md
# Dry-Run: two-value enum (true|false). Round-1 test-analyzer MED-1:
# tighten the lock — anchor on "Two-value enum" framing + anti-anchor
# any third-value drift (auto/default/maybe/off/partial/skip).
assert_grep "Two-value enum" docs/header-convention.md
set +o pipefail
enum_drift=$(grep -iE 'X-Phoenix-Audit-Dry-Run.*\b(auto|default|maybe|off|partial|skip)\b' docs/header-convention.md | wc -l | tr -d ' ' || true)
set -o pipefail
test "$enum_drift" -eq 0 \
  || fail "X-Phoenix-Audit-Dry-Run enum drifted ($enum_drift line(s) suggesting auto/default/maybe/off/partial) — ADR-015 locks to true|false"
pass "Header values precisely specified (X-Phoenix-Audit=true literal, Run-Id=UUIDv4, Dry-Run two-value enum locked + drift anti-anchored)"

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
# Round-1 silent-failure MEDIUM: TBD-19 row-shape anchor (mirror of
# Patch #20's TBD-18 anchor). The substring `TBD-19` alone matches prose
# anywhere; the row-shape regex enforces the actual table row exists.
# Prettier-tolerant: allow 1+ spaces before closing pipe.
assert_grep '^\| \(TBD-19\) +\|' docs/audit-notes.md
pass "ADR-015 cleanly takes the next number; ADR-014 reservation tracked; TBD-19 row-shape anchored"

# -- Honest threat-model disclosure: headers are NOT cryptographic ------------
# Similar to how ADR-013 honestly disclosed namespace-only vs HMAC. The
# header convention is advisory; a malicious target could echo the
# acknowledgment attribute without actually honoring. Spec must say so.
assert_grep "advisory, not enforced" docs/header-convention.md
# Round-3 silent-failure-hunter + test-analyzer: closed-vocabulary
# anti-anchor regex is structurally flawed (each round adds N synonyms,
# reviewers find M more). Switching to BYTE-LOCK the canonical threat-
# model claims — same discipline as the warning fixture above. Any reword
# of the load-bearing claims fails the gate; only ADDING contradictory
# claims elsewhere needs the regex coarse-filter (which we keep below).
IFS= read -r -d '' THREAT_MODEL_INTRO <<'EOF' || true
The header convention is **advisory, not enforced.** Specifically:
EOF
THREAT_MODEL_INTRO="${THREAT_MODEL_INTRO%$'\n'}"
assert_block_present "$THREAT_MODEL_INTRO" docs/header-convention.md 50
IFS= read -r -d '' THREAT_CLAIM_1 <<'EOF' || true
1. **A target that ignores the headers still executes side-effecting tools.**
   The headers don't prevent execution; they only request the target opt into
   dry-run. The audit-report warning above is the visible signal when a
   target didn't opt in.
EOF
THREAT_CLAIM_1="${THREAT_CLAIM_1%$'\n'}"
assert_block_present "$THREAT_CLAIM_1" docs/header-convention.md
IFS= read -r -d '' THREAT_CLAIM_2 <<'EOF' || true
2. **The acknowledgment attribute (`phoenix_audit.honored = true`) is
   self-reported by the target.** A malicious target could emit the attribute
   without actually short-circuiting its side-effecting tools.
EOF
THREAT_CLAIM_2="${THREAT_CLAIM_2%$'\n'}"
assert_block_present "$THREAT_CLAIM_2" docs/header-convention.md
IFS= read -r -d '' THREAT_CLAIM_3 <<'EOF' || true
3. **Run-Id is not cryptographically bound.** A malicious target could log
   or replay the Run-Id outside the audit window.
EOF
THREAT_CLAIM_3="${THREAT_CLAIM_3%$'\n'}"
assert_block_present "$THREAT_CLAIM_3" docs/header-convention.md 50
# Round-1 test-analyzer HIGH-1 + negative-space gap #4: anti-anchor against
# any silent strengthening of the disclosure. Match lines making cryptographic
# / enforcement / guaranteed claims, THEN strip lines that are:
#  - negative disclaimers ("NOT cryptographically bound" — disclosing the
#    absence of cryptographic enforcement)
#  - explicit deferral framing (TBD-19 / post-hackathon / future / deferred
#    / out of scope)
#  - the immediate neighborhood of TBD-19's paragraph (look 2 lines forward
#    via grep -A1 around any TBD-19/post-hackathon mention)
set +o pipefail
deferral_lines=$(grep -nE 'TBD-19|post-hackathon|out of scope|deferred' docs/header-convention.md \
  | cut -d: -f1 \
  | awk '{print $1; print $1+1; print $1+2; print $1+3; print $1+4}' \
  | sort -un)
strengthening_bad=$(grep -niE '(cryptograph[a-z]*\s+(bound|verified|prevented|prevents|enforced|enforces|tight|secure|secures|bind|binds|block|blocks|guarantee|guarantees|sign|signs|authenticate[d]?)|tamper-proof|enforced\s+via\s+crypt|guaranteed\s+(to\s+)?(prevent|short-circuit|block)|(MANDATES?|REQUIRES?|DICTATES?|COMPELS?|IMPOSES?)\s+(that|all|every|each|the\s+target)|(non-negotiable|non-optional|contractually\s+enforced|binding\s+(on|for|requirement)|contractually\s+obligated|hard\s+requirement|unbreakable|inviolable|enforceable|COMPULSORY|OBLIGATORY)\s*(target|requirement|implementation|under)?|(headers?|targets?)\s+(prevent|block|prohibit|stop|halt|preclude|enforce)s?\s+(side\s*-?\s*effect|the\s+target)|(headers?|convention|run-id|attribute)\s+(will\s+be|shall\s+be)?\s*(enforced|honored\s+as|mandatory|required\s+via)|shall\s+(stop|block|prevent|prohibit|enforce|halt)|will\s+be\s+(implemented|enforced|blocked|honored|cryptographically)|will\s+ship|cannot\s+proceed\s+without|Failure\s+to\s+honor\s+results\s+in)' docs/header-convention.md \
  | grep -ivE '(not cryptograph|NOT cryptograph)' \
  | while IFS= read -r line; do
      ln=$(echo "$line" | cut -d: -f1)
      if ! echo "$deferral_lines" | grep -qx "$ln"; then
        echo "$line"
      fi
    done \
  | wc -l | tr -d ' ' || true)
set -o pipefail
test "$strengthening_bad" -eq 0 \
  || fail "header-convention.md contains $strengthening_bad strengthening claim(s) outside the deferral context — headers are advisory, not enforced (ADR-015)"
# HMAC deferral tracked separately (matches the Patch #20 TBD-18 pattern).
assert_grep "TBD-19|post-hackathon" docs/header-convention.md
pass "Threat model honestly disclosed: headers advisory; cryptographic binding deferred; strengthening claims anti-anchored"

# -- Run-Id correlation: header value MUST match run-config audit_run_id ------
# This is the load-bearing claim — the headers' Run-Id and the run-config's
# audit_run_id are the same UUID, so Phoenix Audit can correlate probes to
# the audit run on the target side.
# Round-1 test-analyzer MED-3: bounded wildcard so a future PR can't
# satisfy this with "MUST match the docstring; the audit_run_id field
# is separately defined".
assert_grep 'MUST match.{0,40}audit_run_id|same UUID|identical to' docs/header-convention.md
# Cross-reference run-config schema.
assert_grep "run-config-schema.md" docs/header-convention.md
# Round-1 test-analyzer negative-space gap #1: cross-reference ADR-013's
# `phoenix_audit.*` namespace so the namespace-consistency story across
# patches #19/#20 doesn't fragment silently.
assert_grep "mirrors ADR-013" docs/header-convention.md
pass "Header Run-Id locked to match run-config audit_run_id; ADR-013 namespace cross-ref anchored"

# -- Report warning text is locked verbatim against a HARDCODED literal -------
# Round-2 silent-failure HIGH-B: previous version extracted the fixture
# from the doc and asserted "it's in the doc" — tautological. Replaced
# with a hardcoded canonical literal in this test script; any byte-drift
# in the doc fails the gate loud. This is the actual Patch #20 discipline
# (Patch #20's cover paragraph was hardcoded in the test script too).
IFS= read -r -d '' CANONICAL_WARNING <<'EOF' || true
Target did not signal it honored the X-Phoenix-Audit-* headers (`phoenix_audit.honored = true` was absent from {N} probe-response spans). Side-effecting tool calls during this audit run MAY have been executed for real against the target. To opt into dry-run behavior, the target must read `X-Phoenix-Audit-Dry-Run` and short-circuit side-effecting tools when its value is `true`, AND emit `phoenix_audit.honored = true` as a span attribute on every response.
EOF
# Strip the trailing newline read -d '' leaves on the buffer.
CANONICAL_WARNING="${CANONICAL_WARNING%$'\n'}"
# Defensive: catastrophic-parse-failure floor.
[ "${#CANONICAL_WARNING}" -ge 400 ] \
  || fail "CANONICAL_WARNING heredoc parsed to ${#CANONICAL_WARNING} chars (expected ≥400); heredoc parse failure suspected"
fenced_text_count=$(grep_count '^```text$' docs/header-convention.md)
test "$fenced_text_count" -eq 1 \
  || fail "header-convention.md has $fenced_text_count fenced \`\`\`text blocks (expected exactly 1 — the warning fixture)"
# REAL byte-identical lock: assert the canonical literal (defined in THIS
# test script) appears verbatim in the doc. Any drift in the doc fails.
assert_block_present "$CANONICAL_WARNING" docs/header-convention.md
# Round-1 test-analyzer negative-space gap #3: ensure exactly ONE {N}
# placeholder AND no other placeholders co-existing (round-2 MED-B).
n_placeholder_count=$(echo "$CANONICAL_WARNING" | grep -oE '\{N\}' | wc -l | tr -d ' ' || true)
total_placeholders=$(echo "$CANONICAL_WARNING" | grep -oE '\{[^}]+\}' | wc -l | tr -d ' ' || true)
test "$n_placeholder_count" -eq 1 \
  || fail "canonical warning has $n_placeholder_count \`{N}\` placeholders (expected exactly 1)"
test "$total_placeholders" -eq 1 \
  || fail "canonical warning has $total_placeholders {…} placeholders (expected exactly 1 — only {N}); other placeholders forbidden"
# Round-1 test-analyzer MED-2: anti-anchor named weakenings that
# would gut the verbatim lock from elsewhere in the doc.
# Round-2 test-analyzer MED-4: broader vocabulary (customer-language /
# nationally-appropriate / equivalent-message / localized-form variants).
assert_no_grep '(paraphrased|softened|abbreviated|MAY include a (shorter|alternate)|customer language of choice|nationally appropriate wording|equivalent message|localized form|alternate phrasing|reference implementation, not a hard requirement)' docs/header-convention.md
assert_no_grep 'translation.equivalent' docs/header-convention.md
# Positive: the rationale that explains WHY verbatim must survive.
assert_grep 'same lock-discipline as the Patch #20 cover paragraph' docs/header-convention.md
pass "Report-warning text locked VERBATIM via HARDCODED canonical literal (byte-drift in doc now fails loud; single fenced block; exactly 1 {N} + no other placeholders; named weakenings anti-anchored broader vocabulary)"

# -- Downstream-obligation anchors INSIDE the section, not file-wide ---------
# Round-2 test-analyzer HIGH-2: previous version asserted presence anywhere
# in the file — moving the strings to "## Appendix: misc strings" defeated
# the gate. Now extract the Downstream-obligations SECTION (start at
# `^## Downstream test obligations`, stop at the next H2) and assert the
# anchors INSIDE that section only.
DOWNSTREAM_SECTION=$(awk '/^## Downstream test obligations/{flag=1} flag && /^## / && !/^## Downstream/{exit} flag' docs/header-convention.md)
[ "${#DOWNSTREAM_SECTION}" -ge 500 ] \
  || fail "Downstream-obligations section extracted to ${#DOWNSTREAM_SECTION} chars (expected ≥500) — section missing/gutted"
# Write extracted section to a temp file so we can grep against it.
DOWNSTREAM_TMPFILE=$(mktemp)
echo "$DOWNSTREAM_SECTION" >"$DOWNSTREAM_TMPFILE"
# Round-3 LOW: quote the trap body to avoid premature expansion + clobber.
trap 'rm -f "$DOWNSTREAM_TMPFILE"' EXIT
# Epic 4 injector: three headers + refuse-on-missing semantic. INSIDE section.
assert_grep 'X-Phoenix-Audit: true' "$DOWNSTREAM_TMPFILE"
assert_grep 'X-Phoenix-Audit-Run-Id' "$DOWNSTREAM_TMPFILE"
assert_grep 'X-Phoenix-Audit-Dry-Run' "$DOWNSTREAM_TMPFILE"
# Epic 6 Reporter byte-identical lock + {N}-only-placeholder refuse. INSIDE section.
assert_grep 'byte-identical' "$DOWNSTREAM_TMPFILE"
assert_grep 'refuse to substitute any placeholder other than `\{N\}`' "$DOWNSTREAM_TMPFILE"
# Section presence (anchor on the actual header too).
assert_grep '^## Downstream test obligations' docs/header-convention.md
# Round-2 test-analyzer MED-7: anchor the BOOLEAN attribute kind discipline
# the doc explicitly says is load-bearing for Epic 3/6 type-mismatch
# prevention. Anchor on both the AttributeValue.bool_value technical name
# AND the BOOLEAN human-readable form.
assert_grep 'AttributeValue\.bool_value' docs/header-convention.md
assert_grep 'BOOLEAN' docs/header-convention.md
pass "Downstream obligations section-scoped: Epic 4 three headers + Epic 6 byte-identical + {N}-only refuse + BOOLEAN attribute kind anchored"

# -- 400-line guard -----------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean"

# -- §14: no mocks introduced (this patch is spec-only — no src/ changes) -----
# Round-1 silent-failure HIGH-2: drop the `test -d ... &&` conditional that
# silently skipped coverage. Mirror Patch #20: unconditional SCAN_DIRS so
# deletion of either dir fails the test loud via assert_dir inside the helper.
SCAN_DIRS=(apps/target-agent/src apps/phoenix-audit-agent/src)
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
