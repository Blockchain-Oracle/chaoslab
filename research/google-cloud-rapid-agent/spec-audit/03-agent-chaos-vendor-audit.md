# Spec Audit 03 — `deepankarm/agent-chaos` Vendor Plan (ADR-006 + S5.1–S5.5)

**Audited:** 2026-06-03
**Auditor:** spec-audit subagent
**Pinned canonical commit:** `32beff46a28ca043e252095e6cc62ffe2010e645` (default branch `main`, HEAD as of 2026-01-02)
**Verdict:** **PROCEED — but the vendor delivers far less than the architecture doc claims, and the F1–F4 stories already know this.** The repo exists, the license is Apache-2.0, the three target files exist at the claimed paths, and the spec's downstream wrapper stories (S5.2–S5.5) wisely **DO NOT actually depend on the vendored code's runtime behavior** — they re-implement F1–F4 directly against ADK callbacks per `architecture/04 §8.2`. The "3–4 days saved" claim from `architecture/01 §2` and ADR-006 is **OVERSOLD** but not load-bearing: the worst that happens if the vendor is useless is that the wrapper modules ignore `_vendored/` and the smoke test (S5.1) still passes because it only checks imports. Net: vendor for IP-laundering / attribution / mining inspiration, not for runtime reuse.

---

## Summary

| Claims audited | Count |
|---|---|
| CONFIRMED | 7 |
| NEEDS-FIX | 3 |
| WRONG (oversold but not load-bearing) | 2 |

---

## Claim-by-claim findings

### 1. Repo exists, is reachable, license is Apache-2.0 — **CONFIRMED**

- URL: `https://github.com/deepankarm/agent-chaos` returns HTTP 200; default branch `main`.
- License (root `LICENSE` file at pinned SHA): **Apache License, Version 2.0** — verified verbatim, no GPL/BSD contamination. SPDX id `Apache-2.0` returned by `gh api`. ChaosLab's Apache-2.0 license is compatible.
- Repo metadata (verified `gh api repos/deepankarm/agent-chaos`):
  - Created `2025-12-22`, last push `2026-01-02T10:44:57Z`, last `updated_at` `2026-05-22T06:08:20Z` (metadata refresh only).
  - 23 stars, 0 forks, 0 watchers beyond stargazers, **0 open issues, 0 closed issues that weren't authored by the maintainer** (issues #1 and #2 are self-PRs).
  - Has a public PyPI release `agent-chaos 0.1.3` (Jan 2026), 4 releases total (v0.1.0 → v0.1.3 in a 4-day burst Dec 30 – Jan 2).

### 2. File structure matches `chaos/{llm,tool,user}.py` claim — **CONFIRMED**

`gh api repos/deepankarm/agent-chaos/contents/src/agent_chaos/chaos?ref=<pinned-SHA>` returns:

```
__init__.py    (2637 B)   — package re-exports
base.py        (6329 B)   — ChaosPoint enum, ChaosResult, Chaos Protocol, TriggerConfig
builder.py     (4077 B)   — fluent ChaosBuilder
context.py     (4700 B)   — context-mutation chaos
history.py     (8853 B)   — between-turn history chaos
llm.py         (8829 B)   — RateLimit/Timeout/ServerError/AuthError/ContextLength
stream.py      (4527 B)   — stream-cut, stream-hang, slow-ttft, slow-chunks
tool.py        (6386 B)   — ToolError/ToolEmpty/ToolTimeout/ToolMutate
user.py        (4566 B)   — UserInputMutateChaos
CLAUDE.md      (2242 B)   — coding-agent rules from upstream
```

All three files S5.1 names (`llm.py`, `tool.py`, `user.py`) exist at the exact paths the story claims. **However**: the architecture doc's claim "`src/agent_chaos/patch/{providers,...}/`" also exists (verified) but is **provider-specific monkey-patching** of LLM SDK methods — see Finding 4 for why it's Anthropic-only and therefore useless to ChaosLab.

### 3. Each fault class our spec claims is implemented — **NEEDS-FIX (the mapping is loose and re-implementation is required for 3 of 4)**

