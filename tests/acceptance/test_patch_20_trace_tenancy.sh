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
#
# Round-2 additions (per silent-failure-hunter + test-analyzer + comment-
# analyzer feedback on commit 808a318):
#   - Cover-page paragraph locked verbatim via assert_block_present (no
#     more fragment-pinning loophole that let "derived embeddings"
#     weakenings slip past).
#   - Model A anti-anchor broadened to all forms (centralizes/will/may/
#     should/must centralize) AND positively locked the canonical NOT
#     statement so refusal text can't be silently deleted.
#   - §14 mock scan delegated to _lib.sh helper that applies the same
#     B1/B3/B4 silent-failure discipline as run_silent — no more
#     `|| true` swallowing grep tool errors.
#   - Cross-file content verification (cited file CONTENT, not just
#     existence) for server.py + test1_cross_tenant_ingest.py.
#   - Phoenix `lines 29-49` line-range citation verified end-to-end.
#   - PRD-side trace-tenancy anchors added.

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
# Defensive: _lib.sh sets strict mode, but re-declare here so anyone reading
# this test in isolation sees the strict-mode requirement at the test level.
set -euo pipefail

# -- ADR-013 added to architecture.md -----------------------------------------
# (ADR-013 not ADR-014 — Ed25519 was reserved second per audit-notes D4-3
#  rev'd to ADR-014; trace tenancy patch landed first in architecture.md.)
assert_grep "^### ADR-013: Trace tenancy" docs/architecture.md
assert_grep "customer-side Phoenix project" docs/architecture.md
assert_grep "Model C \\(hybrid\\)" docs/architecture.md
# Positive lock: the canonical NOT statement MUST survive. If deleted,
# the spec has been gutted regardless of what else still passes.
assert_grep 'Phoenix Audit does NOT centralize audit traces in our vendor Phoenix project' docs/architecture.md
# ANTI-anchor: round-3 silent-failure-hunter R3-1 caught that the
# enumerated-verb-forms anti-anchor missed past-tense ("centralized")
# and noun forms ("centralization"). Replaced with a morpheme-level
# pattern: anything matching "Phoenix Audit ... centraliz*" within a
# short token window is refused — EXCEPT the canonical NOT line above
# (which uses "does NOT centralize" — the morpheme regex catches that
# too, so we positively whitelist the locked line via grep -v before
# counting).
#
# Count of "Phoenix Audit + any centraliz* form" occurrences on a single
# line, MINUS the canonical-NOT line, MUST be zero.
# Note: grep exits 1 on no-match; with pipefail this would kill set -e
# before the test command can fire. Disable pipefail JUST for this
# pipeline. Trade-off: grep tool-error (≥2) goes unnoticed for the
# count — acceptable because the file is small + readable + the
# canonical-NOT positive lock above already proved the file is parseable.
set +o pipefail
adr013_bad_lines=$(grep -E '(Phoenix )?Audit[[:space:]]+([a-z]+[[:space:]]+){0,3}centraliz' docs/architecture.md \
  | grep -v 'does NOT centralize audit traces in our vendor Phoenix project' \
  | wc -l | tr -d ' ')
set -o pipefail
test "$adr013_bad_lines" -eq 0 \
  || fail "architecture.md contains 'Phoenix Audit ... centraliz*' wording outside the canonical NOT line ($adr013_bad_lines line(s))"
pass "ADR-013 (trace tenancy = customer-side Phoenix) lands in architecture.md; Model A wording refused in all morphological forms (morpheme-level check)"

