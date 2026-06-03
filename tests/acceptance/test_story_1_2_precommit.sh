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
# Robust discriminator: parse `- hook id: <id>` lines that follow a `Failed` line.
# Require the set of failed hook ids to be exactly {check-max-lines} pre-S1.3.
# Strips ANSI color codes so TTY-emulated pre-commit output (PRE_COMMIT_COLOR=always,
# `script`/`unbuffer` wrappers) doesn't break the regex anchors.
echo "Running: uv run pre-commit run --all-files (stub failure on check-max-lines is acceptable pre-S1.3)..."
logfile="$(mktemp)"
set +e
uv run pre-commit run --all-files >"$logfile" 2>&1
rc=$?
set -e

# Strip ANSI codes to a sibling log for parsing.
plain="${logfile}.plain"
sed -E $'s/\x1b\\[[0-9;]*[a-zA-Z]//g' "$logfile" > "$plain"

if [ "$rc" -eq 0 ]; then
  pass "pre-commit run --all-files: all green"
elif [ "$rc" -eq 1 ]; then
  # Parse failed hook ids: collect each `- hook id: X` that follows a `...Failed` line.
  # awk state machine: when we see a Failed line, arm in_fail; the next `- hook id:` consumes it.
  # POSIX-compatible: avoid bash-4-only mapfile/readarray. macOS ships bash 3.2.
  failed_ids_raw=$(awk '
    /^[A-Za-z].*\.{5,}.*Failed[[:space:]]*$/ { in_fail=1; next }
    in_fail && /^- hook id:/ { print $4; in_fail=0; next }
    /^[A-Za-z]/ && !/^- / { in_fail=0 }
  ' "$plain")
  # Count + extract distinct ids.
  if [ -z "$failed_ids_raw" ]; then
    failed_ids_count=0
  else
    failed_ids_count=$(printf '%s\n' "$failed_ids_raw" | wc -l | tr -d ' ')
  fi
  failed_ids_joined=$(printf '%s' "$failed_ids_raw" | tr '\n' ' ' | sed 's/ $//')

  if [ "$failed_ids_count" -eq 1 ] && [ "$failed_ids_joined" = "check-max-lines" ]; then
    # Additionally verify the failure mode is the documented stub (missing scripts/check_max_lines.py).
    if grep -qE "can't open file.*scripts/check_max_lines\.py" "$plain"; then
      pass "pre-commit run --all-files: only check-max-lines stub fails (expected pre-S1.3)"
    else
      echo "--- pre-commit output ---" >&2
      cat "$logfile" >&2
      rm -f "$logfile" "$plain"
      fail "check-max-lines failed but NOT with the documented stub signature (missing script)"
    fi
  else
    echo "--- pre-commit output ---" >&2
    cat "$logfile" >&2
    rm -f "$logfile" "$plain"
    fail "expected exactly {check-max-lines} to fail pre-S1.3, got: {${failed_ids_joined:-<none>}}"
  fi
else
  echo "--- pre-commit output ---" >&2
  cat "$logfile" >&2
  rm -f "$logfile" "$plain"
  fail "pre-commit run exited with unexpected code $rc"
fi
rm -f "$logfile" "$plain"

# -- BDD-adjacent (pr-test-analyzer Gap #1): assert load-bearing local hook `entry:` values.
# Guards IF-2 (prettier fix) and the S1.3 check-max-lines hand-off contract against silent regression.
assert_grep "entry: python3 scripts/check_max_lines.py --strict" .pre-commit-config.yaml
assert_grep "entry: pnpm exec prettier --write" .pre-commit-config.yaml
pass "load-bearing hook entry: values pinned (IF-2 + S1.3 contract)"

# -- BDD: CLAUDE.md mentions pre-commit ---------------------------------------
assert_grep "pre-commit" CLAUDE.md
pass "CLAUDE.md mentions pre-commit"

echo
echo "==========================================="
echo "story-1.2 verification: PASS"
echo "==========================================="
