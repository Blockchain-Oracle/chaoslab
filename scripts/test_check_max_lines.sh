#!/usr/bin/env bash
# Self-contained smoke test for scripts/check_max_lines.py.
# Creates a 401-line and a 400-line probe under apps/, asserts the script
# fails on the first and passes on the second. Cleans up via trap.
#
# Run from repo root: bash scripts/test_check_max_lines.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PROBE="apps/chaoslab-agent/src/__chaoslab_lint_probe__.py"
mkdir -p "$(dirname "$PROBE")"
trap 'rm -f "$PROBE"' EXIT

# Scenario 1: 401 significant lines → must fail.
printf 'a = 1\n%.0s' $(seq 1 401) > "$PROBE"
set +e
python3 scripts/check_max_lines.py --strict >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -ne 1 ]; then
  echo "401-line: FAIL (UNEXPECTED — script returned $rc, want 1)" >&2
  exit 1
fi
echo "401-line: FAIL (expected)"

# Scenario 2: exactly 400 significant lines → must pass.
printf 'b = 1\n%.0s' $(seq 1 400) > "$PROBE"
set +e
python3 scripts/check_max_lines.py --strict >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  echo "400-line: PASS (UNEXPECTED — script returned $rc, want 0)" >&2
  exit 1
fi
echo "400-line: PASS (expected)"

echo "scripts/check_max_lines.py smoke test: PASS"
