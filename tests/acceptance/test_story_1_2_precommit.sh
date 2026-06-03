#!/usr/bin/env bash
# Acceptance test for story-1.2-precommit-hooks.
# Translates BDD criteria from docs/stories/story-1.2-precommit-hooks.md.
# Exit 0 = story complete.
#
# NOTE: this test SIDE-EFFECTS the repo's .git/hooks/ via `pre-commit install`.
# That's intentional — installing the local git hooks IS part of "done" for S1.2.
#
# Run from anywhere: bash tests/acceptance/test_story_1_2_precommit.sh

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- BDD: pre-commit installed as dev dep -------------------------------------
assert_toml_key pyproject.toml dependency-groups.dev
assert_toml_value_contains pyproject.toml dependency-groups.dev pre-commit
pass "pre-commit declared in [dependency-groups.dev]"

# Verify it actually resolved into the workspace .venv.
run_silent uv sync
run_silent bash -c "uv pip list | grep -q '^pre-commit '"
pass "pre-commit resolved into workspace .venv"

# -- BDD: .pre-commit-config.yaml exists --------------------------------------
assert_file .pre-commit-config.yaml
pass ".pre-commit-config.yaml present"

# -- BDD: all 9 required hook IDs present in config ---------------------------
# Story-1.2 spec requires exactly these 9 ids. We check each individually for
# precise diagnostic on failure (which hook is missing).
for hook_id in ruff ruff-format ty-check check-max-lines eslint prettier gitleaks markdownlint conventional-pre-commit; do
  assert_grep "^[[:space:]]*-[[:space:]]+id:[[:space:]]+${hook_id}\$" .pre-commit-config.yaml
done
pass "all 9 required hook ids present in .pre-commit-config.yaml"

# -- BDD: pre-commit install creates local git hooks --------------------------
run_silent uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
assert_file .git/hooks/pre-commit
assert_file .git/hooks/commit-msg
pass "pre-commit install wired .git/hooks/pre-commit + commit-msg"

# -- BDD: pre-commit run --all-files exits 0, OR exits 1 ONLY on the
#         check-max-lines stub (because scripts/check_max_lines.py lands in S1.3)
echo "Running: uv run pre-commit run --all-files (stub failure on check-max-lines is acceptable pre-S1.3)..."
logfile="$(mktemp)"
set +e
uv run pre-commit run --all-files >"$logfile" 2>&1
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
  pass "pre-commit run --all-files: all green"
elif [ "$rc" -eq 1 ]; then
  # Acceptable iff the failure mention(s) check-max-lines/scripts and no other hook fails.
  if ! grep -q "check_max_lines\|check-max-lines" "$logfile"; then
    echo "--- pre-commit output ---" >&2
    cat "$logfile" >&2
    rm -f "$logfile"
    fail "pre-commit run failed for a non-stub reason (no check_max_lines reference in output)"
  fi
  # Sanity check: count "Failed" lines — if more than one hook failed, that's a problem.
  failed_count=$(grep -cE "^[A-Za-z].*\.{5,}.*Failed\$" "$logfile" || true)
  if [ "$failed_count" -gt 1 ]; then
    echo "--- pre-commit output ---" >&2
    cat "$logfile" >&2
    rm -f "$logfile"
    fail "more than one hook failed ($failed_count) — only check-max-lines stub is acceptable"
  fi
  pass "pre-commit run --all-files: only check-max-lines stub fails (expected pre-S1.3)"
else
  echo "--- pre-commit output ---" >&2
  cat "$logfile" >&2
  rm -f "$logfile"
  fail "pre-commit run exited with unexpected code $rc"
fi
rm -f "$logfile"

# -- BDD: CLAUDE.md mentions pre-commit ---------------------------------------
assert_grep "pre-commit" CLAUDE.md
pass "CLAUDE.md mentions pre-commit"

echo
echo "==========================================="
echo "story-1.2 verification: PASS"
echo "==========================================="
