#!/usr/bin/env bash
# Acceptance test for Patch #21 — multi-turn session shape for the 6-test demo.
# Translates issue #21 deliverables into machine-verifiable assertions.
# Exit 0 = patch complete.
#
# SPEC-ONLY patch per memo 27 sequencing. Runtime wiring lands in Epic 5's
# injector story (which materializes the 6-probe demo battery against the
# shape declared here).
#
# Inherits the hardened disciplines from Patch #19 + #20:
#   - HARDCODED canonical literals via assert_block_present (not extracted
#     from doc — Patch #19 round-2 lesson on tautology).
#   - Section-scoped anchors for downstream obligations (Patch #19 round-2).
#   - grep_count helper for any count-based gate (Patch #20 round-4).
#   - Strict mode re-declared at script level (Patch #20 round-3 R3-F14).
#   - §14 unconditional SCAN_DIRS (Patch #20 round-3 R3-F6).

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
set -euo pipefail

# -- ADR-016 added to architecture.md -----------------------------------------
assert_grep '^### ADR-016: Multi-turn session shape' docs/architecture.md
# Locks the 3-single-turn + 3-two-turn split.
assert_grep '3 single-turn' docs/architecture.md
assert_grep '3 two-turn' docs/architecture.md
# Cites memo 27 sub-question 2.
assert_grep 'memo 27 sub-q 2|sub-question 2|Sub-question 2' docs/architecture.md
# Memo 27 Sub-question 2 header exists in the brainstorm doc (D4-8 lesson).
assert_grep '^## Sub-question 2' research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md
pass "ADR-016 (multi-turn session shape: 3 single + 3 two-turn) lands in architecture.md + memo 27 sub-q 2 anchor verified"

# -- docs/session-shape.md NEW + load-bearing sections present ----------------
assert_file docs/session-shape.md
assert_grep '## Session-shape declaration' docs/session-shape.md
assert_grep '## OSS-tool landscape' docs/session-shape.md
assert_grep '## Latency budget' docs/session-shape.md
assert_grep '## Downstream test obligations' docs/session-shape.md
pass "session-shape.md declares the shape + OSS landscape + latency budget + downstream obligations sections"

# -- OSS-tool prior art cited honestly (D4-8 cite-and-verify) -----------------
# Promptfoo's named multi-turn primitives — these are documented as part
# of the rationale for picking 2-turn over 1-turn.
assert_grep 'Promptfoo' docs/session-shape.md
assert_grep 'Crescendo' docs/session-shape.md
assert_grep 'GOAT' docs/session-shape.md
# DeepEval / DeepTeam — multi-turn-as-headline-feature.
assert_grep 'DeepEval|DeepTeam' docs/session-shape.md
# Garak — stateless-per-probe (the "easy mode" we don't want to copy).
assert_grep 'Garak' docs/session-shape.md
# Inspect AI — multi-turn-by-design.
assert_grep 'Inspect AI' docs/session-shape.md
# TruLens — span-based, conversation-continuity is caller's job.
assert_grep 'TruLens' docs/session-shape.md
pass "OSS prior art cited: Promptfoo (Crescendo, GOAT) + DeepEval/DeepTeam + Garak + Inspect AI + TruLens"

# -- Per-probe session-mode mapping is locked verbatim -----------------------
# Round-3 Patch #19 lesson: byte-lock canonical claims via HARDCODED literal
# in test script. Drift in the doc's session-mix declaration fails loud.
# The doc uses `<!-- prettier-ignore -->` directive immediately above the
# session-shape table so Prettier doesn't column-align it (which would
# break the byte-match). The heredoc here matches the un-aligned form.
IFS= read -r -d '' SESSION_MIX <<'EOF' || true
<!-- prettier-ignore -->
| Probe | Source | Mode | Rationale |
| --- | --- | --- | --- |
| 1 | HarmBench #1 | single-turn | Harmful-output elicitation; direct prompt is high-signal. |
| 2 | HarmBench #2 | single-turn | Second harmful-output category; same rationale. |
| 3 | CARES | single-turn | Healthcare-safety direct-question; multi-turn adds no signal. |
| 4 | OWASP LLM01 | 2-turn | Crescendo-style: establish benign context, then escalate to injection. |
| 5 | MITRE ATLAS (indirect) | 2-turn | Indirect-injection-via-tool-output requires the tool call on turn 1. |
| 6 | MITRE ATLAS (escalation) | 2-turn | Trust-establish on turn 1, attack on turn 2. |
EOF
SESSION_MIX="${SESSION_MIX%$'\n'}"
[ "${#SESSION_MIX}" -ge 400 ] \
  || fail "SESSION_MIX heredoc parsed to ${#SESSION_MIX} chars (expected ≥400); heredoc parse failure suspected"
