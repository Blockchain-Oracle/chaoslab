#!/usr/bin/env bash
# Shared acceptance-test helpers.
# Source from tests/acceptance/test_story_*.sh as: source "$(dirname "$0")/_lib.sh"
#
# Sets strict-mode, anchors to REPO_ROOT, and provides surgical assertions
# that distinguish "legitimate failure" from "tool failure" — addressing the
# silent-failure findings in PR #1 review (B1/B2/B3/B4).

set -euo pipefail

# Resolve REPO_ROOT from the *invoking* script's location (BASH_SOURCE[1]),
# not from _lib.sh itself.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[1]}")/../.." && pwd)"
cd "$REPO_ROOT"

# -- output helpers (no emojis per project style) -----------------------------

fail() {
  # Print to stderr with [FAIL] prefix. Optional second arg = exit code.
  echo "[FAIL] $1" >&2
  exit "${2:-1}"
}

pass() {
  echo "[PASS] $1"
}

# -- file / dir assertions ----------------------------------------------------

assert_file() {
  test -f "$1" || fail "missing file: $1"
}

assert_dir() {
  test -d "$1" || fail "missing dir: $1"
}

assert_readable() {
  test -r "$1" || fail "unreadable file: $1"
}

# -- grep helpers (B1 fix: discriminate "zero matches" from "real error") -----

assert_grep() {
  # Pattern must appear ≥1 times in file.
  local pattern="$1" file="$2"
  assert_readable "$file"
  if grep -qE "$pattern" "$file"; then
    return 0
  fi
  local rc=$?
  if [ "$rc" -ge 2 ]; then
    fail "grep failed against $file (exit $rc, pattern '$pattern')"
  fi
  fail "pattern '$pattern' not found in $file"
}

assert_no_grep() {
  # Pattern must NOT appear in file.
  local pattern="$1" file="$2"
  assert_readable "$file"
  if grep -qE "$pattern" "$file"; then
    fail "pattern '$pattern' UNEXPECTEDLY found in $file"
  fi
  local rc=$?
  if [ "$rc" -ge 2 ]; then
    fail "grep failed against $file (exit $rc, pattern '$pattern')"
  fi
}

# Count grep matches with proper error-code discrimination.
# Echoes count to stdout. Exits non-zero only on grep-tool failure.
grep_count() {
  local pattern="$1" file="$2"
  assert_readable "$file"
  local count rc
  set +e
  count=$(grep -cE "$pattern" "$file")
  rc=$?
  set -e
  if [ "$rc" -ge 2 ]; then
    fail "grep failed against $file (exit $rc, pattern '$pattern')"
  fi
  # grep -c outputs the count even on exit 1 (zero matches).
  echo "${count:-0}"
}

assert_grep_at_least() {
  # Pattern must appear ≥N times in file.
  local pattern="$1" file="$2" min="$3"
  local count
  count=$(grep_count "$pattern" "$file")
  if [ "$count" -lt "$min" ]; then
    fail "expected ≥$min matches of '$pattern' in $file, got $count"
  fi
}

# -- first-line / content checks (B2 fix: awk-based, surface actual content) --

assert_first_nonblank_contains() {
  # First non-blank line of $file must contain $needle (substring).
  local file="$1" needle="$2"
  assert_readable "$file"
  local first
  first=$(awk 'NF{print; exit}' "$file") || fail "awk failed on $file"
  case "$first" in
    *"$needle"*) return 0 ;;
    *) fail "first non-blank line of $file does not contain '$needle' (got: '$first')" ;;
  esac
}

# -- TOML introspection (Q2 fix: portable, BSD-grep-safe) ---------------------
# Uses system python3 (>=3.11 has tomllib stdlib). macOS ships 3.14.

assert_toml_key() {
  # Verify a dot-path key exists in a TOML file.
  # Usage: assert_toml_key pyproject.toml tool.uv.workspace.members
  local file="$1" key="$2"
  assert_readable "$file"
  python3 -c "
import sys, tomllib
with open('$file', 'rb') as f:
    d = tomllib.load(f)
for k in '$key'.split('.'):
    if not isinstance(d, dict) or k not in d:
        sys.exit(1)
    d = d[k]
" >/dev/null 2>&1 || fail "TOML key '$key' missing in $file"
}

assert_toml_value_contains() {
  # Verify a TOML key's value (stringified via repr) contains a substring.
  # Useful for list/dict membership checks.
  local file="$1" key="$2" needle="$3"
  assert_readable "$file"
  python3 -c "
import sys, tomllib
with open('$file', 'rb') as f:
    d = tomllib.load(f)
for k in '$key'.split('.'):
    d = d[k]
sys.exit(0 if '$needle' in repr(d) else 1)
" >/dev/null 2>&1 || fail "TOML key '$key' in $file does not contain '$needle'"
}

# -- command runner (B3 fix: capture exit code, print on failure only) --------

run_silent() {
  # Run a command, suppress output on success, print full log on failure.
  # Usage: run_silent uv sync
  local logfile
  logfile="$(mktemp)"
  if "$@" >"$logfile" 2>&1; then
    rm -f "$logfile"
    return 0
  fi
  local rc=$?
  echo "--- output from: $* ---" >&2
  cat "$logfile" >&2
  echo "--- end output ---" >&2
  rm -f "$logfile"
  fail "command failed (exit $rc): $*"
}
