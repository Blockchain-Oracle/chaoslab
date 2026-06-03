# Spec Audit Summary — ChaosLab

**Compiled:** 2026-06-03
**Scope:** 7 parallel empirical audits cross-checking the ChaosLab spec against actual library source / SDK / API surfaces.
**Total audit corpus:** 1,702 lines across `spec-audit/01-07`.

---

## Overall verdict: 🟡 **AMEND-THEN-PROCEED**

The spec's wedge, architecture shape, judging-criteria alignment, and demo plan are **all sound**. But ~11 specific claims about external libraries / SDK versions / API surfaces have drifted from current reality. Each is addressable with a targeted spec edit; none invalidate the wedge or the build plan. **Apply the 13 critical amendments below, then fire `sahil-hackathon-orchestrator`.**

**Aggregate counts** across all 7 audits:

- ✅ **~48 claims CONFIRMED** as accurate
- 🟡 **~17 claims NEEDS-FIX** (doc-hygiene, minor amendments — non-blocking)
- 🔴 **~11 claims WRONG** (load-bearing — must amend before orchestrator dispatch)

The RAT (executed earlier today) already validated 5 separate items from the original audit list. This audit found 11 more.

---

## Per-domain results

| #   | Domain                             | Verdict |   ✅ |  🟡 |  🔴 | Critical finding                                                                          |
| --- | ---------------------------------- | ------- | ---: | --: | --: | ----------------------------------------------------------------------------------------- |
| 01  | ADK + A2A source                   | AMEND   |    6 |   4 |   1 | `a2a-sdk` version pin breaks `uv sync` (S2.2 line 134)                                    |
| 02  | OpenInference packages             | AMEND   |    7 |   2 |   1 | `openinference.instrumentation.library` attribute is FABRICATED                           |
| 03  | `deepankarm/agent-chaos` vendoring | PIVOT   |    7 |   3 |   2 | "Saves 3-4 days" claim is wrong — actual savings ≈ 0                                      |
| 04  | GitLab MCP endpoint                | PIVOT   |    4 |   2 |   3 | Official MCP lacks `create_branch` + `create_or_update_file` — S6.6 not viable as written |
| 05  | Frontend stack                     | AMEND   |   11 |   3 |   2 | Next.js 15 is stale; npm `latest` is 16.2.7                                               |
| 06  | Gemini + Cloud Run + WIF           | AMEND   | many |   1 |   4 | `google-github-actions/*@v2` is 9 months stale → `@v3`                                    |
| 07  | 8 critical stories                 | CLEAN   |    6 |   2 |   0 | 12 file-path duplicates (NEW vs UPDATE conflict)                                          |

---

## 🔴 Critical amendments (MUST apply before orchestrator dispatches)

These 13 amendments fix the WRONG claims and prevent coding agents from burning cycles on bad assumptions. All are surgical (line-level edits, no architecture rewrites).

### A1. GitLab MR emitter pivot (audit-04, S6.6)

**Fix:** ADR-011 in `architecture.md` + `story-6.6-gitlab-mr-emitter.md` + `partner-gitlab.md`.

**Specific change:**

- **Keep** the official `https://gitlab.com/api/v4/mcp` for `create_merge_request` ONLY (preserves judging credit)
- **Move** branch creation + file commits to the `python-gitlab` SDK (already in deps at `architecture.md` L173). Use `POST /projects/:id/repository/branches` and `POST /projects/:id/repository/files/:file_path`.
- Update `_gitlab_mcp_client.py` to call ONLY the verified-real 16 tools the official server exposes.
- Update S6.6 BDD: the integration test must hit BOTH paths (MCP for MR, REST API for files) — and one `@pytest.mark.online` test must validate this against a real test repo before recording demo.

**Free-tier vs Premium:** Official docs say Premium/Ultimate; hackathon FAQ says trial. Test with a fresh trial account on Day 1.

### A2. `google-github-actions/*` major version bump v2 → v3 (audit-06)

**Fix:** `docs/architecture.md` ADR-009; `docs/cicd.md` lines 240, 247; `docs/stories/story-1.6-staging-deploy-workflow.md` line 56; `research/.../best-practices/02-cicd-github-actions.md` (every yaml example).