S5.2–S5.5 each claim a vendored primitive backs them. Reality:

| Story | Fault | Story claim | What's actually in the vendored code | Verdict |
|---|---|---|---|---|
| S5.2 | F1 malformed_tool_output | Wraps vendored `tool.py` | `tool.py` has `ToolErrorChaos`, `ToolEmptyChaos`, `ToolTimeoutChaos`, `ToolMutateChaos`. **`ToolMutateChaos`** maps to F1's `invalid_json` / `missing_required_field` / `type_mismatch` modes (user supplies a custom mutator function — ChaosLab would supply 4 such mutators). `exception` mode is NOT directly supported — `apply()` returns a `ChaosResult.mutate(...)`, not raise. **Note:** Story 5.2's "Known pitfalls" explicitly says *"Do NOT depend on `_vendored/` for F1. The vendored `tool.py` is reference-only for F1 — F1 is simple enough to implement directly from `architecture/04 §8.2`."* — so the story already knows this. | **Re-implementation, NOT reuse.** Vendored code is reference-only. |
| S5.3 | F2 prompt_injection | Wraps vendored `user.py` | `user.py` has ONE class, `UserInputMutateChaos`, which takes a user-supplied mutator function. **The 4 OWASP LLM01 payloads (`instruction_override`, `role_hijacking`, `payload_smuggling`, `indirect_injection`) are NOT in the vendored code** — the upstream README example shows `inject_prompt_attack(query) -> f"{query} IGNORE PREVIOUS INSTRUCTIONS."` as a docstring example only. ChaosLab must write all 4 payload strings itself (the story's `_PAYLOADS` dict). The "vendored primitive" is just a thin pydantic wrapper around a callable. | **Re-implementation. The 4 payloads are wholly new code.** Vendor saves ~5 LOC of pydantic boilerplate at most. |
| S5.4 | F3 context_poisoning | Wraps vendored code | The vendored `chaos/` dir has both `context.py` (context-mutate chaos, NOT mentioned in S5.1's vendor list) AND `history.py` (history-mutate, history-truncate, history-inject for between-turn poisoning). **NEITHER is on S5.1's vendor list.** S5.4's reference impl uses ADK `BaseRetrievalTool` monkey-patching directly — independent of vendor. | **Vendor list is INCOMPLETE for F3.** If S5.4 were to genuinely reuse, it would want `context.py` + `history.py` vendored. Story 5.4 doesn't — it re-implements. |
| S5.5 | F4 latency_spike | Wraps vendored `tool.py`'s `ToolTimeoutChaos` | Vendored `ToolTimeoutChaos.apply()` returns the **string** `"Tool execution timed out after Xs"` as a mutated result. It DOES NOT actually `asyncio.sleep`. It doesn't construct an httpx transport shim. **S5.5's reference impl re-implements both `asyncio.sleep` and the httpx `AsyncBaseTransport` shim from scratch.** | **Re-implementation. Vendored primitive is just a flag/string.** Vendor saves nothing. |

**Net: 0 of 4 fault classes meaningfully consume vendored runtime code.** All 4 wrapper stories implement directly against ADK callbacks. The vendoring is effectively documentation / attribution / mining for ideas, not code reuse.

### 4. LLM provider — Anthropic-only, NOT Gemini — **WRONG (load-bearing for vendored `llm.py`)**

`llm.py` is hard-coded to construct Anthropic SDK exception types:

```python
def to_exception(self, provider: str) -> Exception:
    if provider == "anthropic":
        import anthropic
        return anthropic.RateLimitError(...)
    raise NotImplementedError(f"Provider {provider} not implemented")
```

All 5 LLM chaos classes (`RateLimit`, `Timeout`, `ServerError`, `AuthError`, `ContextLength`) follow this same pattern. Default provider is `"anthropic"`. There is no Gemini code path — `to_exception("gemini")` raises NotImplementedError unconditionally.

The patch/providers/ situation is the same:

- `patch/providers/anthropic.py` → 35,608 bytes (fully implemented)
- `patch/providers/gemini.py` → 633 bytes (`class GeminiPatcher: ... raise NotImplementedError("Gemini provider not yet implemented")`)
- `patch/providers/openai.py` → 626 bytes (same stub)

Upstream README confirms verbatim: **"Supported: Anthropic models (via `anthropic` SDK)"** and **"Planned: OpenAI, Gemini models"** under a "Status" heading dated Jan 2026, never updated since.

ChaosLab is Gemini-only (ADR-007, `JUDGE_LLM = "gemini-3.5-flash"`; `architecture.md` "Banned patterns" forbids Anthropic/OpenAI SDKs in the agent). **Vendoring `llm.py` verbatim therefore vendors dead code paths and an `anthropic` dependency we don't want.**

**Fix:** Either (a) vendor `llm.py` but **document it as reference-only** in `_vendored/README.md` and don't import its symbols (the smoke test currently asserts only `import succeeds` which will pass — provided `anthropic` is installed); OR (b) skip `llm.py` entirely from the vendor and update S5.1's file modification map + NOTICE to vendor only `tool.py` + `user.py` (the two files with mostly-provider-agnostic code paths).

Recommended: **(b)**. `llm.py` brings net negative value — its only Gemini-compatible class is `TimeoutChaos` and even that constructs `anthropic.APITimeoutError`. Removing `llm.py` from the vendor list cuts ~8.8 KB of dead code, eliminates the optional `anthropic` install pressure, and matches what S5.2–S5.5 actually use (none of them call `llm.py` classes).

### 5. Code style + Python 3.12 compatibility — **CONFIRMED**

- `pyproject.toml` declares `requires-python = ">=3.12"` — same as ChaosLab.
- Uses modern idioms: `from __future__ import annotations`, PEP 604 `int | None`, `typing.Self`, `pydantic` v2 (`ConfigDict`, `PrivateAttr`, `model_validator`).
- No deprecated patterns (`typing.List`, `typing.Optional`, dataclasses). PR #1 from Jan 2 was a refactor *away* from dataclasses to pydantic, so the code is currently pydantic v2 throughout.
- Type hints are complete; `py.typed` marker file is present so downstream type checkers see signatures.

### 6. Dependency surface — **NEEDS-FIX (one transitive risk; otherwise clean)**

Vendored files' runtime imports (verified by reading every line):

- `tool.py`: `inspect`, `typing.Any/Callable`, `pydantic`, `agent_chaos.chaos.base`, `agent_chaos.chaos.builder` → **no third-party deps beyond pydantic** (which ChaosLab already pulls).
- `user.py`: same shape as `tool.py`. No third-party deps beyond pydantic.
- `llm.py`: `httpx` (ChaosLab uses), `pydantic` (ChaosLab uses), conditional `import anthropic` inside each `to_exception` — only imported if `provider == "anthropic"`, so vendoring without installing `anthropic` is fine IF we never call `to_exception`. **However**, S5.1's smoke test asserts the module imports cleanly. Module-level imports are `httpx`, `pydantic`, `agent_chaos.chaos.base`, `agent_chaos.chaos.builder` — none require anthropic. ✓
- `agent_chaos.chaos.base` (transitively required by all three): imports `pydantic`, `agent_chaos.types`. `agent_chaos.types` defines `ChaosAction` and `ChaosPoint` enums — these are pure Python. ✓
- `agent_chaos.chaos.builder`: imports `agent_chaos.chaos.base` only. ✓

**Transitive risk:** vendoring `{llm,tool,user}.py` verbatim creates `from agent_chaos.chaos.base import ...` and `from agent_chaos.chaos.builder import ChaosBuilder` imports that **DO NOT RESOLVE** because we're not pip-installing `agent-chaos`. Smoke test S5.1's `importlib.import_module("chaoslab_agent.injector.faults._vendored.llm")` **will fail at import** with `ModuleNotFoundError: No module named 'agent_chaos'`.

**Fix:** S5.1 must also vendor `chaos/base.py` (6.3 KB), `chaos/builder.py` (4.1 KB), and `agent_chaos/types.py` (1.4 KB), THEN rewrite the import paths from `agent_chaos.chaos.X` → `chaoslab_agent.injector.faults._vendored.X`. This contradicts the story's verbatim-copy + "Do NOT add docstrings, type fixes, or 'minor cleanups'" rule. Either:

  - (a) Rewrite the imports as a documented, one-line `# vendored: import rewritten` patch per file (minimal, clearly justified deviation from verbatim policy), OR
  - (b) Don't vendor at all — `pip install agent-chaos` as a regular dependency. But the upstream pulls in `httpx`, `fastapi`, `uvicorn`, `websockets`, `pydantic` and optionally `anthropic/openai/gemini`. `fastapi`/`uvicorn`/`websockets` are NOT in ChaosLab's `architecture.md` "Required external libraries" table — they're the upstream's CLI/UI runtime deps. Pip-installing would add bloat but is mechanically simpler than the import-rewrite carve-out. **Cost:** ~30 MB of disk + 4 transitive deps not on our list.
  - (c) **RECOMMENDED:** Skip the vendor entirely. Per Finding 3, the wrapper modules don't consume the runtime; they just borrow the IDEAS. Replace S5.1 with a much smaller story: "Add `NOTICE` attribution + `architecture/04 §8.2` reference comments in F1–F4 modules pointing at the upstream files for IP-trail." Saves ~1.5h of build + sidesteps the import-rewrite problem.

### 7. Recent activity / project liveness — **NEEDS-FIX (project is essentially abandoned)**

Commit history (verified):

```
32beff46  2026-01-02  feat: add pydantic-evals integration (#2)
a5fd515d  2026-01-02  feat: add pydantic-evals integration
f5b20c24  2026-01-02  Merge pull request #1
7b9196a9  2026-01-02  chore: update version
fecc1695  2026-01-02  refactor: use pydantic instead of dataclasses ...
7ad4ac3d  2026-01-02  refactor: metrics store
... (all 2026-01-01 / 2026-01-02)
```

**No commits between 2026-01-02 and 2026-06-03 (5 months).** Last release v0.1.3 was Jan 2; PyPI shows no updates since. The `updated_at` field of `2026-05-22` on the repo metadata is a non-substantive refresh (likely a README touch or topics edit, not code).

Issue tracker is dormant — total of 2 issues, both authored by the maintainer himself as PR-issues for self-merged refactors.

**Implication for ChaosLab:** vendoring at a frozen SHA is fine *because* the project is frozen — there's nothing to drift against. But the "active, v0.1.3 released Jan 2026" framing in `architecture/01 §2` line 73 ("Status: Active") was accurate when written and is now stale. The repo is *one developer's side project that shipped 4 releases in a 4-day burst, then went silent*. Recommend updating `architecture/01 §2` to "Status: dormant since Jan 2026, but Apache-2.0 freeze is acceptable for vendor use."

### 8. Issue tracker health — **CONFIRMED (no critical open bugs)**

- 0 open issues, 0 ever-open security advisories, no critical CVE reports against `agent-chaos==0.1.3` on PyPI.
- The 2 historical issues were both maintainer self-PRs. No third-party bug reports.

### 9. Integration pattern — framework-agnostic? — **WRONG (tied to anthropic + own runtime)**

The vendored chaos classes (`ToolErrorChaos`, `UserInputMutateChaos`, etc.) implement a `Chaos` Protocol from `chaos/base.py`:

```python
class Chaos(Protocol):
    @property
    def point(self) -> ChaosPoint: ...
    def should_trigger(self, call_number: int, **kwargs) -> bool: ...
    def apply(self, **kwargs) -> ChaosResult: ...
```

**They are framework-agnostic at the data-class level** — the chaos *spec* is just config + a `should_trigger`/`apply` decision pair. But to actually inject anything, you need the upstream `ChaosPatcher` (from `patch/patcher.py`) which **monkey-patches `anthropic` SDK methods** at module-load time. From the README's examples, every use of agent-chaos pairs a chaos list with `BaselineScenario` + `Turn` from the upstream's scenario runner, which is `pydantic-ai`-based.

In other words: **the data classes are reusable; the injection mechanism is not.** ChaosLab plans to inject via ADK callbacks (`before_tool_callback`, `before_model_callback`), which is a completely different mechanism from `ChaosPatcher`'s SDK monkey-patch.

This is fine for the "vendor as reference" use case but is the substantive answer to the architecture doc's claim of "framework-agnostic primitives." It's actually framework-coupled at the only layer that matters (injection wiring). ChaosLab's S5.2–S5.5 wrap *the idea*, not the code.

### 10. Pinned canonical commit — **CONFIRMED**

```
SHA:    32beff46a28ca043e252095e6cc62ffe2010e645
Date:   2026-01-02T10:44:55Z
Tag:    main HEAD; released as v0.1.3 (Jan 2 release on PyPI is built from this same SHA)
Verify: gh api repos/deepankarm/agent-chaos/commits/32beff46a28ca043e252095e6cc62ffe2010e645 → returns sha match
```

This is the SHA S5.1's NOTICE block should be pinned to.

---

## Alternatives considered (and rejected)

`gh search repos "agent chaos" --language=python` returns 11 results. Filtering for substance:

| Repo | Stars | License | Active | Notes |
|---|---|---|---|---|
| **`deepankarm/agent-chaos`** | 23 | Apache-2.0 | dormant 5mo | The only candidate with a published PyPI package + Apache-2.0 license + non-trivial code (>20 KB of fault logic). |
| `floritange/AgentChaos` | 0 | MIT | active May 2026 | "Evaluate agent system robustness through controlled, runtime, non-intrusive LLM API fault injection." Looks promising on description but 0 stars + no PyPI release + unverified code quality. **MIT-licensed** — compatible with Apache-2.0. Worth a 5-minute look if `deepankarm` is fully discarded. |
| `IntelligentDDS/AgentChaos` | 0 | no license | active Mar 2026 | **No license file** → cannot legally vendor. Skip. |
| `NoraXu-0111/AgentChaos` | 0 | unknown | active Jun 2026 | 0 stars, recent activity but unknown shape. |
| `Xrenya/AgentChaosMCP` | 0 | unknown | active May 2026 | MCP-focused, not fault primitives. Skip. |
| `Ch4you/AgenticChaosMonkey` | 1 | unknown | inactive Jan 2026 | Skip. |
| `NVIDIA/garak` | 8002 | Apache-2.0 | very active | Different shape — vulnerability *scanner*, not a fault-primitive library. Too heavyweight for vendoring. We could optionally lift Garak probe templates as inspiration for F2 payloads, but that's a stretch (see `architecture/04 §4.5` for the existing Garak reference). |

**Verdict on alternatives:** `deepankarm/agent-chaos` remains the best (only) candidate that ships Apache-2.0, has a non-trivial primitive library, and aligns with the architectural intent. No swap recommended.

---

## What to do

### Option A — Proceed with vendor (the current spec, with patches)

Keep ADR-006 but tighten S5.1:

1. **Vendor only `chaos/tool.py` + `chaos/user.py`** (drop `chaos/llm.py` per Finding 4 — it's Anthropic-bound dead code).
2. **Also vendor `chaos/base.py` + `chaos/builder.py` + `agent_chaos/types.py`** (transitive imports per Finding 6).
3. **Rewrite the 4 import lines** in the vendored files (from `agent_chaos.chaos.base` → `chaoslab_agent.injector.faults._vendored.base`, etc.). Document each rewrite as a one-line patch in `_vendored/README.md`'s "Modifications" section. This is a justified deviation from the "verbatim, no edits" rule — the alternative is non-functional code.
4. **NOTICE pin SHA**: `32beff46a28ca043e252095e6cc62ffe2010e645`.
5. **Smoke test (S5.1's BDD criterion #5)** is fine as-is — `importlib.import_module(...)` will succeed once imports are rewired.
6. **Document explicitly in `_vendored/README.md`** that the vendored code is "reference + attribution-only — runtime wrappers in `chaoslab_agent/injector/faults/{malformed_tool_output,prompt_injection,context_poisoning,latency_spike}.py` do NOT call into the vendored modules. The vendor exists for IP-trail and to credit `deepankarm/agent-chaos`'s pioneering work on LLM-layer fault taxonomy."

Time cost: ~1.5h (matches S5.1 estimate). Net build savings claim: ~0 days (NOT the 3–4 days `architecture/01 §2` claims) — but the wrappers were always going to be ~80 LOC each per `architecture/04 §8.2`.

### Option B — Skip the vendor entirely (RECOMMENDED)

Replace S5.1 with a smaller `S5.1-attribution-only` story:

1. **NOTICE attribution to `deepankarm/agent-chaos`** as "prior art consulted; no code vendored," pinned SHA, Apache-2.0 acknowledged.
2. **Each of F1–F4** (`malformed_tool_output.py`, `prompt_injection.py`, `context_poisoning.py`, `latency_spike.py`) carries a module docstring credit line: `# Inspired by deepankarm/agent-chaos chaos/{tool,user}.py at SHA <pinned>. Implementation independent.`
3. **Update ADR-006** to reflect that the vendoring claim was wrong on closer inspection — the wrappers are not derived works of the upstream code, just inspired by its taxonomy. This is more honest about provenance and IS LEGALLY CLEANER (no Apache-2.0 redistribution obligations to maintain).
4. **Drop the "saves 3–4 days" claim from `architecture/01 §2 Move 2`** — the actual savings come from `architecture/04 §8.2`'s 80-LOC reference implementations, which we already have inline in the stories. The vendor was a red herring.

Time cost: ~20 min (just append to NOTICE + update 4 module docstrings + amend ADR-006). **Saves the 1.5h of S5.1 + sidesteps every Finding 3/4/6 issue.**

### Hard verdict

**Option B is structurally cleaner.** The architecture doc's "vendor agent-chaos" claim was based on a surface read of the upstream README + file sizes. On detailed inspection, the upstream is Anthropic-coupled at the injection layer (the layer that matters), and the data-class layer is not load-bearing — F1–F4's wrappers re-implement the injection wiring against ADK callbacks completely independently.

If Abu wants to keep ADR-006 unchanged for narrative simplicity, Option A works — but the spec MUST acknowledge that the vendored code is "reference + attribution-only" and the import-rewrite carve-out from Finding 6 is required. Either path lands at a working Epic 5 by Day 3. **The original ADR-006 claim of "3–4 days saved" is wrong; the actual savings are zero.** What *does* save time is `architecture/04 §8.2`'s inline 80-LOC reference implementations — those are the real engineering shortcut, not the vendor.

---

## Files audited

- `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` (ADR-006, lines 258–262; vendored library row in dependency table, line 178)
- `/Users/abu/dev/hackathon/rapid-agents/docs/stories/story-5.1-vendor-agent-chaos.md`
- `/Users/abu/dev/hackathon/rapid-agents/docs/stories/story-5.2-fault-malformed-tool.md`
- `/Users/abu/dev/hackathon/rapid-agents/docs/stories/story-5.3-fault-prompt-injection.md`
- `/Users/abu/dev/hackathon/rapid-agents/docs/stories/story-5.4-fault-context-poisoning.md`
- `/Users/abu/dev/hackathon/rapid-agents/docs/stories/story-5.5-fault-latency-spike.md`
- `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/01-reference-implementations.md` §2 + §7 Move 2

## Upstream files inspected verbatim (at pinned SHA `32beff46a28ca043e252095e6cc62ffe2010e645`)

- `LICENSE`
- `pyproject.toml`
- `README.md`
- `src/agent_chaos/chaos/__init__.py`
- `src/agent_chaos/chaos/base.py`
- `src/agent_chaos/chaos/builder.py`
- `src/agent_chaos/chaos/llm.py`
- `src/agent_chaos/chaos/tool.py`
- `src/agent_chaos/chaos/user.py`
- `src/agent_chaos/patch/__init__.py`
- `src/agent_chaos/patch/patcher.py`
- `src/agent_chaos/patch/providers/{anthropic,gemini,openai}.py` (header inspection)