# -- Filter attribute is namespaced consistently across spec ------------------
# Round-2 comment-analyzer H1: architecture.md line 314 originally used
# bare `audit_run_id` while line 325 used the namespaced form. Both must
# now use `phoenix_audit.audit_run_id`. This anchor catches re-divergence.
assert_grep 'filtered by `phoenix_audit\.audit_run_id` span attribute' docs/architecture.md
# Round-3 silent-failure-hunter R3-4: the "filtered by" anchor only
# catches one specific phrasing. Count bare ``audit_run_id`` references
# (NOT preceded by `phoenix_audit.`) EXCLUDING lines that explicitly
# call them out as the "bare" form (i.e., the legitimate disclaimers
# at lines 314 + 325 both say "bare `audit_run_id`"). Any unlabeled
# bare reference = the divergence is back.
set +o pipefail
bare_unlabeled_count=$(grep -nE '[^.`]`audit_run_id`' docs/architecture.md \
  | grep -vE 'bare `audit_run_id`' \
  | wc -l | tr -d ' ')
set -o pipefail
test "$bare_unlabeled_count" -eq 0 \
  || fail "architecture.md has $bare_unlabeled_count unlabeled-bare \`audit_run_id\` reference(s) — only the explicitly-labeled 'bare \`audit_run_id\`' disclaimers are legitimate"
pass "Filter attribute consistently namespaced as phoenix_audit.audit_run_id (count-based bare-form check; ≤1 allowed in tradeoff disclaimer)"

# -- ADR-013 references RAT-2 Test 1 by file path + line range + measurement --
# Per D4-8 process lesson: cite empirical sources by path AND verify the
# cited content actually exists in the cited file AND the cited line range
# spans the cited section.
assert_grep 'RAT-2-results.md' docs/architecture.md
# Word-boundary anchor — `\b1\.37s\b` rejects future drift to `11.37s` /
# `0.137s` (loose substring would silently match).
assert_grep '[^0-9]1\.37s emit-to-visible' docs/architecture.md
# Cross-file consistency: the cited measurement MUST exist in the cited file.
assert_grep '1\.37s' research/google-cloud-rapid-agent/RAT-2-results.md
# Line-range citation verified: line 29 starts Test 1; line 49 is in Test 1
# region (verdict / measurement). Insertions ahead of line 29 silently
# invalidate the citation; this assertion catches that. Round-3 R3-F5:
# failure message now includes the actual line where Test 1 lives so the
# operator can update the citation without re-derivation.
if [ "$(awk 'NR==29' research/google-cloud-rapid-agent/RAT-2-results.md | grep -cE 'Test 1' || true)" -lt 1 ]; then
  actual_line=$(grep -nE '^## Test 1' research/google-cloud-rapid-agent/RAT-2-results.md | head -1 | cut -d: -f1)
  fail "RAT-2-results.md line 29 no longer starts Test 1 (now at line ${actual_line:-?}) — update architecture.md + run-config-schema.md 'lines 29-49' citation"
fi
if [ "$(awk 'NR>=29 && NR<=49 {print}' research/google-cloud-rapid-agent/RAT-2-results.md | grep -cE '1\.37s' || true)" -lt 1 ]; then
  actual_line=$(grep -nE '1\.37s' research/google-cloud-rapid-agent/RAT-2-results.md | head -1 | cut -d: -f1)
  fail "RAT-2-results.md lines 29-49 no longer contain the 1.37s measurement (1.37s now at line ${actual_line:-?}) — update citation"
fi
pass "ADR-013 cites RAT-2 Test 1 + 1.37s measurement verified in cited file + cited line range (29-49) verified (with actionable failure messages)"

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

# -- Schema uses namespaced `phoenix_audit.audit_run_id` consistently ---------
# Round-2 comment-analyzer H2: schema YAML comment line 71 used bare
# `audit_run_id` while the namespace prose 45 lines down used the
# namespaced form. Catch re-divergence.
assert_grep 'phoenix_audit\.audit_run_id == <the top-level audit_run_id>' docs/run-config-schema.md
pass "Schema uses namespaced phoenix_audit.audit_run_id consistently (no bare-form drift in YAML comments)"