**Specific change:** sed-style replace `google-github-actions/auth@v2` → `@v3`, same for `setup-gcloud@v2`, `deploy-cloudrun@v2`. The v2 actions have been backport-only since 2025-08-28.

⚠ S1.6 hardcodes `@v2` in a regex-checked BDD acceptance criterion — coding agent would write v2 workflows on day 1 if not fixed.

### A3. Drop `a2a-sdk` explicit version pin (audit-01, S2.2)

**Fix:** `docs/stories/story-2.2-target-a2a-exposure.md` line 134.

**Specific change:** Remove `a2a-sdk>=1.1.0,<2.0.0` from the dependency list. `google-adk[a2a]` 2.1.0 transitively requires `a2a-sdk<0.4,>=0.3.4` — pinning explicitly causes a guaranteed `uv sync` resolver conflict. Let the `[a2a]` extra resolve transitively.

### A4. Next.js version: pin `^15` explicitly OR bump to 16 (audit-05)

**Fix:** `docs/architecture.md` TS library table; `docs/stories/story-7.1-nextjs-scaffold.md`.

**Recommended: bump to Next.js 16.** All patterns the spec uses (`output: 'standalone'`, App Router, `next/font`, `next/image`, SSE route handlers) work identically on 16. v16 has been mainline ~8 months. Sticking with `^15` requires explicit `next@15` pins everywhere because `pnpm add next` resolves to `^16` today.

### A5. Drop `deepankarm/agent-chaos` vendoring; use attribution-only (audit-03, S5.1)

**Fix:** ADR-006 in `architecture.md`; `docs/stories/story-5.1-vendor-agent-chaos.md`; `research/.../architecture/01-reference-implementations.md` § "Move 2".

**Specific change:** Convert S5.1 from "copy 3 files + add NOTICE" to "add NOTICE entry + module-docstring attribution credits in F1-F4 source files." Why: F1-F4 stories already reimplement against ADK callbacks directly; the vendored `llm.py` is Anthropic-only with a Gemini `NotImplementedError` stub. Net effort drops from ~1.5h to ~20 min.

**Update ADR-006 narrative:** "We considered vendoring but the upstream is Anthropic-only and dormant. Architecture/code patterns inspired by `deepankarm/agent-chaos` (Apache-2.0, attributed in NOTICE) but reimplemented natively against ADK."

### A6. Fix fabricated OpenInference attribute name (audit-02, S3.3)

**Fix:** `docs/stories/story-3.3-langchain-adapter.md` BDD criterion.

**Specific change:** Replace `span.attributes["openinference.instrumentation.library"] == "langchain"` with `instrumentation_scope.name == "openinference.instrumentation.langchain"` (the OTEL span-record field) OR `attributes["openinference.span.kind"] in {"LLM","TOOL","CHAIN"}` (the canonical OpenInference attribute).

### A7. Fix fabricated tool-call attribute name (audit-02)

**Fix:** any BDD criterion across stories that uses `tool_call.name`.

**Specific change:** Replace `tool_call.name` with `tool_call.function.name` (the real OpenInference semantic-convention attribute).

### A8. Remove `--startup-cpu-boost` fallback (audit-06, S1.6)

**Fix:** `docs/stories/story-1.6-staging-deploy-workflow.md` Notes section.

**Specific change:** Drop the "fallback to `--startup-cpu-boost` if `--cpu-boost` fails" path — the fallback flag doesn't exist in current gcloud. `--cpu-boost` is the only correct flag. Remove the "drift" failure mode from `cicd.md` §13 #5 and replace with the OIDC issuer URI trailing-slash pitfall.

### A9. Fix `gemini-3.1-pro` identifier (audit-06)

**Fix:** any reference to `gemini-3.1-pro` in spec.

**Specific change:** Replace with `gemini-3.1-pro-preview` (the current Vertex AI model ID). Note: this only affects fallback model documentation — JUDGE_LLM stays `gemini-3.5-flash` per ADR-007.

### A10. Rewrite ADR-007 cost rationale (audit-06)

**Fix:** `docs/architecture.md` ADR-007.

