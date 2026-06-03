#!/usr/bin/env bash
# Acceptance test for story-1.3-max-lines-script.
# Translates BDD criteria from docs/stories/story-1.3-max-lines-script.md.
# Exit 0 = story complete.
#
# Run from anywhere: bash tests/acceptance/test_story_1_3_max_lines.sh

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- BDD: script file exists + is executable ----------------------------------
assert_file scripts/check_max_lines.py
test -x scripts/check_max_lines.py || fail "scripts/check_max_lines.py is not executable"
pass "scripts/check_max_lines.py exists and is executable"

# -- BDD: meta-rule — the enforcer itself must be ≤400 lines ------------------
script_lines=$(wc -l < scripts/check_max_lines.py | tr -d ' ')
if [ "$script_lines" -gt 400 ]; then
  fail "scripts/check_max_lines.py is $script_lines lines (must be ≤400 — meta-rule)"
fi
pass "scripts/check_max_lines.py is ≤400 lines ($script_lines lines)"

# -- BDD: clean-state run passes (no source files >400 lines yet) -------------
run_silent python3 scripts/check_max_lines.py --strict
pass "python3 scripts/check_max_lines.py --strict exits 0 on clean state"

# -- BDD: a 401-significant-line dummy under apps/ triggers exit 1 ------------
PROBE="apps/chaoslab-agent/src/__chaoslab_lint_probe__.py"
mkdir -p "$(dirname "$PROBE")"
# Trap ensures cleanup even on test failure mid-way through this block.
trap 'rm -f "$PROBE"' EXIT
printf 'x = 1\n%.0s' $(seq 1 401) > "$PROBE"
actual_lines=$(grep -cE '^x = 1' "$PROBE")
if [ "$actual_lines" -ne 401 ]; then
  fail "probe file should have 401 significant lines, got $actual_lines"
fi
set +e
output=$(python3 scripts/check_max_lines.py --strict 2>&1)
rc=$?
set -e
if [ "$rc" -ne 1 ]; then
  echo "--- script output ---" >&2
  printf '%s\n' "$output" >&2
  fail "401-line probe should exit 1, got $rc"
fi
case "$output" in
  *"$PROBE"*) : ;;
  *) fail "401-line probe failure output must reference the probe path '$PROBE' (got: $output)" ;;
esac
rm -f "$PROBE"
trap - EXIT
pass "401-line probe correctly fails with stdout referencing the path"

# -- BDD: a 400-significant-line dummy under apps/ exits 0 --------------------
mkdir -p "$(dirname "$PROBE")"
trap 'rm -f "$PROBE"' EXIT
printf 'y = 1\n%.0s' $(seq 1 400) > "$PROBE"
run_silent python3 scripts/check_max_lines.py --strict
rm -f "$PROBE"
trap - EXIT
pass "exact 400-line file passes (boundary inclusive)"

# -- BDD: vendored files are skipped ------------------------------------------
VENDORED="apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/__lint_probe__.py"
mkdir -p "$(dirname "$VENDORED")"
trap 'rm -rf "apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored"' EXIT
printf 'z = 1\n%.0s' $(seq 1 500) > "$VENDORED"
run_silent python3 scripts/check_max_lines.py --strict
rm -rf "apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored"
trap - EXIT
pass "500-line file under _vendored/ is correctly excluded"

# -- Adversarial (PR #3 review GAP-1 / F3): substring match must NOT exclude
#    a directory whose name merely CONTAINS an exclusion pattern.
#    e.g., `apps/foo/rebuild/x.py` is NOT under `build/` — it's `rebuild/`.
REBUILD="apps/chaoslab-agent/src/rebuild/__lint_probe__.py"
mkdir -p "$(dirname "$REBUILD")"
trap 'rm -rf "apps/chaoslab-agent/src/rebuild"' EXIT
printf 'q = 1\n%.0s' $(seq 1 401) > "$REBUILD"
set +e
python3 scripts/check_max_lines.py --strict >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -ne 1 ]; then
  rm -rf "apps/chaoslab-agent/src/rebuild"
  trap - EXIT
  fail "401-line file under rebuild/ MUST trigger the rule (substring guard broken: got rc=$rc)"
