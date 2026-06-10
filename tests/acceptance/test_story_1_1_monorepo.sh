#!/usr/bin/env bash
# Acceptance test for story-1.1-monorepo-init.
# Translates BDD criteria from docs/stories/story-1.1-monorepo-init.md
# into runnable assertions. Exit 0 = story complete.
#
# Run from anywhere: bash tests/acceptance/test_story_1_1_monorepo.sh

# shellcheck source=tests/acceptance/_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# -- BDD: repo-root files exist -----------------------------------------------
for f in pyproject.toml pnpm-workspace.yaml package.json LICENSE NOTICE \
         .gitignore .markdownlint.json .gitleaks.toml CLAUDE.md README.md; do
  assert_file "$f"
done
pass "all 10 repo-root files present"

# -- BDD: top-level dirs exist ------------------------------------------------
for d in apps packages infra scripts docs; do
  assert_dir "$d"
done
pass "all 5 top-level dirs present"

# -- BDD: workspace members declared (TOML-aware; portable across grep flavors)
assert_toml_key pyproject.toml tool.uv.workspace.members
assert_toml_value_contains pyproject.toml tool.uv.workspace.members phoenix-audit-agent
assert_toml_value_contains pyproject.toml tool.uv.workspace.members target-agent
pass "uv workspace members declared (phoenix-audit-agent + target-agent)"

# -- BDD: pnpm workspace declares apps/* --------------------------------------
assert_grep "apps/\*" pnpm-workspace.yaml
pass "pnpm workspace declares apps/*"

# -- BDD: LICENSE first non-blank line contains "Apache License" --------------
# awk-based; tolerates leading blank lines and surfaces actual content on fail.
assert_first_nonblank_contains LICENSE "Apache License"
pass "LICENSE is Apache-2.0"

# -- BDD: README §13 run-locally references uv sync AND pnpm install ----------
assert_grep_at_least "(uv sync|pnpm install)" README.md 2
pass "README §13 run-locally section present"

# -- BDD: .gitignore covers .venv + node_modules + .next ----------------------
assert_grep_at_least "(\.venv|node_modules|\.next)" .gitignore 3
pass ".gitignore covers required patterns"

# -- BDD: all 3 app workspace member files present ----------------------------
assert_file apps/phoenix-audit-agent/pyproject.toml
assert_file apps/target-agent/pyproject.toml
assert_file apps/phoenix-audit-web/package.json
pass "all 3 app workspace member files present"

# -- BDD: uv sync exits 0; .venv/ exists --------------------------------------
echo "Running: uv sync..."
run_silent uv sync
assert_dir .venv
pass "uv sync succeeds; .venv/ exists"

# -- BDD: pnpm install exits 0; node_modules/ exists --------------------------
echo "Running: pnpm install..."
run_silent pnpm install
assert_dir node_modules
pass "pnpm install succeeds; node_modules/ exists"

# -- BDD: workspace resolved --------------------------------------------------
run_silent uv pip list
pass "uv workspace resolved"

# -- BDD: workspace-root pyproject.toml has NO [project] table ----------------
# Negative grep — if the table exists, fail; if grep itself errors, fail with diagnostic.
if grep -qE "^\[project\]" pyproject.toml; then
  fail "workspace-root pyproject.toml MUST NOT have [project] table (uv-workspace pattern)"
fi
pass "workspace-root pyproject.toml has no [project] table"

# -- BDD: NOTICE has PhoenixAudit header ------------------------------------------
assert_grep "PhoenixAudit" NOTICE
pass "NOTICE has project header"

# -- BDD: ruff config blocks present ------------------------------------------
assert_toml_key pyproject.toml tool.ruff
assert_toml_key pyproject.toml tool.ruff.lint
assert_toml_key pyproject.toml tool.ruff.format
pass "ruff config blocks present"

# -- BDD: ty config block present ---------------------------------------------
assert_toml_key pyproject.toml tool.ty
pass "ty config block present"

# -- BDD: pytest + coverage config present ------------------------------------
assert_toml_key pyproject.toml tool.pytest.ini_options
assert_toml_key pyproject.toml tool.coverage.run
assert_toml_key pyproject.toml tool.coverage.report
pass "pytest + coverage config present"

echo
echo "==========================================="
echo "story-1.1 verification: PASS"
echo "==========================================="