**Specific change:** The "17× cheaper than Pro" rationale is wrong — Pro is currently only 1.33× more than Flash. **Flash-Lite (`gemini-3.1-flash-lite`) is the real 8-11× delta vs Flash.** Two options:

- **A10a (keep current):** Update ADR-007 narrative to "Flash chosen for quality+cost balance; Pro is only ~1.3× more so the cost rationale is weaker than originally stated, but Flash is sufficient quality and avoids per-eval surprise costs."
- **A10b (consider Flash-Lite):** Switch JUDGE_LLM to `gemini-3.1-flash-lite` for the LLM-as-judge layer; saves real money. Risk: Flash-Lite quality on `tool_invocation` eval rubrics is unverified. **Recommend A10a (keep Flash) for safety; revisit Flash-Lite if cost overruns appear.**

### A11. Acknowledge ADK workflow-class deprecation (audit-01)

**Fix:** add a new ADR (ADR-012) to `architecture.md`.

**Specific change:** Document that `SequentialAgent`, `LoopAgent`, `ParallelAgent` are `@deprecated` in ADK 2.1.0 (replaced by `google.adk.workflow.Workflow`). Acknowledge: "We use the deprecated classes for hackathon speed and ADK's `filterwarnings` config suppresses the deprecation warning. Migration to `Workflow` is post-hackathon work."

### A12. Convert 12 duplicate `— NEW —` file paths to `UPDATE` (audit-07)

**Fix:** 12 story files (the later story in each pair).

**Specific change:** Audit-07 enumerated 12 file paths declared `— NEW —` by two stories each (stub-then-real lifecycle pattern). Convert the later story's `NEW` to `UPDATE` to prevent orchestrator "file already exists" conflicts. Primarily affects Dockerfiles, `pyproject.toml`, and the patcher/judge/injector `__init__.py` + `agent.py` stub-then-real chain (S4.2 → S5.7 → S6.1 → S6.3 → S6.4).

### A13. Fix S5.2's `before_tool_callback` raise pattern (audit-01)

**Fix:** `docs/stories/story-5.2-fault-malformed-tool.md`.

**Specific change:** Raising from `before_tool_callback` is undefined behavior in ADK 2.1.0. Use `on_tool_error_callback` instead. Also: the `invalid_json` malformation mode currently returns a raw string but the callback's return type is `Optional[dict]` — return `{"_invalid_json_payload": "<bad string>"}` or similar typed envelope.

---

## 🟡 Minor amendments (apply after orchestrator dispatches OR roll into the relevant story)

- **B1.** Sync 13 stories' `Depends on:` lines with `sprint-status.yaml` (yaml is canonical; stories drift)
- **B2.** S5.2 missing `story-3.2-adk-adapter` in its `Depends on:` line
- **B3.** S8.4 deps line is prose; convert to parseable ID list
- **B4.** Drop `tailwindConfig` from `prettier.config.mjs` — Tailwind 4 has no JS config (audit-05)
- **B5.** Update `framer.com/motion` URL references to `motion.dev` (audit-05)
- **B6.** Add `ANTHROPIC_API_KEY` BDD check to S7.12 visual-loop story (audit-05)
- **B7.** Add `openinference-instrumentation-openai-agents` to `architecture.md` library table (audit-02)
- **B8.** Add base `openinference-instrumentation` package to library table (provides `using_session` etc.) (audit-02)
- **B9.** Clarify S2.3 instrumented surfaces: `Runner.run_async` + `BaseAgent.run_async` (not "Agent.run() level") (audit-02)
- **B10.** Update S2.2 BDD `app.router.routes` check to use HTTP curl instead (already in shell-verification — just remove the prose claim) (audit-01)
- **B11.** Add visx peerDeps override to `pnpm.peerDependencyRules` config: `{"@visx/*": {"react": "^19"}}` (audit-05)
- **B12.** Document GitLab MCP free-tier vs Premium uncertainty as a Day-1 verification step (audit-04)
- **B13.** Add `pnpm.peerDependencyRules` block to root `package.json` (audit-05)

---

## ✅ Strongly confirmed (no changes needed)

The spec is correct about:

