# Story — Implement 400-line enforcement script

**ID:** story-1.3-max-lines-script
**Epic:** Epic 1 — Repo + CI/CD foundation
**Depends on:** story-1.2-precommit-hooks
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** coding agent (and Abu, reviewing PRs)
**I want to** have a single Python script that enforces the 400-significant-line rule on every source file, wired into pre-commit AND CI
**So that** no file ever silently grows past the readable-by-fresh-context-agent threshold — the hard architectural invariant per ADR-010

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `scripts/check_max_lines.py` — NEW — full implementation copy-pasted verbatim from `docs/cicd.md` §"400-line enforcement script" code block. Accepts `--strict` flag (default behavior). Walks `apps/`, `packages/`, `scripts/`. Skips `_vendored/`, `__init__.py`, `.d.ts`, `node_modules/`, `.next/`, `dist/`, `build/`. Counts significant lines (strips blanks + single-line comments per language).
- `scripts/__init__.py` — NEW — empty file so `scripts/` is a discoverable Python module (optional but cheap).
- `scripts/test_check_max_lines.sh` — NEW — small bash test harness: creates a 401-line dummy Python file in a tmp dir, runs the script against it (with `ROOTS` overridden via env), asserts exit code 1; creates a 400-line dummy file, asserts exit code 0; cleans up.
- `.pre-commit-config.yaml` — UPDATE — replace the stub `check-max-lines` hook's `entry:` line if needed (should already match `python3 scripts/check_max_lines.py --strict` from story-1.2 — verify only).
- `CLAUDE.md` — UPDATE — add one bullet: "The 400-line rule is enforced by `scripts/check_max_lines.py`. Run `python3 scripts/check_max_lines.py --strict` locally before pushing. Excluded paths: `_vendored/`, `__init__.py`, `.d.ts`, generated dirs (per ADR-010 + `coding-standards.md` §400-line rule)."

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the repo has the workspace skeleton from stories 1.1-1.2
When the coding agent creates scripts/check_max_lines.py per docs/cicd.md
Then `test -f scripts/check_max_lines.py` exits 0
And `python3 scripts/check_max_lines.py --strict` exits 0 (no files exceed 400 lines yet)

Given a freshly-created dummy file with 401 significant lines under apps/
When `python3 scripts/check_max_lines.py --strict` runs
Then exit code is 1
And stdout contains the dummy file path

Given a freshly-created dummy file with exactly 400 significant lines under apps/
When `python3 scripts/check_max_lines.py --strict` runs
Then exit code is 0
And stdout contains "All files ≤ 400 lines" or equivalent success message

Given a file with 500 lines but located under apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/foo.py
When `python3 scripts/check_max_lines.py --strict` runs
Then exit code is 0 (vendored is excluded per the EXCLUDE_PATTERNS list)

Given the .pre-commit-config.yaml from story-1.2
When `grep -E "check_max_lines\.py" .pre-commit-config.yaml` runs
Then exit code is 0 (the script reference is wired into the local hook)

Given the test harness scripts/test_check_max_lines.sh exists
When `bash scripts/test_check_max_lines.sh` runs
Then exit code is 0 (all assertions pass)
And stdout contains "401-line: FAIL (expected)" and "400-line: PASS (expected)"

Given the script itself
When `wc -l scripts/check_max_lines.py` runs
Then output ≤ 400 (the enforcer must itself conform — meta-rule)
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Script file exists and is executable
test -f scripts/check_max_lines.py
chmod +x scripts/check_max_lines.py

# Script itself respects 400-line rule
[ "$(wc -l < scripts/check_max_lines.py)" -le 400 ]

# Clean-state run passes (no files over 400 lines yet)
python3 scripts/check_max_lines.py --strict

# Create a 401-significant-line dummy and confirm fail
TMPFILE="apps/chaoslab-agent/src/__chaoslab_lint_probe__.py"
mkdir -p "$(dirname "$TMPFILE")"
printf 'x = 1\n%.0s' $(seq 1 401) > "$TMPFILE"
set +e
python3 scripts/check_max_lines.py --strict
EXIT=$?
set -e
[ "$EXIT" -eq 1 ]
rm "$TMPFILE"

# Create a 400-significant-line dummy and confirm pass
printf 'y = 1\n%.0s' $(seq 1 400) > "$TMPFILE"
python3 scripts/check_max_lines.py --strict
rm "$TMPFILE"

# Confirm pre-commit hook references the script
grep -q "check_max_lines.py" .pre-commit-config.yaml

# Run the bundled test harness
bash scripts/test_check_max_lines.sh

# CLAUDE.md mentions the script
grep -q "check_max_lines.py" CLAUDE.md

echo "story-1.3 verification: PASS"
```

---

## Notes for coding agent

- The canonical script body is in `docs/cicd.md` §"400-line enforcement script" — paste verbatim into `scripts/check_max_lines.py`. Constants: `MAX_LINES = 400`, `ROOTS = ["apps/", "packages/", "scripts/"]`, `EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}`, `EXCLUDE_PATTERNS = {"__init__.py", ".d.ts", "_vendored/", "node_modules/", ".next/", "dist/", "build/"}`.
- The `--strict` flag in the spec is currently a no-op in the source (no argparse) — that's intentional, the flag exists for forward-compat. If you want to be tidy, parse it via `sys.argv` so it doesn't crash on unknown args.
- The "significant lines" count strips lines that are blank OR start with `#`, `//`, `/*`, `*`, `<!--` after `.strip()`. Multi-line block comments (`""" ... """` in Python, `/* ... */` in TS) are counted as significant — that's intentional. Docstrings COUNT toward the line budget (per coding-standards rule: split early).
- The script processes Markdown files too — that's per ADR-010. `docs/*.md` are exempt because `docs/` is not in `ROOTS`. If a corpus file in `apps/*/src/**.md` exists it WILL be checked; rare but possible.
- For `scripts/test_check_max_lines.sh`: must clean up on both success and failure. Use `trap "rm -f $TMPFILE" EXIT` pattern.
- The `apps/chaoslab-web/package.json` from story-1.1 is JSON, not in `EXTENSIONS`, so it's never counted. Good.
- Reference: `best-practices/03 §1.1` (400-line enforcement rationale + script pattern), `cicd.md` ADR-010.