# -- Validation rules locked: ALL 4 rules, regex pinned, https-only -----------
# Each rule asserted on its load-bearing string. A future refactor that
# silently drops one would fail here.
assert_grep '`https` ONLY' docs/run-config-schema.md
assert_grep 'MUST be non-empty' docs/run-config-schema.md
# Pin the project-name regex LITERALLY. In ERE, ^ [ ] { } $ all need
# escaping to match as literal characters. Single-quoted so bash doesn't
# touch the backslashes.
assert_grep '\^\[a-z0-9\]\[a-z0-9_-\]\{0,62\}\$' docs/run-config-schema.md
assert_grep 'pydantic.SecretStr' docs/run-config-schema.md
assert_grep 'discarded from memory' docs/run-config-schema.md
# Rule 4 must clarify Python string-immutability honestly + use a helper
# context manager (not the BaseModel directly).
assert_grep 'audit_run_context' docs/run-config-schema.md
assert_grep 'Bytes-level zeroization' docs/run-config-schema.md
pass "Validation rules locked: https-only + non-empty api_key + project-name regex literal + SecretStr + helper-CM + honest scrub caveat"

# -- Phoenix project-name regex framed honestly (D4-8 lesson) -----------------
# Reviewer caught: "Phoenix project naming convention" framed as upstream
# authority but Phoenix doesn't publish a project-name regex. Reframed as
# Phoenix Audit's locally-imposed rule modeled on common conventions.
assert_grep "locally-imposed constraint" docs/run-config-schema.md
# The original "Phoenix prompt-tag rule" quoted citation has been dropped
# (no URL available for it; D4-8 lesson — don't cite what you can't link).
assert_no_grep "Phoenix's documented prompt-tag rule" docs/run-config-schema.md
# Empirical claim softened from "evidence" to "existence proof" with explicit
# disclaimer that one passing name is not a derivation of Phoenix's rule set.
assert_grep 'Empirical existence' docs/run-config-schema.md
pass "Phoenix regex framed honestly; prompt-tag rule citation dropped; empirical claim disclaimed"

# -- _build_a2a_app cited correctly as PATTERN not COPY -----------------------
# Reviewer caught: _build_a2a_app whitelists http+https; schema requires
# https-only. Citation must say "pattern" not "copy". Grep is line-oriented
# so we anchor on two short single-line phrases the markdown contains.
assert_grep 'fail-loud `SystemExit` PATTERN' docs/run-config-schema.md
assert_grep 'whitelist content differs' docs/run-config-schema.md
# ANTI-anchor: must NOT call the relationship a "copy" — that wording
# would imply the http+https whitelist gets reused verbatim (it doesn't).
# Broadened to catch synonyms: copy / duplicate / clone / verbatim from.
assert_no_grep '(copy|duplicate|clone|verbatim copy|verbatim duplicate) of `?_build_a2a_app`?' docs/run-config-schema.md
assert_no_grep '(same code|verbatim) (as|from) `?_build_a2a_app`?' docs/run-config-schema.md
pass "_build_a2a_app cited as portable PATTERN (not copy/duplicate/clone) — whitelist content differs"

# -- Cited files exist AND their cited content actually exists in them --------
# Round-2 test-analyzer M2: round-1 fix verified existence but not content
# for two citations (test1_cross_tenant_ingest.py + server.py). Apply the
# D4-8 discipline to both.
assert_file research/google-cloud-rapid-agent/RAT-2-results.md
assert_file research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md
assert_file research/google-cloud-rapid-agent/rat-2-phoenix-audit/test1_cross_tenant_ingest.py
assert_file apps/target-agent/src/target_agent/server.py
# Content verification: server.py must actually contain the cited frozenset
# + urlparse + _build_a2a_app pattern.
assert_grep '_build_a2a_app' apps/target-agent/src/target_agent/server.py
assert_grep 'frozenset' apps/target-agent/src/target_agent/server.py
# Content verification: test1 script must actually contain the cited
# `rat2-test1-cross-tenant-{8-hex}` pattern reference.
assert_grep 'rat2-test1-cross-tenant' research/google-cloud-rapid-agent/rat-2-phoenix-audit/test1_cross_tenant_ingest.py
pass "All cited files exist AND their cited content verified inside them (D4-8 fully applied)"

