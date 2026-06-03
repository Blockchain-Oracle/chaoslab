#!/usr/bin/env bash
# Acceptance test for story-1.1-monorepo-init.
# Translates the BDD criteria from docs/stories/story-1.1-monorepo-init.md
# into a runnable verification. Exit 0 = story complete; non-zero = blocked.
#
# Run from repo root: ./tests/acceptance/test_story_1_1_monorepo.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

fail() {
  echo "❌ FAIL: $1" >&2
  exit 1
}
pass() {
  echo "✅ $1"
}

# --- BDD: repo-root files exist ---
for f in pyproject.toml pnpm-workspace.yaml package.json LICENSE NOTICE .gitignore .markdownlint.json .gitleaks.toml CLAUDE.md README.md; do
  test -f "$f" || fail "missing repo-root file: $f"
done
pass "all 10 repo-root files present"

# --- BDD: top-level dirs exist ---
for d in apps packages infra scripts docs; do
  test -d "$d" || fail "missing top-level dir: $d"
done
pass "all 5 top-level dirs present"

# --- BDD: workspace members declared in pyproject.toml ---
grep -qE "members\s*=\s*\[.*chaoslab-agent.*target-agent" pyproject.toml \
  || grep -Pzq "(?s)members\s*=\s*\[[^\]]*chaoslab-agent[^\]]*target-agent" pyproject.toml \
  || fail "pyproject.toml [tool.uv.workspace] members must include chaoslab-agent + target-agent"
pass "uv workspace members declared"

# --- BDD: pnpm-workspace.yaml lists apps/* ---
grep -qE "apps/\*" pnpm-workspace.yaml || fail "pnpm-workspace.yaml missing 'apps/*'"
pass "pnpm workspace members declared"

# --- BDD: Apache-2.0 verbatim ---
head -1 LICENSE | grep -q "Apache License" || fail "LICENSE first line must contain 'Apache License'"
pass "LICENSE is Apache-2.0"

# --- BDD: README has run-locally per §13 ---
COUNT=$(grep -cE "(uv sync|pnpm install)" README.md || echo 0)
if [ "${COUNT:-0}" -lt 2 ]; then
  fail "README.md must reference both 'uv sync' AND 'pnpm install' (got $COUNT matches)"
fi
pass "README run-locally section present ($COUNT matches)"

# --- BDD: .gitignore covers Python + Node + IDE ---
COUNT=$(grep -cE "(\.venv|node_modules|\.next)" .gitignore || echo 0)
if [ "${COUNT:-0}" -lt 3 ]; then
  fail ".gitignore must cover .venv, node_modules, .next (got $COUNT matches)"
fi
pass ".gitignore covers required patterns"

# --- BDD: app pyproject.toml workspace members ---
test -f apps/chaoslab-agent/pyproject.toml || fail "missing apps/chaoslab-agent/pyproject.toml"
test -f apps/target-agent/pyproject.toml   || fail "missing apps/target-agent/pyproject.toml"
test -f apps/chaoslab-web/package.json     || fail "missing apps/chaoslab-web/package.json"
pass "all 3 app workspace member files present"

# --- BDD: uv sync from repo root exits 0 + .venv created ---
echo ""
echo "Running: uv sync..."
uv sync 2>&1 | tail -5
test -d .venv || fail "uv sync did not create .venv/"
pass "uv sync succeeds; .venv/ exists"

# --- BDD: pnpm install from repo root exits 0 + node_modules created ---
echo ""
echo "Running: pnpm install..."
pnpm install 2>&1 | tail -5
test -d node_modules || fail "pnpm install did not create node_modules/"
pass "pnpm install succeeds; node_modules/ exists"

# --- BDD: uv pip list works (workspace resolved) ---
uv pip list >/dev/null 2>&1 || fail "uv pip list failed (workspace not resolved)"
pass "uv workspace resolved"

# --- BDD: workspace-root pyproject.toml has NO [project] table ---
if grep -qE "^\[project\]" pyproject.toml; then
  fail "workspace-root pyproject.toml MUST NOT have [project] table (uv-workspace pattern)"
fi
pass "workspace-root pyproject.toml has no [project] table (correct)"

# --- BDD: NOTICE has the ChaosLab header ---
grep -q "ChaosLab" NOTICE || fail "NOTICE must contain 'ChaosLab'"
pass "NOTICE has project header"

# --- BDD: ruff config block present in workspace root ---
grep -qE "\[tool\.ruff\]" pyproject.toml || fail "pyproject.toml missing [tool.ruff]"
grep -qE "\[tool\.ruff\.lint\]" pyproject.toml || fail "pyproject.toml missing [tool.ruff.lint]"
grep -qE "\[tool\.ruff\.format\]" pyproject.toml || fail "pyproject.toml missing [tool.ruff.format]"
pass "ruff config blocks present"

# --- BDD: ty config block present ---
grep -qE "\[tool\.ty\]" pyproject.toml || fail "pyproject.toml missing [tool.ty]"
pass "ty config block present"

# --- BDD: pytest + coverage config present ---
grep -qE "\[tool\.pytest\.ini_options\]" pyproject.toml || fail "missing [tool.pytest.ini_options]"
grep -qE "\[tool\.coverage\.run\]" pyproject.toml || fail "missing [tool.coverage.run]"
pass "pytest + coverage config present"

echo ""
echo "═══════════════════════════════════════"
echo "story-1.1 verification: PASS"
echo "═══════════════════════════════════════"
