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
  #
  # Exit-code discrimination matters: grep 0=match, 1=no-match, ≥2=tool-error.
  # Round-3 silent-failure-hunter R3-6 caught: `if grep ...; then` resets
  # `$?` to 0 in the no-match branch, making the rc≥2 tool-error check
  # unreachable. Capture explicitly into rc instead.
  local pattern="$1" file="$2"
  assert_readable "$file"
  local rc=0
  grep -qE "$pattern" "$file" || rc=$?
  if [ "$rc" -ge 2 ]; then
    fail "grep failed against $file (exit $rc, pattern '$pattern')"
  fi
  if [ "$rc" -ne 0 ]; then
    fail "pattern '$pattern' not found in $file"
  fi
}

assert_no_grep() {
  # Pattern must NOT appear in file.
  # Same exit-code discrimination as assert_grep (round-3 R3-6).
  local pattern="$1" file="$2"
  assert_readable "$file"
  local rc=0
  grep -qE "$pattern" "$file" || rc=$?
  if [ "$rc" -ge 2 ]; then
    fail "grep failed against $file (exit $rc, pattern '$pattern')"
  fi
  if [ "$rc" -eq 0 ]; then
    fail "pattern '$pattern' UNEXPECTEDLY found in $file"
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

# -- block / paragraph assertions (multi-line content lock) -------------------

assert_block_present() {
  # Verify a multi-line block is present verbatim inside a file
  # (substring match — every byte of the block must appear in order).
  # Round-3 R3-3 + round-4 R4-F8: explicitly reject empty needle
  # (Python's `"" in text` is trivially True; an empty needle would
  # silently pass). Reject suspiciously-short needles (defensive
  # against heredoc parse failure). Default minimum is 32 chars, but
  # callers can override via optional 3rd argument for legitimate
  # short fixtures (signature formats, version strings, etc.).
  # Usage: assert_block_present "$block_text" docs/foo.md [min_chars=32]
  local block="$1" file="$2" min_chars="${3:-32}"
  [ -n "$block" ] || fail "assert_block_present: empty needle (heredoc parse failure?)"
  if [ "${#block}" -lt "$min_chars" ]; then
    fail "assert_block_present: needle suspiciously short (${#block} chars; expected ≥${min_chars} — heredoc parse failure? caller can override via 3rd arg)"
  fi
  assert_readable "$file"
  # Round-4 comment-analyzer LOW: discriminate Python exit codes:
  # 0=present, 1=absent, other=tool error. Use rc capture, not || fail.
  set +e
  python3 - "$file" "$block" <<'PY'
import sys, pathlib
file_path, needle = sys.argv[1], sys.argv[2]
text = pathlib.Path(file_path).read_text()
sys.exit(0 if needle in text else 1)
PY
  local rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then return 0; fi
  if [ "$rc" -eq 1 ]; then fail "block not found verbatim in $file"; fi
  fail "assert_block_present: python3 helper exited rc=$rc (tool error, not absent-match)"
}

assert_block_absent() {
  # Inverse of assert_block_present — pattern MUST NOT appear verbatim.
  # Round-4 comment-analyzer LOW: don't silently pass on python error.
  local block="$1" file="$2"
  [ -n "$block" ] || fail "assert_block_absent: empty needle"
  assert_readable "$file"
  set +e
  python3 - "$file" "$block" <<'PY'
import sys, pathlib
file_path, needle = sys.argv[1], sys.argv[2]
text = pathlib.Path(file_path).read_text()
sys.exit(0 if needle in text else 1)
PY
  local rc=$?
  set -e
  if [ "$rc" -eq 1 ]; then return 0; fi
  if [ "$rc" -eq 0 ]; then fail "block unexpectedly present in $file"; fi
  fail "assert_block_absent: python3 helper exited rc=$rc (tool error, not match)"
}

# -- safe recursive-grep scan (B1/B3/B4 discipline applied to multi-dir scan) -

assert_no_pattern_in_dirs() {
  # Verify a regex pattern does NOT appear in any file under the given
  # directories. Discriminates "zero matches" (exit 1 — clean) from
  # "tool error" (exit ≥2 — fail loud with stderr surfaced).
  # The `--exclude-pattern` flag allows lines containing a literal carve-out
  # marker to be filtered out before the failure check.
  # Usage:
  #   assert_no_pattern_in_dirs PATTERN [--exclude-pattern STR] DIR [DIR...]
  #
  # Round-3 test-analyzer R3-F4 caught: original parser only checked $1
  # for --exclude-pattern; a mis-ordered call (`PAT DIR --exclude-pattern
  # MARK DIR`) would silently skip the filter. Now scans ALL args for `--`
  # flags and fails on anything unrecognized (no silent fall-through).
  local pattern="$1"
  shift
  local exclude=""
  local dirs=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --exclude-pattern)
        [ -n "$exclude" ] && fail "assert_no_pattern_in_dirs: --exclude-pattern supplied twice"
        [ "$#" -ge 2 ] || fail "assert_no_pattern_in_dirs: --exclude-pattern missing value"
        exclude="$2"
        shift 2
        ;;
      --*)
        fail "assert_no_pattern_in_dirs: unknown flag '$1' (typo? supported: --exclude-pattern)"
        ;;
      *)
        dirs+=("$1")
        shift
        ;;
    esac
  done
  [ "${#dirs[@]}" -gt 0 ] || fail "assert_no_pattern_in_dirs: no scan dirs supplied"
  for d in "${dirs[@]}"; do
    assert_dir "$d"
  done
  local raw_log
  raw_log="$(mktemp)"
  set +e
  grep -rEn "$pattern" "${dirs[@]}" >"$raw_log" 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ge 2 ]; then
    echo "--- grep tool error (rc=$rc, pattern '$pattern') ---" >&2
    cat "$raw_log" >&2
    rm -f "$raw_log"
    fail "grep tool failure scanning: ${dirs[*]}"
  fi
  local violations
  if [ -n "$exclude" ]; then
    violations=$(grep -v "$exclude" "$raw_log" || true)
  else
    violations=$(cat "$raw_log")
  fi
  rm -f "$raw_log"
  if [ -n "$violations" ]; then
    echo "--- pattern '$pattern' found in scan dirs ---" >&2
    echo "$violations" >&2
    fail "assert_no_pattern_in_dirs: violations in ${dirs[*]}"
  fi
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