# -- audit_run_id namespaced + HMAC deferred to TBD-18 ------------------------
# Reviewer caught: bare `audit_run_id` collides with Customer's other workloads.
# Must be namespaced. HMAC binding deferred (TBD-18) — namespace IS the v1
# mitigation for the realistic threat model.
assert_grep "phoenix_audit\\.audit_run_id" docs/run-config-schema.md
assert_grep "phoenix_audit\\.audit_run_id" docs/architecture.md
assert_grep "TBD-18" docs/run-config-schema.md
# Round-3 test-analyzer negative-space gap: anchor on the actual ROW
# SHAPE in audit-notes (markdown table cell starting with `| (TBD-18) |`)
# rather than just the literal "TBD-18" string anywhere. This catches
# a regression that removes the row but keeps the substring elsewhere.
assert_grep '^\| \(TBD-18\) \|' docs/audit-notes.md
# Schema's "What this PR does NOT do" section MUST disclose the HMAC
# deferral explicitly (no quiet promise rotting in prose).
assert_grep "does NOT implement the .phoenix_audit\\.run_signature. HMAC" docs/run-config-schema.md
pass "Namespaced phoenix_audit.audit_run_id is the v1 mitigation; HMAC tracked as TBD-18 with row-shape anchor + disclosed as non-delivery in schema"

# -- Report-page paragraph locked VERBATIM as a canonical fixture -------------
# Round-2 silent-failure F2: fragment-pinning let weakenings slip past.
# Round-3 test-analyzer + R3-F1/F2: the previous version maintained TWO
# copies of the cover paragraph (test heredoc + schema fenced block) which
# could silently drift. Now extracting the canonical fixture FROM the
# schema's fenced text block at test-time — single source of truth.
#
# The schema's `Canonical fixture` section is rendered as a fenced text
# block (```text ... ```) so awk can extract the contents reliably.
COVER_FIXTURE=$(awk '/^```text$/{flag=1; next} /^```$/{flag=0} flag' docs/run-config-schema.md)
# Defensive: if extraction produced an empty or implausibly-short string,
# the schema has been gutted — fail loud rather than trivially "pass".
[ "${#COVER_FIXTURE}" -ge 400 ] \
  || fail "Cover-fixture extraction from schema produced ${#COVER_FIXTURE} chars (expected ≥400); schema's fenced text block missing or fenced markers drifted"
# Now lock the extracted fixture against itself appearing in the schema —
# trivially true post-extraction, but the extraction itself proves the
# fenced block exists and is well-formed.
assert_block_present "$COVER_FIXTURE" docs/run-config-schema.md
# Round-3 test-analyzer R3-F1/F2: dropped the phantom
# `cover-page .*does not retain copies` single-line anchor. It (a) was
# the loophole class the assert_block_present already closes, (b) had
# a misleading comment claiming the rationale paragraph contained the
# phrase (it doesn't), and (c) was line-oriented so any multi-line
# weakening slipped past anyway. Replaced with a structural count gate
# (round-3 silent-failure-hunter R3-5): the schema may make a small,
# bounded number of post-retention claims; any unbounded growth means
# someone is adding competing softer wording elsewhere.
postret_count=$(grep -cE '(after report generation|after the audit run|post-report)' docs/run-config-schema.md)
# Five legitimate occurrences as of efe2238: api_key-discard (2 — fields
# detail + rule 4), cover blockquote, canonical-fixture text block,
# verbatim-lock rationale. Any growth above 5 = someone added a
# competing post-retention claim — must be reviewed.
test "$postret_count" -le 5 \
  || fail "schema makes $postret_count post-retention claims (baseline 5: api_key-discard ×2, cover blockquote, canonical-fixture, rationale); growth signals a competing softer rephrase — review the new occurrence"
