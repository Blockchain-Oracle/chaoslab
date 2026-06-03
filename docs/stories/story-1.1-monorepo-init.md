# Story — Initialize uv + pnpm monorepo

**ID:** story-1.1-monorepo-init
**Epic:** Epic 1 — Repo + CI/CD foundation
**Depends on:** None (this is the first story in the project)
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** coding agent shipping ChaosLab stories
**I want to** start from a fully scaffolded `uv` + `pnpm` monorepo with workspace roots, top-level dirs, license/notice files, and base config
**So that** every later story drops files into a known, lint-ready, line-counted skeleton instead of reinventing repo layout

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `pyproject.toml` — NEW — workspace-root `uv` config; defines `[tool.uv.workspace] members = ["apps/chaoslab-agent", "apps/target-agent"]`; carries the ruff / ty / pytest / coverage config blocks from `docs/coding-standards.md`
- `pnpm-workspace.yaml` — NEW — `packages: ["apps/*", "packages/*"]`
- `package.json` — NEW — workspace root with `name`, `private: true`, `packageManager: "pnpm@9.x"`, `engines.node: ">=20"`, top-level `scripts` (`lint`, `format`, `typecheck`, `test`) that delegate to workspace filters
- `apps/.gitkeep` — NEW — placeholder so empty dir is tracked
- `packages/.gitkeep` — NEW — placeholder
- `infra/.gitkeep` — NEW — placeholder (real files land in story-1.4)
- `scripts/.gitkeep` — NEW — placeholder (real `check_max_lines.py` lands in story-1.3)
- `docs/.gitkeep` — NEW — placeholder; `docs/PRD.md` etc. already exist, this just guarantees dir is present
- `CLAUDE.md` — NEW — skeleton header + "see docs/" pointer; one-paragraph "how to navigate the repo" stub
- `README.md` — NEW — skeleton with §13 ordering (project name, one-line pitch, demo URL placeholder `TBD`, demo GIF placeholder, run-locally 3-step `uv sync && pnpm install && make dev`, license link, Apache-2.0 attribution)
- `LICENSE` — NEW — verbatim Apache-2.0 text (https://www.apache.org/licenses/LICENSE-2.0.txt)
- `NOTICE` — NEW — empty header `ChaosLab\nCopyright 2026 Abu Mostofa\n` (vendoring attribution lands in story-5.1)
- `.gitignore` — NEW — standard Python (`__pycache__`, `*.pyc`, `.venv/`, `.uv-cache/`, `dist/`, `build/`, `*.egg-info/`, `.coverage`, `htmlcov/`) + Node (`node_modules/`, `.next/`, `out/`, `.turbo/`, `pnpm-lock.yaml.bak`) + IDE (`.vscode/`, `.idea/`, `.DS_Store`) + env (`.env`, `.env.local`)
- `.markdownlint.json` — NEW — disables MD013 (line length, conflicts with prose-heavy docs), MD033 (allow inline HTML for badges), MD041 (allow non-h1 first line in stories)
- `.gitleaks.toml` — NEW — extends default ruleset; allowlist for `LICENSE` file (false positives on `Apache-2.0`); allowlist for `docs/research/**` corpus content
- `apps/chaoslab-agent/pyproject.toml` — NEW — minimal `[project] name = "chaoslab-agent" version = "0.1.0" requires-python = ">=3.12"`; declares it as a uv-workspace member
- `apps/target-agent/pyproject.toml` — NEW — minimal `[project] name = "target-agent" version = "0.1.0" requires-python = ">=3.12"`; uv-workspace member
- `apps/chaoslab-web/package.json` — NEW — minimal `{ "name": "chaoslab-web", "version": "0.1.0", "private": true }` (real Next.js scaffold lands in story-7.1, this just unblocks `pnpm install`)

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the repo root is clean (no pyproject.toml, no pnpm-workspace.yaml)
When the coding agent completes this story
Then `test -f pyproject.toml && test -f pnpm-workspace.yaml && test -f package.json` exits 0
And `test -f LICENSE && test -f NOTICE && test -f .gitignore && test -f .markdownlint.json && test -f .gitleaks.toml` exits 0
And `test -f CLAUDE.md && test -f README.md` exits 0

Given pyproject.toml has been created at repo root
When `grep -E "members\s*=\s*\[.*chaoslab-agent.*target-agent" pyproject.toml` runs
Then exit code is 0 (workspace members declared)

Given the workspace root pyproject.toml exists
When `uv sync` runs from the repo root
Then exit code is 0
And `.venv/` directory is created at repo root

Given pnpm-workspace.yaml lists apps/* and packages/*
When `pnpm install` runs from the repo root
Then exit code is 0
And `node_modules/` exists at repo root

Given LICENSE was created
When `head -1 LICENSE` runs
Then output contains "Apache License" (verbatim Apache-2.0 text)

Given README.md was created
When `grep -E "(uv sync|pnpm install)" README.md | wc -l` runs
Then output ≥ 2 (run-locally instructions present per §13)

Given apps/chaoslab-agent/pyproject.toml and apps/target-agent/pyproject.toml exist
When `uv pip list` runs after `uv sync`
Then exit code is 0 (workspace members resolved without error)

Given the .gitignore was created
When `grep -E "(\.venv|node_modules|\.next)" .gitignore | wc -l` runs
Then output ≥ 3
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Repo-root files exist
test -f pyproject.toml
test -f pnpm-workspace.yaml
test -f package.json
test -f LICENSE
test -f NOTICE
test -f .gitignore
test -f .markdownlint.json
test -f .gitleaks.toml
test -f CLAUDE.md
test -f README.md

# Top-level dirs exist
test -d apps && test -d packages && test -d infra && test -d scripts && test -d docs

# Workspace members declared
grep -E "members\s*=\s*\[.*chaoslab-agent.*target-agent" pyproject.toml
grep -E "apps/\*" pnpm-workspace.yaml

# Apache-2.0 verbatim
head -1 LICENSE | grep -q "Apache License"

# README §13 run-locally
grep -cE "(uv sync|pnpm install)" README.md  # expect ≥ 2

# uv resolves the workspace
uv sync
test -d .venv

# pnpm resolves the workspace
pnpm install
test -d node_modules

echo "story-1.1 verification: PASS"
```

---

## Notes for coding agent

- The workspace-root `pyproject.toml` carries the FULL ruff / ty / pytest / coverage configuration verbatim from `docs/coding-standards.md` §"Python standards" — including `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]`, `[tool.ruff.format]`, `[tool.ty]`, `[tool.ty.terminal]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]`, `[tool.coverage.report]`. Copy-paste, do not paraphrase.
- The mypy fallback block (`[tool.mypy]`) from `docs/coding-standards.md` is INCLUDED in the workspace pyproject.toml but inert until ADR-001 fallback triggers; that's fine.
- `apps/chaoslab-web/package.json` MUST be valid JSON so `pnpm install` doesn't fail — even though the real Next.js scaffold lands in story-7.1.
- `pyproject.toml` at workspace root declares NO `[project]` table — only `[tool.uv.workspace]` + the tool configs. Each app under `apps/*` has its own `[project]` block. This is the documented uv-workspace pattern.
- For `.gitleaks.toml`: extend the default ruleset rather than redefining everything. Pattern: `[extend] useDefault = true` + `[[allowlist.paths]]`.
- `CLAUDE.md` for this story is a STUB — single paragraph pointing to `docs/PRD.md`, `docs/architecture.md`, `docs/cicd.md`, `docs/coding-standards.md`. Future stories enrich it.
- `README.md` demo URL is `TBD` placeholder — story-8.1 fills in the real Cloud Run URL after deploy.
- Do NOT run `pre-commit install` here — that's story-1.2's job. Do not create `.pre-commit-config.yaml` either.
- Do NOT create `scripts/check_max_lines.py` here — that's story-1.3. The `scripts/.gitkeep` placeholder is enough.
- Do NOT create `infra/*.sh` here — that's story-1.4.
- Do NOT create `.github/workflows/*.yaml` here — those are stories 1.5–1.7.
