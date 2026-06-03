# Story — Attribute `deepankarm/agent-chaos` in NOTICE (no vendoring)

**ID:** story-5.1-vendor-agent-chaos
**Epic:** Epic 5 — Fault injection (the 4 fault classes)
**Depends on:** story-1.1-monorepo-init (NOTICE file exists)
**Estimate:** ~20 min
**Status:** PENDING
**tags:** [backend, p0, injector, docs]

---

## ⚠ AMENDED 2026-06-03 per audit A5 (`spec-audit/03-agent-chaos-vendor-audit.md`)

**The original story (below) called for vendoring `chaos/{llm,tool,user}.py` into `_vendored/`. ADR-006 has been amended (`docs/architecture.md`) — we do NOT vendor anymore.**

**What this story now does:**
1. **Verify the source repo** at `github.com/deepankarm/agent-chaos` is reachable and Apache-2.0 licensed (already verified by audit; pinned commit SHA `32beff46a28ca043e252095e6cc62ffe2010e645`)
2. **Add a `NOTICE` entry at repo root** with the attribution text:
   ```
   This project draws architectural inspiration from `deepankarm/agent-chaos`
   (https://github.com/deepankarm/agent-chaos), Apache-2.0 licensed.
   Reference commit: 32beff46a28ca043e252095e6cc62ffe2010e645 (2026-01-02).
   No source code is copied; fault primitives in apps/chaoslab-agent/src/chaoslab_agent/injector/faults/
   are implemented natively against the Google ADK callback system per architecture/04 §8.
   ```
3. **Add a one-line credit to each F1-F4 source file's module docstring** (S5.2-S5.5 add the code; S5.1 just confirms the docstring template):
   ```python
   """F<N>: <fault name>. Architectural inspiration from deepankarm/agent-chaos (Apache-2.0)."""
   ```