fi
rm -rf "apps/chaoslab-agent/src/rebuild"
trap - EXIT
pass "rebuild/ correctly NOT excluded (path-component match, not substring)"

# -- Adversarial (PR #3 review Q5): unknown args must be rejected loud --------
set +e
python3 scripts/check_max_lines.py --bogus-flag-does-not-exist >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -ne 2 ]; then
  fail "unknown arg must exit 2 (argparse), got rc=$rc"
fi
pass "unknown args are rejected loud (exit 2, not silently accepted)"

# -- Adversarial (PR #3 review Q2): missing ROOTS must fail loud --------------
TMPDIR_PROBE=$(mktemp -d)
set +e
( cd "$TMPDIR_PROBE" && python3 "$REPO_ROOT/scripts/check_max_lines.py" --strict >/dev/null 2>&1 )
rc=$?
set -e
rm -rf "$TMPDIR_PROBE"
if [ "$rc" -ne 2 ]; then
  fail "running from a dir without apps/packages/scripts MUST exit 2 (config error), got rc=$rc"
fi
pass "missing ROOTS from cwd fails loud with exit 2 (not silent green)"

# -- Adversarial (PR #3 review Q6): [FAIL] output goes to stderr, not stdout --
PROBE_STDERR="apps/chaoslab-agent/src/__chaoslab_stderr_probe__.py"
mkdir -p "$(dirname "$PROBE_STDERR")"
trap 'rm -f "$PROBE_STDERR"' EXIT
printf 'r = 1\n%.0s' $(seq 1 401) > "$PROBE_STDERR"
# Redirect stderr away; stdout MUST be empty (failure msg goes to stderr).
stdout_capture=$(python3 scripts/check_max_lines.py --strict 2>/dev/null || true)
rm -f "$PROBE_STDERR"
trap - EXIT
if [ -n "$stdout_capture" ]; then
  fail "[FAIL] output must go to stderr, not stdout (got stdout: '$stdout_capture')"
fi
pass "failure output correctly directed to stderr (Unix discipline)"

# -- BDD: pre-commit hook references the script -------------------------------
assert_grep "check_max_lines\\.py" .pre-commit-config.yaml
pass ".pre-commit-config.yaml references scripts/check_max_lines.py"

# -- BDD: bundled test harness scripts/test_check_max_lines.sh works ----------
assert_file scripts/test_check_max_lines.sh
test -x scripts/test_check_max_lines.sh || fail "scripts/test_check_max_lines.sh is not executable"
harness_output=$(bash scripts/test_check_max_lines.sh 2>&1)
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "--- harness output ---" >&2
  printf '%s\n' "$harness_output" >&2
  fail "scripts/test_check_max_lines.sh exited $rc (expected 0)"
fi
case "$harness_output" in
  *"401-line: FAIL (expected)"*) : ;;
  *) fail "harness output must contain '401-line: FAIL (expected)' (got: $harness_output)" ;;
esac
case "$harness_output" in
  *"400-line: PASS (expected)"*) : ;;
  *) fail "harness output must contain '400-line: PASS (expected)' (got: $harness_output)" ;;
esac
pass "scripts/test_check_max_lines.sh runs green with expected markers"

# -- BDD: CLAUDE.md mentions the script ---------------------------------------
assert_grep "check_max_lines\\.py" CLAUDE.md
pass "CLAUDE.md mentions scripts/check_max_lines.py"

# -- Pre-commit end-to-end: now that the real script exists, the check-max-lines
#    hook should PASS (no more --no-verify needed for future commits).
echo "Running: uv run pre-commit run check-max-lines --all-files (should now PASS)..."
run_silent uv run pre-commit run check-max-lines --all-files
pass "pre-commit check-max-lines hook now passes (S1.3 unblocks --no-verify-free commits)"

echo
echo "==========================================="
echo "story-1.3 verification: PASS"
echo "==========================================="