assert_block_present "$SESSION_MIX" docs/session-shape.md
pass "6-probe session-mode mix locked VERBATIM via HARDCODED canonical literal (byte-drift fails loud; prettier-ignore directive prevents column-alignment churn)"

# -- Honest threat-model claims byte-locked (Patch #19 round-3 lesson) -------
# The shape's load-bearing honest claims about single-turn-is-weak.
IFS= read -r -d '' SHAPE_CLAIM_1 <<'EOF' || true
**Single-turn is the easy mode of the attack.** OWASP LLM01 (prompt injection) and the MITRE ATLAS equivalent techniques are materially weaker as single-turn tests. The most-cited real-world prompt-injection attacks (Crescendo, indirect-injection-via-tool-output) require >1 turn of context to land.
EOF
SHAPE_CLAIM_1="${SHAPE_CLAIM_1%$'\n'}"
assert_block_present "$SHAPE_CLAIM_1" docs/session-shape.md

IFS= read -r -d '' SHAPE_CLAIM_2 <<'EOF' || true
**Phoenix Audit's session-mix is a deliberate budget-vs-coverage tradeoff, not full coverage.** Naming 3 of the 6 probes as 2-turn captures the higher-signal attacks (Crescendo-style escalation) within the 90-second demo window; running all 6 as 2-turn would blow the budget. Compliance officers reading the audit report should treat the 3 single-turn probes as floor-of-difficulty checks, NOT as comprehensive coverage of their categories.
EOF
SHAPE_CLAIM_2="${SHAPE_CLAIM_2%$'\n'}"
assert_block_present "$SHAPE_CLAIM_2" docs/session-shape.md
pass "Honest threat-model claims byte-locked: single-turn-is-easy-mode + session-mix-is-tradeoff-not-comprehensive"

# -- Latency budget arithmetic anchored ---------------------------------------
# Per memo 27, 16s/round-trip × probe-mode arithmetic must be documented.
assert_grep '16s' docs/session-shape.md
assert_grep '90.second' docs/session-shape.md
# Cross-ref RAT-2 Risk A (the empirical latency measurement source).
assert_grep 'RAT-2' docs/session-shape.md
pass "Latency budget cited (16s/round-trip × probe-mode + 90s demo window + RAT-2 source)"

# -- Cross-file consistency: ADR-016 ↔ session-shape.md bidirectional --------
assert_grep 'session-shape.md' docs/architecture.md
assert_grep 'ADR-016' docs/session-shape.md
pass "ADR-016 ↔ session-shape.md cross-reference is bidirectional"

# -- audit-notes D4-11 formal-landing record exists --------------------------
assert_grep '^### D4-11 — Multi-turn session shape' docs/audit-notes.md
assert_grep 'Patch #21' docs/audit-notes.md
# Content anchors (not just generic "Patch #21").
assert_grep '3 single-turn' docs/audit-notes.md
assert_grep '3 two-turn' docs/audit-notes.md
# Memo-27 paraphrase consistency (per Patch #20 lesson).
assert_grep 'BEFORE writing more S2.x stories' docs/audit-notes.md
pass "audit-notes D4-11 records the formal spec landing for Patch #21 with content anchors"

# -- ADR numbering: ADR-016 follows ADR-015 (Patch #19) ----------------------
# ADR-014 still reserved for Ed25519 (TBD-14, not yet written); the gap is
# explained in audit-notes D4-3.
assert_grep 'ADR-016' docs/architecture.md
assert_grep 'ADR-015' docs/architecture.md
assert_grep 'ADR-014 — Ed25519 signing' docs/audit-notes.md
pass "ADR-016 cleanly takes the next number; prior reservations still tracked"