- **Wedge selection** (W1 ChaosLab Arize track) — RAT validated, novelty gate clean
- **Architecture shape** — 3 Cloud Run services + hybrid orchestrator + A2A target peer (Candidate B); SalesShortcut won with this exact shape
- **ADK API surface** — `LlmAgent` (with singular `instruction` field), all 4 callbacks (+ 2 bonus error callbacks), `to_a2a()`, `RemoteA2aAgent`, `Runner` all exist as documented
- **Phoenix integration** — RAT validated end-to-end; ADR-005 confirmed exactly (0 write tools in MCP); `phoenix.client.AsyncClient.experiments.run_experiment()` works as spec assumes
- **OpenInference instrumentor packages** — all 5 frameworks have current Python packages (range 2026-05-18 to 2026-06-02 release dates)
- **Cloud Run constraints** — 60-min HTTP timeout, `--cpu-boost`, `--set-secrets`, blue/green via `--no-traffic --tag=`, min-instances=1 cost all verified
- **WIF top-4 failure modes** — verified via real GitHub issues
- **Tailwind 4 stable** (`@theme` CSS-first is canonical); shadcn CLI 4.10.0 has Tailwind 4 compat
- **Framer Motion 12.40.0** — `motion.div`, stagger, `useReducedMotion` all stable v12 APIs
- **DAG sanity** — single root, no cycles, all 52 estimates ≤2h, all dep refs resolve
- **`sahil-visual-loop` skill exists** at the expected path with templates matching S7.12's file map verbatim
- **`deepankarm/agent-chaos` repo + license** — Apache-2.0 confirmed, SHA pinned, no better alternative exists (just don't VENDOR it; attribution-only)
- **~$72 cost projection** — re-verified against current 2026 pricing

---

## Recommended sequence

1. **Apply amendments A1-A13** (~2-3 hours of focused spec editing)
2. **Re-read `docs/sprint-status.yaml`** to confirm DAG sanity after edits
3. **Brief integration test on Day 1** of build:
   - Run RAT-style check on GitLab MCP (A1) before S6.6 implementation
   - Run RAT-style check on Vertex AI model resolution (A9) before E4 implementation
4. **Fire `sahil-hackathon-orchestrator`** — creates GitHub repo + 52 issues + dispatches coding agents per DAG

**Confidence:** with A1-A13 applied, the spec is buildable and the orchestrator will not waste cycles. The fixes are surgical; the architecture and wedge stay intact.

---

## What this audit caught that would have hurt the build

If we had skipped this audit and fired the orchestrator with the unamended spec:

| #   | Failure mode                                                         | Impact                                                                 |
| --- | -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 1   | `uv sync` hard-fails on day 1 due to `a2a-sdk` version conflict (A3) | Coding agent stuck; whole build blocked                                |
| 2   | S1.6 generates v2 GitHub Actions workflows (9 months stale) (A2)     | Workflows technically work but accumulate deprecation warnings + drift |
| 3   | S6.6 implementation hits "unknown MCP tool" errors at runtime (A1)   | Patcher loop broken; demo's "MR-emission" wow moment fails             |
| 4   | S5.2 raises from `before_tool_callback` (undefined behavior) (A13)   | F1 fault class silently misbehaves; demo fails                         |
| 5   | S3.3 BDD asserts on a fabricated attribute name (A6)                 | Test passes against mock, fails against real LangChain trace           |
| 6   | S5.1 spends 1.5h vendoring code that gets used nowhere (A5)          | Day 2 wasted                                                           |
| 7   | `pnpm add next` writes `"next": "^16"` not `"^15"` (A4)              | Stack mismatch; some patterns silently wrong                           |

That's ~5 hours of debugging + ~1 day of wasted scope-creep. The audit cost ~25 minutes of parallel wall-clock + this synthesis. Net save: ~5-8 hours.

---

## Updates to `docs/audit-notes.md`

The original 41 open items in `docs/audit-notes.md` were "verify on first run" / "minor coordination" items. This audit resolves 5 of them empirically (the RAT) + adds the 13 critical amendments above. The `docs/audit-notes.md` file should be appended with a "Day-3 audit findings" section summarizing A1-A13 + B1-B13, so the orchestrator's coding agents have a single canonical reference.
