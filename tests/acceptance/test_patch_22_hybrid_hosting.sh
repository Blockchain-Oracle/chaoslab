#!/usr/bin/env bash
# Acceptance test for Patch #22 — Hybrid Phoenix-hosting amendment (ADR-017).
# Translates the hybrid-hosting plan into machine-verifiable assertions.
# Exit 0 = patch complete.
#
# This is a SPEC-LEVEL patch (no Python hot path changes; the compose.yaml fix
# is the only non-doc edit). Runtime wiring lands in Epic 4 orchestrator stories.
#
# Inherits ALL hardened disciplines from Patches #19/#20/#21:
#   - HARDCODED canonical literals via assert_block_present (PR #29 round-2 lesson)
#   - grep_count helper for count-based gates (PR #28 round-4 NB-1 fix)
#   - Section-scoped awk extraction + tempfile for downstream obligations
#   - <!-- prettier-ignore --> directive prevents markdown table churn (PR #30)
#   - Negation-context whitelist via \b word boundaries (PR #29 round-3)
#   - §14 unconditional SCAN_DIRS (PR #28 round-3)
#   - Cross-file Model-A anti-anchor loop (PR #20 round-3)

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
set -euo pipefail

# -- ADR-017 lands in architecture.md ----------------------------------------
assert_grep '^### ADR-017: Hybrid Phoenix-hosting' docs/architecture.md
assert_grep 'Phoenix Audit-side by default' docs/architecture.md
assert_grep 'Customer-side BYO' docs/architecture.md
# Explicitly supersedes ADR-013's mode-specific claims (NOT all of ADR-013;
# only the "Customer-side only" stance).
assert_grep 'supersede.*ADR-013|ADR-013.*supersede' docs/architecture.md
pass "ADR-017 (Hybrid Phoenix-hosting) lands in architecture.md + explicitly supersedes ADR-013 mode-specific claims"

# -- Honest rationale: ADR-013's original overstated claims are NAMED + corrected
# The Big-4 precedent + Annex IV reading + signature integrity correction.
assert_grep 'Big-4|Big.Four' docs/architecture.md
assert_grep 'Annex IV.*not require.*Customer-side|Annex IV.*specif.*pack contents' docs/architecture.md
# Hash-at-acquisition framing replaces the "evidence must live at Customer" claim.
assert_grep 'hash-at-acquisition|ISO/IEC 27037' docs/architecture.md
pass "ADR-017 documents honest rationale: Big-4 precedent + Annex IV reading + signature-integrity correction"

# -- ADR-004 amended for production self-hosted Phoenix -----------------------
# ADR-004 was originally scoped self-hosted Phoenix Docker to dev-only.
# Hybrid amendment promotes it to production-grade infrastructure.
assert_grep 'production' docs/architecture.md
# The amendment marker per project convention.
assert_grep 'ADR-004.*AMENDED|AMENDED.*ADR-004' docs/architecture.md
pass "ADR-004 amended to allow self-hosted Phoenix in production (not just dev)"

# -- docs/run-config-schema.md amended for hybrid mode -----------------------
# `phoenix_provider` field added; `customer_phoenix` block now OPTIONAL.
assert_grep 'phoenix_provider' docs/run-config-schema.md
assert_grep '"phoenix-audit"|"customer"' docs/run-config-schema.md
# Default is the zero-friction mode.
assert_grep 'default.*phoenix-audit|phoenix-audit.*default' docs/run-config-schema.md
# customer_phoenix is now optional, required ONLY in BYO mode.
assert_grep 'customer_phoenix.*OPTIONAL|OPTIONAL.*customer_phoenix' docs/run-config-schema.md
pass "run-config-schema.md declares phoenix_provider with phoenix-audit default + customer_phoenix is now OPTIONAL"

# -- Two cover-paragraph variants byte-locked via HARDCODED literals ---------
# Default-mode variant (Phoenix Audit hosted; 24h retention).
IFS= read -r -d '' COVER_DEFAULT_MODE <<'EOF' || true
Audit traces are retained in Phoenix Audit's hosted Phoenix project for 24 hours after this report's cryptographic signature is emitted, then cryptographically erased via Cloud KMS key-shred. Phoenix Audit acts as a GDPR Article 28 data processor for the duration of the retention window. This signed PDF is the durable artifact; all underlying probe-and-response data is destroyed after the retention window closes.
EOF
COVER_DEFAULT_MODE="${COVER_DEFAULT_MODE%$'\n'}"
[ "${#COVER_DEFAULT_MODE}" -ge 200 ] \
  || fail "COVER_DEFAULT_MODE heredoc parsed to ${#COVER_DEFAULT_MODE} chars (expected ≥200); heredoc parse failure suspected"
assert_block_present "$COVER_DEFAULT_MODE" docs/run-config-schema.md