4. **Delete any `_vendored/` directory references** in this story's file modification map and from `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/`. There is no vendoring.
5. **Why:** the upstream `chaos/llm.py` is Anthropic-only (hardcoded `anthropic.RateLimitError` etc.) and `patch/providers/gemini.py` is a `NotImplementedError` stub. F1-F4 already reimplement natively. Vendoring offers zero code reuse, costs ~1.5h of integration, and adds maintenance burden. Attribution-only is legally clean (Apache-2.0 doesn't require attribution for non-copy use) and adequate as architectural courtesy.

**Amended BDD acceptance criteria:**
```
Given the NOTICE file at repo root
When `grep "deepankarm/agent-chaos" NOTICE` runs
Then exit 0 AND the pinned SHA "32beff46a28ca043e252095e6cc62ffe2010e645" appears in the file

Given no _vendored/ directory exists anywhere under apps/chaoslab-agent/src/
When `find apps/chaoslab-agent/src -type d -name _vendored` runs
Then output is empty (exit 0 with no results)

Given F1-F4 modules will be authored in S5.2-S5.5
When each is created, its docstring includes "deepankarm/agent-chaos" + "Apache-2.0"
Then a grep across all 4 returns at least 4 matches (one per file)
```

**File modification map (amended):**
- `NOTICE` (NEW or UPDATE at repo root) — add the attribution block above
- Remove all references to `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/` from the rest of the story content below
- The original "vendor copy" file map below is **superseded** — coding agent should treat it as historical context only

**Original story content below preserved as historical context — coding agent: IGNORE the file modification map below; follow the AMENDED section above.**

---

---

## User story

**As a** ChaosLab maintainer staring at a 9-day deadline
**I want to** vendor the fault primitives from `deepankarm/agent-chaos` (Apache-2.0) into `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/`
**So that** the 4 MVP fault classes (F1-F4) wrap battle-tested primitives instead of re-implementing rate-limit / timeout / mutation logic from scratch — per ADR-006 this saves 3-4 days of build and is the largest single time saving on `architecture/01 §2`'s catalog

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/__init__.py` — NEW if absent — empty marker (re-exports for F1-F4 land in stories 5.2-5.5)
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/__init__.py` — NEW — empty marker; per ADR-010 the `_vendored/` directory is EXCLUDED from the 400-line guard and from coverage
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/llm.py` — NEW — verbatim copy of `src/agent_chaos/chaos/llm.py` from `github.com/deepankarm/agent-chaos` at the pinned SHA. Do NOT reformat with ruff (vendored carve-out); do NOT delete unused symbols
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/tool.py` — NEW — verbatim copy of `src/agent_chaos/chaos/tool.py` at the same SHA
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/user.py` — NEW — verbatim copy of `src/agent_chaos/chaos/user.py` at the same SHA
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/README.md` — NEW — vendored notice: source repo URL, pinned commit SHA, copy date (2026-06-02), Apache-2.0 license link, list of modifications (initially: "none — verbatim copy. Integration with ADK callback system lives in sibling F1-F4 wrapper modules.")
- `NOTICE` — UPDATE (or NEW at repo root if absent) — append attribution block: `This project includes code from deepankarm/agent-chaos (https://github.com/deepankarm/agent-chaos), licensed under Apache License 2.0. Pinned commit: <full 40-char SHA>. Files: apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/{llm,tool,user}.py. Modifications: integrated with Google ADK callback system in sibling wrapper modules (no edits to vendored files themselves).`
- `apps/chaoslab-agent/tests/unit/injector/faults/__init__.py` — NEW — empty marker
- `apps/chaoslab-agent/tests/unit/injector/faults/test_vendored_smoke.py` — NEW — ≥6 smoke tests asserting the vendored modules import without error, expose the symbols downstream wrappers will consume (e.g., chaos builder classes from `llm.py` / `tool.py` / `user.py`), and do NOT raise on module load. The test does NOT exercise behavior — that's stories 5.2-5.5. ~80 lines.
- `scripts/check_max_lines.py` — UPDATE only if the existing exclusion list misses `_vendored/` — confirm `_vendored/` is in the excluded paths per `coding-standards.md` §"Excluded" + ADR-010. NO modification if already covered.
- `pyproject.toml` (workspace root) — UPDATE — confirm `[tool.coverage.run] omit` already contains `*/_vendored/*` per `coding-standards.md`; NO modification if already present.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the NOTICE file exists at the repo root
When `grep "deepankarm/agent-chaos" NOTICE` runs
Then exit code is 0

Given the NOTICE file has a pinned commit SHA
When `grep -oE "Pinned commit: [0-9a-f]{40}" NOTICE` runs
Then exit code is 0 and the matched SHA is a real commit on `https://github.com/deepankarm/agent-chaos` (verified by gh api repos/deepankarm/agent-chaos/commits/<SHA> returning HTTP 200)

Given the vendored README references the SHA
When `grep -oE "[0-9a-f]{40}" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/README.md` runs
Then the matched SHA equals the SHA in NOTICE

Given the three vendored files exist
When `test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/llm.py && test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/tool.py && test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/user.py` runs
Then exit code is 0

Given the vendored modules import cleanly
When `uv run python -c "from chaoslab_agent.injector.faults._vendored import llm, tool, user; print('ok')"` runs
Then stdout contains "ok" and exit code is 0

Given the smoke-test suite runs
When `uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_vendored_smoke.py -v` runs
Then ≥6 tests pass and exit code is 0

Given `_vendored/` is correctly excluded from the 400-line guard per ADR-010
When `python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/` runs
Then exit code is 0 even if a vendored file exceeds 400 lines

Given the LICENSE file at the repo root is Apache-2.0
When `grep -E "Apache License" LICENSE` runs
Then exit code is 0 (license compatibility precondition for the vendor)
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# 1) NOTICE has the attribution + pinned SHA
grep -q "deepankarm/agent-chaos" NOTICE
SHA=$(grep -oE "Pinned commit: [0-9a-f]{40}" NOTICE | awk '{print $3}')
[ -n "$SHA" ] || { echo "no pinned SHA in NOTICE"; exit 1; }

# 2) The SHA is a real commit (online verification)
gh api "repos/deepankarm/agent-chaos/commits/${SHA}" --jq .sha | grep -q "${SHA}"

# 3) Vendored README mirrors the SHA
grep -q "${SHA}" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/README.md

# 4) Vendored files exist + import cleanly
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/llm.py
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/tool.py
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/user.py
uv run python -c "from chaoslab_agent.injector.faults._vendored import llm, tool, user; print('ok')" | grep -q ok

# 5) Smoke tests pass with ≥6 cases
uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_vendored_smoke.py -v
TEST_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_vendored_smoke.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$TEST_COUNT" -ge 6 ] || { echo "expected ≥6 smoke tests, got $TEST_COUNT"; exit 1; }

# 6) 400-line guard skips _vendored (ADR-010)
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/

# 7) LICENSE precondition (Apache-2.0)
grep -q "Apache License" LICENSE

# 8) Coverage omit confirmed
grep -q "_vendored" pyproject.toml

echo "story-5.1 verification: PASS"
```

---

## Notes for coding agent

### How to pin the SHA (do this FIRST, then copy)

```bash
# Resolve a real, recent SHA. Use main branch HEAD at the moment of vendoring.
SHA=$(gh api repos/deepankarm/agent-chaos/commits/main --jq .sha)
echo "Pinning to ${SHA}"
# Copy each file at that exact ref:
gh api "repos/deepankarm/agent-chaos/contents/src/agent_chaos/chaos/llm.py?ref=${SHA}" --jq .content | base64 -d > apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/llm.py
gh api "repos/deepankarm/agent-chaos/contents/src/agent_chaos/chaos/tool.py?ref=${SHA}" --jq .content | base64 -d > apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/tool.py
gh api "repos/deepankarm/agent-chaos/contents/src/agent_chaos/chaos/user.py?ref=${SHA}" --jq .content | base64 -d > apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/user.py
```

### NOTICE block — exact template to append

```
================================================================================
Third-party code: deepankarm/agent-chaos
================================================================================

This project includes code from `deepankarm/agent-chaos`
(https://github.com/deepankarm/agent-chaos), licensed under Apache License 2.0
(https://www.apache.org/licenses/LICENSE-2.0).

Pinned commit: <FULL_40_CHAR_SHA>
Copied on: 2026-06-02
Files included:
  apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/llm.py
  apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/tool.py
  apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/user.py

Modifications: integrated with Google ADK callback system in sibling wrapper
modules (apps/chaoslab-agent/src/chaoslab_agent/injector/faults/*.py).
The vendored files themselves are unmodified verbatim copies.
```

### Architecture context

- **ADR-006 (`architecture.md`):** authorizes the vendor with locked attribution + integration target. This story executes ADR-006 verbatim.
- **License compatibility:** ChaosLab is Apache-2.0; agent-chaos is Apache-2.0 → direct vendor permitted with attribution per §4 of the Apache 2.0 license.
- **§14 carve-out:** vendored code is NOT subject to the no-`mock`/`fake` rule even if upstream uses those words (it's third-party code with NOTICE attribution). The `_vendored/` path is in the exclusion list per `coding-standards.md` §"Excluded".
- **400-line carve-out:** `_vendored/` is also excluded from `scripts/check_max_lines.py` per ADR-010 + `coding-standards.md`. Verify before submitting — if a vendored file is >400 lines, the test in story 1.3 must already be configured to skip `_vendored/`.
- **Coverage carve-out:** `pyproject.toml` `[tool.coverage.run] omit = ["*/_vendored/*", ...]` ensures vendored code is not counted toward the 80% threshold.
- **DO NOT** ruff/format the vendored files. Configure `.ruff.toml` extend-exclude or per-directory config if ruff trips on them.

### Smoke-test pattern (sample)

```python
# apps/chaoslab-agent/tests/unit/injector/faults/test_vendored_smoke.py
import importlib
import pytest


def test_vendored_llm_imports() -> None:
    mod = importlib.import_module("chaoslab_agent.injector.faults._vendored.llm")
    assert mod is not None


def test_vendored_tool_imports() -> None:
    mod = importlib.import_module("chaoslab_agent.injector.faults._vendored.tool")
    assert mod is not None


def test_vendored_user_imports() -> None:
    mod = importlib.import_module("chaoslab_agent.injector.faults._vendored.user")
    assert mod is not None


def test_vendored_init_is_marker_only() -> None:
    mod = importlib.import_module("chaoslab_agent.injector.faults._vendored")
    assert hasattr(mod, "__name__")


def test_vendored_readme_pins_sha() -> None:
    import re, pathlib
    readme = pathlib.Path("apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/README.md")
    assert readme.exists()
    assert re.search(r"\b[0-9a-f]{40}\b", readme.read_text()) is not None


def test_notice_pins_same_sha() -> None:
    import re, pathlib
    notice = pathlib.Path("NOTICE").read_text()
    assert "deepankarm/agent-chaos" in notice
    assert re.search(r"Pinned commit: [0-9a-f]{40}", notice) is not None
```

### Known pitfalls

- **Do NOT auto-format `_vendored/` with ruff.** Configure `extend-exclude = ["**/_vendored/**"]` if ruff is the one project-wide style check that would touch these files. The diff vs upstream must be byte-identical.
- **Do NOT add docstrings, type fixes, or "minor cleanups"** to vendored code. If a vendored file needs a fix, fork it into a sibling non-vendored module and import from there. The whole point of vendoring is provenance — once you edit, you've forked.
- **Do NOT import from `_vendored/` outside `chaoslab_agent.injector.faults`.** The wrapper modules (5.2-5.5) are the single ingress point.
- **The downstream wrapper API** (`MalformedToolOutputFault`, `PromptInjectionFault`, etc. in stories 5.2-5.5) is what the rest of the codebase imports. `_vendored/` is implementation detail.
- **Cross-reference:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/01-reference-implementations.md` §2 (full inventory of vendored primitives + license confirmation) + §7 Move 2 (rationale: saves 3-4 days). `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/04-fault-injection-eval.md` §8.2 (concrete injection code for F1-F4 that wraps these vendored primitives).