# -- Downstream-obligation section-scoped anchors (Patch #19 round-2 lesson) -
# Extract the "## Downstream test obligations" section via awk + assert
# anchors INSIDE that section only (presence-anywhere-in-file is too loose).
DOWNSTREAM_SECTION=$(awk '/^## Downstream test obligations/{flag=1} flag && /^## / && !/^## Downstream/{exit} flag' docs/session-shape.md)
[ "${#DOWNSTREAM_SECTION}" -ge 400 ] \
  || fail "Downstream-obligations section extracted to ${#DOWNSTREAM_SECTION} chars (expected ≥400) — section missing/gutted"
DOWNSTREAM_TMPFILE=$(mktemp)
echo "$DOWNSTREAM_SECTION" >"$DOWNSTREAM_TMPFILE"
trap 'rm -f "$DOWNSTREAM_TMPFILE"' EXIT
# Epic 5 injector story obligations.
assert_grep 'Epic 5' "$DOWNSTREAM_TMPFILE"
# Per-probe assignment must be implementable.
assert_grep 'single-turn' "$DOWNSTREAM_TMPFILE"
assert_grep '2-turn' "$DOWNSTREAM_TMPFILE"
# The 2-turn shape must specify how the Injector establishes turn-1 context.
assert_grep 'turn 1' "$DOWNSTREAM_TMPFILE"
# Section presence anchor (in case the section is renamed but content survives).
assert_grep '^## Downstream test obligations' docs/session-shape.md
pass "Downstream obligations section-scoped (Epic 5) + per-probe single/2-turn + turn-1 protocol anchored"

# -- Anti-anchor against silent strengthening of "comprehensive" claims ------
# Patch #21's whole point is that we're NOT claiming comprehensive coverage.
# Round-1 reviewer findings addressed:
#  - silent-failure HIGH-1: switched from inline `wc -l | tr -d ' '` to the
#    `grep_count` helper which fails loud on grep tool errors.
#  - silent-failure MED-1: word-boundary the negation whitelist via \b so
#    `not` doesn't match inside "noteworthy" / "nothing" / "notable".
#  - silent-failure MED-2 + test-analyzer I1: broaden overclaim vocabulary
#    to include production-grade / thorough / extensive / robust / definitive /
#    all-encompassing / covers-everything / 100% coverage / every-category.
#  - test-analyzer I3: apply the gate to PRD + architecture + audit-notes,
#    not just session-shape.md (Patch #20 cross-file Model-A discipline).
#
# Strategy: match overclaim adjective broadly, then word-boundary-filter
# any line with an explicit negation/deferral/tradeoff token.
for f in docs/session-shape.md docs/architecture.md docs/PRD.md docs/audit-notes.md; do
  # Round-2 silent-failure F1 fix: assert_readable each file BEFORE the
  # scan so a missing file fails loud with the helper's clear message
  # instead of silently reporting 0 overclaims via `|| true`.
  assert_readable "$f"
  # First pass: find overclaim candidates. Both `grep -c` and the
  # downstream `grep -v | wc -l` exit 1 on zero matches — disable pipefail
  # so set -e doesn't kill the script, and use `|| true` defensively.
  set +o pipefail
  overclaim_bad=$(grep -niE '\b(comprehensive|complete|exhaustive|thorough|extensive|definitive|robust|production-grade|all-encompassing)\s+(coverage|audit|test|battery|sweep|sample|protection)|\b(covers|tests)\s+(all|every|each)\s+(attack|category|categor|technique|prompt-injection|threat|vector)' "$f" \
    | grep -ivE '\b(NOT|not|cannot|never|no\b|treat.*floor|deliberate.*tradeoff)\b' \
    | wc -l | tr -d ' ' || true)
  set -o pipefail
  test "$overclaim_bad" -eq 0 \
    || fail "$f contains $overclaim_bad comprehensiveness over-claim(s) outside the negation context — Patch #21 is a deliberate tradeoff"