# BYO-mode variant (Customer hosted; the original ADR-013 framing, preserved).
IFS= read -r -d '' COVER_BYO_MODE <<'EOF' || true
Audit traces remain in the Customer's Phoenix project (project ID: {project_name} at {endpoint}) under the Customer's data-retention policy. Phoenix Audit accessed the trace data only during the audit run window (start: {run_started_at}; end: {run_completed_at}) and holds no copy after report generation. This signed PDF is the only Phoenix Audit-side artifact; all underlying evidence remains in the Customer's tenancy.
EOF
COVER_BYO_MODE="${COVER_BYO_MODE%$'\n'}"
[ "${#COVER_BYO_MODE}" -ge 400 ] \
  || fail "COVER_BYO_MODE heredoc parsed to ${#COVER_BYO_MODE} chars (expected ≥400); heredoc parse failure suspected"
assert_block_present "$COVER_BYO_MODE" docs/run-config-schema.md

# Exactly TWO fenced text blocks in the schema (one per cover variant).
# Drift to one block = the hybrid lock has silently collapsed back to single-mode.
fenced_text_count=$(grep_count '^```text$' docs/run-config-schema.md)
test "$fenced_text_count" -eq 2 \
  || fail "run-config-schema.md has $fenced_text_count fenced \`\`\`text blocks (expected exactly 2 — one cover-paragraph variant per hosting mode)"
pass "Two cover-paragraph variants byte-locked via HARDCODED canonical literals (default 24h-retention + BYO Customer-side; exactly 2 fenced text blocks)"

# -- New docs/data-retention-policy.md declares the 24h SLA + GDPR Art 28 ----
assert_file docs/data-retention-policy.md
assert_grep '24.hour|24h TTL' docs/data-retention-policy.md
# Deletion trigger is the signature-emission event, not a clock-based TTL.
assert_grep 'signature.emission|signature-trigger' docs/data-retention-policy.md
# Key-shred (cryptographic erasure) is the deletion method.
assert_grep 'key-shred|cryptographic erasure' docs/data-retention-policy.md
# GDPR Article 28 processor obligations explicitly acknowledged.
assert_grep 'GDPR Article 28|Article 28' docs/data-retention-policy.md
# Right-to-erasure pathway disclosed (mandatory per GDPR research finding).
assert_grep 'right.to.erasure|right of erasure' docs/data-retention-policy.md
# Cross-reference to ADR-017 (the architectural decision this policy serves).
assert_grep 'ADR-017' docs/data-retention-policy.md
pass "data-retention-policy.md declares 24h TTL + signature-trigger + key-shred + GDPR Art 28 + right-to-erasure + ADR-017 cross-ref"

# -- PRD.md rewritten for hybrid positioning ---------------------------------
# Line 39 (competitive cut): hybrid framing replaces "Customer's OWN" sovereignty pitch.
assert_grep 'zero.friction|Phoenix Audit.hosted' docs/PRD.md
assert_grep 'BYO.key|BYO-key' docs/PRD.md
# Line 186 (out-of-scope): self-hosted Phoenix is now IN scope (default mode).
# This is an anti-anchor: refuse the original "out of scope" framing.
prd_out_of_scope_violations=$(grep -nE 'On.premise.*self.hosted.*Phoenix|self.hosted Phoenix.*out.of.scope|self.hosted Phoenix.*not in scope' docs/PRD.md | wc -l | tr -d ' ' || true)
test "$prd_out_of_scope_violations" -eq 0 \
  || fail "PRD.md still lists self-hosted Phoenix as out-of-scope ($prd_out_of_scope_violations occurrence(s)) — hybrid amendment requires it as in-scope default"
# Cross-reference ADR-017.
assert_grep 'ADR-017' docs/PRD.md
pass "PRD.md hybrid positioning landed: zero-friction + BYO-key framing; self-hosted out-of-scope removed; ADR-017 cross-ref"

# -- README.md updated for hybrid positioning --------------------------------
assert_grep 'zero.friction|Phoenix Audit.hosted' README.md
# Anti-anchor: README MUST NOT pitch Customer-side-only as the unconditional differentiator.
readme_customer_side_only_violations=$(grep -nE 'audit traces.*live in.*Customer.s Phoenix project.*not in Phoenix Audit.s tenancy' README.md | wc -l | tr -d ' ' || true)
test "$readme_customer_side_only_violations" -eq 0 \
  || fail "README.md still pitches Customer-side-only as unconditional differentiator ($readme_customer_side_only_violations occurrence(s))"
pass "README.md hybrid framing landed; Customer-side-only unconditional pitch removed"

# -- audit-notes D4-12 formal-landing record ---------------------------------
assert_grep '^### D4-12' docs/audit-notes.md
assert_grep 'Patch #22|hybrid' docs/audit-notes.md
# Cross-refs to the research findings that drove the supersession.
assert_grep 'ADR-017' docs/audit-notes.md
assert_grep 'Big-4|Annex IV' docs/audit-notes.md
pass "audit-notes D4-12 records the hybrid-hosting formal landing + research cross-refs"