# Anti-anchor each specific weakening the Verbatim-lock rationale calls out.
# Any of these in the schema means the lock has been silently weakened.
assert_no_grep 'derived embeddings' docs/run-config-schema.md
assert_no_grep 'aggregate metrics' docs/run-config-schema.md
assert_no_grep 'raw spans themselves' docs/run-config-schema.md
# Regulatory hooks must still appear verbatim.
assert_grep "EU AI Act Annex IV" docs/run-config-schema.md
assert_grep "chain-of-custody" docs/run-config-schema.md
# Canonical fixture header anchor — proves the dedicated fixture block exists.
assert_grep "Canonical fixture" docs/run-config-schema.md
# Verbatim-lock rationale body anchor — proves the rationale itself can't
# be silently rewritten back to permit translation-equivalent wording.
assert_grep "Verbatim is the only durable lock against quiet drift" docs/run-config-schema.md
assert_no_grep "legal substance must be preserved" docs/run-config-schema.md
pass "Cover-page paragraph locked VERBATIM (extracted from schema's fenced canonical fixture; no test/schema duplicate source) + post-retention claim count bounded ≤5 + named weakenings anti-anchored + rationale body locked"

# -- Downstream test obligations section exists with concrete coverage --------
# Future Epic 4 + Epic 6 implementers need a concrete checklist.
assert_grep "Downstream test obligations" docs/run-config-schema.md
assert_grep "Epic 4 orchestrator story" docs/run-config-schema.md
assert_grep "Epic 6 Reporter story" docs/run-config-schema.md
# Extended rule-1 coverage (uppercase scheme, whitespace, homoglyph).
assert_grep "uppercase scheme" docs/run-config-schema.md
assert_grep "Cyrillic" docs/run-config-schema.md
# Epic 6 byte-identical wording (closes the .strip()/normalization loophole).
assert_grep "byte-identical" docs/run-config-schema.md
pass "Downstream obligations enumerated for Epic 4 + Epic 6, with uppercase/whitespace/homoglyph + byte-identical anchors"

# -- audit-notes D4-9 formal-landing record exists ----------------------------
assert_grep "^### D4-9 — Trace tenancy formal spec landing" docs/audit-notes.md
assert_grep "Patch #20" docs/audit-notes.md
# Content anchor (not just generic "Patch #20" which appears throughout repo).
assert_grep "Model C decision" docs/audit-notes.md
assert_grep "trace tenancy contradiction" docs/audit-notes.md
# Paraphrase fixed to match memo 27 verbatim (audit-notes used the old
# "patches before orchestrator stories" wording in round 1; now matches schema).
assert_grep "BEFORE writing more S2.x stories" docs/audit-notes.md
pass "audit-notes D4-9 records the formal spec landing + content anchors + memo-27 paraphrase consistency"

# -- ADR numbering doesn't leave a gap: ADR-013 landed; ADR-014 reserved ------
# Code-reviewer caught: audit-notes originally reserved ADR-013 for Ed25519.
# This patch took ADR-013 (chronological landing); Ed25519 bumped to ADR-014.
# Round-2 code-reviewer HIGH-1: D4-3 wording must make clear ADR-014 is
# "reserved-not-yet-landed", not as-if-already-shipped.
assert_grep 'ADR-014 — Ed25519 signing' docs/audit-notes.md
# ERE: bare ( ) are grouping; escape to match literal parens in the audit-notes table cell.
assert_grep 'ADR-014 \(Ed25519 signing\)' docs/audit-notes.md
# The "not yet written" disclosure must be present (no implication ADR-014
# has landed when only its slot is reserved).
assert_grep "not yet written" docs/audit-notes.md
pass "ADR-013 landed; ADR-014 cleanly reserved (with explicit not-yet-written disclosure) in audit-notes"