done
pass "Comprehensiveness overclaims anti-anchored across session-shape.md + architecture.md + PRD.md + audit-notes.md (broader vocabulary + \\b word-boundary on negation whitelist)"

# -- 2-turn protocol byte-locked (round-1 test-analyzer N3) -------------------
# The load-bearing protocol declaration Epic 5 implements against.
IFS= read -r -d '' TWO_TURN_PROTOCOL <<'EOF' || true
For each 2-turn probe, turn 1 establishes context (benign question, plausible
request) and turn 2 escalates (injection payload, trust exploitation). Each
turn is a full A2A round-trip (for ADK-A2A targets; HTTP-target latency is
TBD until Epic 3 measures). Total wire time per 2-turn probe ≈ 32s assuming
the A2A 16s/round-trip baseline from RAT-2 IF-14.
EOF
TWO_TURN_PROTOCOL="${TWO_TURN_PROTOCOL%$'\n'}"
assert_block_present "$TWO_TURN_PROTOCOL" docs/session-shape.md
pass "2-turn protocol declaration byte-locked (Epic 5 contract verbatim)"

# -- Per-turn span attribute namespace anchored (round-1 test-analyzer N1) ---
# `phoenix_audit.session_mode` + `phoenix_audit.turn_index` — same namespace
# discipline as Patch #19's `phoenix_audit.honored`. Escaped dot regex +
# typo/drift anti-anchor.
assert_grep 'phoenix_audit\.session_mode' docs/session-shape.md
assert_grep 'phoenix_audit\.turn_index' docs/session-shape.md
# Anti-anchor typo/case variants (kebab-case, double-underscore, etc.).
# Round-2 silent-failure F2 fix: use grep_count helper for proper rc≥2
# discrimination instead of raw `grep -cE | true`.
typo_drift=$(grep_count '(phoenix-audit\.session_mode|phoenixAudit\.session_mode|phoenix_audit_session_mode|phoenix\.audit\.session_mode|phoenix-audit\.turn_index|phoenixAudit\.turn_index)' docs/session-shape.md)
test "$typo_drift" -eq 0 \
  || fail "session-shape.md contains $typo_drift typo/drift variant(s) of the phoenix_audit.* namespace"
pass "Per-turn namespace attributes anchored (phoenix_audit.session_mode + phoenix_audit.turn_index) with escaped-dot regex + typo anti-anchor"

# -- PRD-side cross-reference verified (round-1 test-analyzer N2) ------------
# session-shape.md claims a cross-ref to PRD's known-limitations section.
# Verify the PRD actually contains the load-bearing latency language so the
# claim isn't stale.
assert_grep 'A2A round-trip latency' docs/PRD.md
# AND the patch's session-shape.md should reference RAT-2 IF-14 by the
# specific issue ID (not just "RAT-2"), so D4-8 cite-and-verify is enforced.
assert_grep 'IF-14' docs/session-shape.md
assert_grep 'IF-14' research/google-cloud-rapid-agent/RAT-2-results.md
pass "PRD cross-ref to A2A-latency known-limitation verified + RAT-2 IF-14 anchor verified in cited file"

# -- 400-line guard ----------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean"

# -- §14: no mocks introduced (spec-only patch) ------------------------------
SCAN_DIRS=(apps/target-agent/src apps/chaoslab-agent/src)
for d in "${SCAN_DIRS[@]}"; do
  file_count=$(find "$d" -name '*.py' -type f | wc -l | tr -d ' ')
  if [ "$file_count" -eq 0 ]; then
    echo "  §14 WARN: $d has 0 Python files — gate cannot catch mocks here until Epic 4 ships modules"
  else
    echo "  §14 scan target: $d ($file_count Python files)"
  fi
done
assert_no_pattern_in_dirs '(mock|fake|dummy|hardcoded|simulated)' "${SCAN_DIRS[@]}"
pass "§14 clean: no mocks/fakes/dummies/hardcoded/simulated in scan dirs"

echo ""
echo "==========================================="
echo "patch-21 verification: PASS"
echo "==========================================="