# -- infra/phoenix-self-host/compose.yaml: bug fix + pin + Postgres backend --
assert_file infra/phoenix-self-host/compose.yaml
# BLOCKER fix: empty-default PHOENIX_SECRET must be gone. The whole line dropped.
# Original was: `PHOENIX_SECRET=${PHOENIX_SECRET:-}` which crashed Phoenix 17.2.0.
phoenix_secret_empty_default=$(grep -cE 'PHOENIX_SECRET=\$\{PHOENIX_SECRET:-\}' infra/phoenix-self-host/compose.yaml || true)
test "$phoenix_secret_empty_default" -eq 0 \
  || fail "compose.yaml still has the broken 'PHOENIX_SECRET=\${PHOENIX_SECRET:-}' empty-default ($phoenix_secret_empty_default occurrence(s)) — Phoenix 17.2.0 crashes on this"
# Image pinned to 17.2.0 (was :latest in the broken version).
assert_grep 'arizephoenix/phoenix:17\.2\.0' infra/phoenix-self-host/compose.yaml
# Anti-anchor: refuse :latest tag.
latest_tag_violations=$(grep -cE 'arizephoenix/phoenix:latest' infra/phoenix-self-host/compose.yaml || true)
test "$latest_tag_violations" -eq 0 \
  || fail "compose.yaml still uses :latest tag ($latest_tag_violations occurrence(s)) — pin to specific version per smoke-test recommendation"
# Postgres sidecar present.
assert_grep '^\s*postgres:' infra/phoenix-self-host/compose.yaml
assert_grep 'PHOENIX_SQL_DATABASE_URL.*postgresql' infra/phoenix-self-host/compose.yaml
pass "infra/phoenix-self-host/compose.yaml: empty-default PHOENIX_SECRET removed + image pinned to 17.2.0 + Postgres sidecar added"

# -- Cross-file Model-A anti-anchor (PR #20 cross-file discipline) -----------
# The Model A claim ("Phoenix Audit holds traces forever / centralizes audit data")
# is refused across ALL spec files. The 24h TTL framing in default mode is NOT
# Model-A — it's a deliberate retention with cryptographic erasure.
for f in docs/architecture.md docs/run-config-schema.md docs/PRD.md docs/audit-notes.md docs/data-retention-policy.md README.md; do
  assert_readable "$f"
  set +o pipefail
  model_a_bad=$(grep -niE '(Phoenix Audit|we) (hold|retain|store|keep)s? (your |the |all |customer )?(traces|audit data|probe data|evidence) (forever|indefinitely|permanently|without limit)' "$f" \
    | grep -ivE '\b(NOT|not|cannot|never|no\b|do not|does not)\b' \
    | wc -l | tr -d ' ' || true)
  set -o pipefail
  test "$model_a_bad" -eq 0 \
    || fail "$f contains $model_a_bad Model-A regression claim(s) (Phoenix Audit holds traces forever/indefinitely/permanently)"
done
pass "Cross-file Model-A anti-anchor (forever/indefinitely/permanently retention) applied to all 6 spec files"

# -- Anti-anchor against silent collapse back to single-mode ----------------
# The hybrid lock means BOTH modes must remain documented. Refuse any claim
# that Phoenix Audit's overall product stance is "always" / "only" /
# "exclusively" one mode. Whitelist:
#   - lines containing NOT/not/cannot (the canonical denials of the stance)
#   - lines where the match is a NOUN MODIFIER ("only Phoenix Audit-side
#     artifact" = the only thing on our side; not a stance claim) —
#     detected via trailing nouns like "artifact|copy|reference|usage|view"
#   - lines inside the canonical-fixture fenced blocks (BYO + default
#     variants legitimately use this phrasing for legal text)
for f in docs/architecture.md docs/run-config-schema.md docs/PRD.md; do
  set +o pipefail
  collapse_bad=$(grep -niE '(always|only|exclusively|never anything but)\s+(Customer-side|Phoenix Audit-side|self-hosted|BYO)' "$f" \
    | grep -ivE '\b(NOT|not|cannot|never\s+only)\b' \
    | grep -ivE '(only|always|exclusively)\s+(Customer-side|Phoenix Audit-side|self-hosted|BYO)[- ]?(artifact|copy|reference|view|usage|tenancy|store|read)' \
    | wc -l | tr -d ' ' || true)
  set -o pipefail
  test "$collapse_bad" -eq 0 \
    || fail "$f contains $collapse_bad single-mode-collapse claim(s) (always/only/exclusively one mode as a stance, not a noun modifier) — hybrid amendment requires both modes documented"
done
pass "Single-mode-collapse anti-anchor applied (refuses 'always/only/exclusively Customer-side OR Phoenix Audit-side' as a stance; noun-modifier usages whitelisted)"

# -- 400-line guard ----------------------------------------------------------
run_silent python3 scripts/check_max_lines.py --strict
pass "400-line guard clean"

# -- §14: no mocks introduced (spec + infra edits; no Python src changes) ----
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
pass "§14 clean: no mocks/fakes/dummies/hardcoded/simulated in scan dirs"

echo ""
echo "==========================================="
echo "patch-22 verification: PASS"
echo "==========================================="