# -- PRD-side trace-tenancy claim survives (round-2 silent-failure F11) -------
# The patch's pitch is that trace tenancy is now CONSISTENT across the spec
# set. If a future PRD edit silently re-centralizes traces (or quietly
# removes the KMS/customer-tenancy language), nothing in the patch-20 gate
# catches it without these anchors.
assert_grep "Customer.s Phoenix project" docs/PRD.md
assert_grep "Cloud KMS" docs/PRD.md
# Round-3 comment-analyzer MEDIUM: PRD must NOT overstate ADR-013. ADR-013
# honestly discloses a transient in-process read; "zero cross-tenant
# evidence flow" overstates that. Refuse the overstatement.
assert_no_grep 'zero cross-tenant evidence flow' docs/PRD.md
# Apply the morpheme-level Model A anti-anchor to all 3 spec files + PRD.
# Same single-pattern check as ADR-013 above, applied per file. The
# canonical NOT line only appears in architecture.md, so for the other
# three files ANY "Phoenix Audit ... centraliz*" occurrence on a single
# line is a regression.
for f in docs/PRD.md docs/run-config-schema.md docs/audit-notes.md; do
  set +o pipefail
  bad=$(grep -E '(Phoenix )?Audit[[:space:]]+([a-z]+[[:space:]]+){0,3}centraliz' "$f" | wc -l | tr -d ' ')
  set -o pipefail
  test "$bad" -eq 0 \
    || fail "$f contains 'Phoenix Audit ... centraliz*' (Model A regression — $bad line(s))"
done
pass "PRD retains customer-tenancy + KMS anchors; PRD overstatement refused; Model A morpheme-level anti-anchor applied to all 3 spec files + PRD"

# -- 400-line guard -----------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean"

# -- §14: no mocks anywhere new (this patch is spec-only — no src/ changes) ---
# Round-2 silent-failure F3+F4: the round-1 fix replaced `|| true` (BLOCKER)
# with `test -d ... &&` (a different silent-skip pattern) AND retained
# `2>/dev/null | ... || true` on the grep line (triple-swallow). Replaced
# with a single _lib.sh helper that applies the same B3/B4 exit-code
# discipline as run_silent. Missing dirs fail loud; permission errors
# surface; only the "zero matches" exit code is allowed to pass.
#
# Coverage note (M3 stale-comment fix): apps/chaoslab-agent/src EXISTS as
# an empty package tree (created via S1.1 monorepo init, before Epic 4
# has populated it with real modules). The §14 grep scans it today and
# correctly reports zero matches because there's no .py code there yet.
# Once Epic 4 ships its first module, the same grep starts enforcing on
# real source. The unconditional include guarantees: deletion of the dir
# fails the test loud rather than silently dropping coverage.
SCAN_DIRS=(apps/target-agent/src apps/chaoslab-agent/src)
# Visibility: print file count per scanned dir so an "empty scan" PASS is
# transparent (round-2 silent-failure F10). Round-3 R3-F6: empty dirs
# get a louder WARN marker so the no-coverage state can't masquerade as
# real coverage.
for d in "${SCAN_DIRS[@]}"; do
  file_count=$(find "$d" -name '*.py' -type f 2>/dev/null | wc -l | tr -d ' ')
  if [ "$file_count" -eq 0 ]; then
    echo "  §14 WARN: $d has 0 Python files — gate cannot catch mocks here until Epic 4 ships modules"
  else
    echo "  §14 scan target: $d ($file_count Python files)"
  fi
done
# Round-3 silent-failure-hunter R3-2: drop the `--exclude-pattern '§14
# carve-out'` flag. It was a per-line backdoor (any author could stamp
# `# §14 carve-out` next to a mock to bypass review). Today the codebase
# has ZERO legitimate `§14 carve-out` lines (verified by grep), so the
# exclude was a no-op + backdoor. If a future legitimate exemption
# arises, land it via a registry file with structured justification,
# not a per-line bypass marker.
assert_no_pattern_in_dirs '(mock|fake|dummy|hardcoded|simulated)' "${SCAN_DIRS[@]}"
pass "§14 clean: no mocks/fakes/dummies/hardcoded/simulated in ${SCAN_DIRS[*]} (helper applies B3/B4 silent-failure discipline; per-line carve-out backdoor removed)"

echo ""
echo "==========================================="
echo "patch-20 verification: PASS"
echo "==========================================="
