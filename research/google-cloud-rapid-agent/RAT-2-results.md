# RAT-2 Results — Phoenix Audit Group 1 Architecture Validation

**Date executed:** 2026-06-04
**Executed by:** Claude (autonomous, with Abu-provided Phoenix credentials)
**Project under test:** Phoenix Audit (the AI agent that audits other AI agents — Arize track of the Google Cloud Rapid Agent Hackathon)
**Smoke code:** `research/google-cloud-rapid-agent/rat-2-phoenix-audit/`
**Previous RAT:** `RAT-results.md` (2026-06-03 — validated Phoenix-side primitives only)

---

## TL;DR

🟢 **PASS — all three demo-critical architectural assumptions are real.** Phoenix Audit's wedge survives empirical validation:

1. ✅ **Test 1 — Cross-tenant Phoenix trace ingest works.** A Customer's target agent (separate process, separate env) can ship OpenInference traces into a Phoenix project using just the API key + endpoint, and we can read them back. End-to-end latency: **1.37s**.
2. ✅ **Test 2 — A2A round-trip works.** ADK 2.1.0's experimental `to_a2a()` + `RemoteA2aAgent(AgentCard.from_url(...))` correctly delivers a prompt from Phoenix Audit (client) to a target (subprocess), gets a canned response back, and lands traces in Phoenix on both sides.
3. ✅ **Test 3 — Trace clustering works (the cascade-flip).** Phoenix Python client returns all span levels (root + nested) as a DataFrame; differential set-analysis between passing-trace span-sets and failing-trace span-sets correctly identifies the missing protective span (`verify_benefits`) as the common upstream cause of all three failures.

**However, two real risks emerged that demand spec revisions before we ship the demo claims:**

🚨 **Risk A: A2A round-trip latency is ~16s for a no-LLM, localhost call.** Spec claimed "47 tests in 90 seconds." Reality at current performance: 47 × 16s = 12+ minutes. We need to either parallelize hard, drop the test count to ~8, OR change the headline number. **The "90 seconds" demo metric is empirically NOT supported by the wire performance we measured today.**

🚨 **Risk B: Phoenix Cloud free tier is 25,000 spans/month; one round-trip emits 41 spans.** Math: 41 × 47 tests = 1,927 spans per audit → ~13 audits/month on free tier. Demo recording alone would consume ~10% of monthly quota. Mitigation candidates: self-host Phoenix in Docker for dev (and the demo, if needed), aggressively filter span volume, drop test count.

**Six implementation findings (IF-9 through IF-14) logged in this document and slated for `docs/audit-notes.md` synthesis.**

---

## Test 1 — Cross-tenant Phoenix trace ingest

**Hypothesis:** A separate process with our Phoenix API key + endpoint can ship OpenInference-shaped spans into our Phoenix project and we can read them back.

**Smoke script:** `rat-2-phoenix-audit/test1_cross_tenant_ingest.py`

**What happened:**

```
[INFO] Phoenix endpoint: https://app.phoenix.arize.com/s/blockchainoracle-dev
[INFO] API key present: yes (105 chars)
[INFO] Phoenix project (for THIS test run): rat2-test1-cross-tenant-097a6329
[OK] phoenix.otel.register() returned a tracer provider
[OK] Span emitted with marker=rat2-marker-e13a98396073
[OK] Project found server-side: id=UHJvamVjdDo2
[OK] Span landed in Phoenix. server-side span_id=U3BhbjoxNTA4
[OK] Roundtrip latency (emit → server-side visible): 1.37s
[PASS] Test 1 — cross-tenant Phoenix ingest
```

**Verdict:** Cross-tenant ingest is real. Phoenix Audit's foundational assumption — that the Customer's target agent ships traces to a Phoenix project Phoenix Audit can read — is validated. 1.37s emit-to-visible roundtrip is fast enough for the live audit UI.

**Server-side artifact:** project `UHJvamVjdDo2`, span `U3BhbjoxNTA4`, viewable at `https://app.phoenix.arize.com/s/blockchainoracle-dev/projects/UHJvamVjdDo2`.

---

## Test 2 — A2A round-trip between Phoenix Audit and a target subprocess

**Hypothesis:** ADK 2.1.0's `to_a2a()` + `RemoteA2aAgent(AgentCard.from_url(...))` can deliver a prompt from Phoenix Audit's Tester to a target running in a SEPARATE process and return a response. Traces flow on both sides.

**Smoke scripts:**

- `rat-2-phoenix-audit/test2_target_server.py` — the target ADK agent (no LLM, canned response) launched as a subprocess
- `rat-2-phoenix-audit/test2_a2a_roundtrip.py` — the Phoenix Audit-side client + driver

**What happened (after fixing two dep issues mid-RAT — see findings IF-9 and IF-10):**

```
[client] ADK instrumentor attached on client side
[client] Phoenix project for THIS run: rat2-test2-a2a-0c8fdef3
[client] Launching target subprocess: python test2_target_server.py 19999
[client] Waiting for target to bind to 127.0.0.1:19999 (≤30s)...
[client] Target ready on 127.0.0.1:19999
[client] Fetching A2A agent card: http://127.0.0.1:19999/.well-known/agent-card.json
[client] A2A call returned in 15.87s
[client] Response (first 300 chars): 'I am a deliberately-naive customer-support agent...'
[OK] Canned response content matches — A2A wire works
[OK] Phoenix has 41 total span(s) in rat2-test2-a2a-0c8fdef3; 1 carry our rat2.test marker
[PASS] Test 2 — A2A round-trip wire
```

**Verdict:** A2A wire works structurally. End-to-end, the request goes Phoenix Audit → A2A → target subprocess → A2A → back. Both sides ship traces to Phoenix.

**🚨 Real risks discovered:**

1. **15.87 second end-to-end latency for a single no-LLM round-trip on localhost loopback.** This is far slower than the spec's implied "47 tests in 90 seconds" headline. Suspected causes: AgentCard well-known JSON fetch, ADK Runner startup, ADK Session setup, internal handshake overhead. The slow path is not the network (localhost) and not an LLM (canned response).
   - **Mitigation candidates** (decisions needed before locking demo arc):
     - Parallelize: run all 47 tests concurrently via `asyncio.gather`
     - Drop count: reduce to ~6-12 tests for the demo, claim "high-signal adversarial battery" not "47 tests"
     - Connection pooling: keep one A2A connection open across all tests
     - Investigate ADK internals to find the slow step (likely `AgentCardBuilder` work)

2. **41 spans per single A2A round-trip with `openinference-instrumentation-google-adk` attached on both sides.** Phoenix Cloud free tier = 25,000 spans/month → 25,000 / (41 × 47) = ~13 audits/month. Demo recording + judging-window deployments alone could consume the quota.
   - **Mitigation candidates:**
     - Self-host Phoenix in Docker on Abu's VPS for all dev iteration (free, no quota)
     - Switch to Phoenix Cloud only for the final demo recording + judging window
     - Aggressively filter what ADK spans we ship (sampling? span_processor that drops non-load-bearing spans?)
     - Document this risk transparently in the PRD so judges aren't surprised

---

## Test 3 — Trace clustering (the cascade-flip)

**Hypothesis:** Given N failed traces and M passing traces in Phoenix (synthetically created to share a known pattern), Phoenix Audit can read them back, group by `trace_id`, and identify the COMMON upstream span that all failures share — the "3 failures collapse into 1 root cause" demo moment.

**Smoke script:** `rat-2-phoenix-audit/test3_trace_clustering.py`

**What happened (after fixing two dep + API-shape issues mid-RAT — see findings IF-11 and IF-12):**

```
[INFO] Emitting 3 FAIL + 3 PASS traces...
[OK] 6 traces emitted
[OK] Phoenix returned 15 spans for rat2-test3-clustering-40cdf983
[INFO] Span name counts:
name
check_formulary     6
adversarial_test    6
verify_benefits     3
[INFO] Grouped into 3 fail + 3 pass traces
[INFO] Spans common to ALL failing traces: {'adversarial_test', 'check_formulary'}
[INFO] Spans common to ALL passing traces: {'verify_benefits', 'adversarial_test', 'check_formulary'}
[INFO] Spans PASS has but FAIL lacks (the missing protective step): {'verify_benefits'}
[PASS] Test 3 — trace clustering
Identified root cause: 'verify_benefits' span MISSING from all 3 failing traces
```

**Verdict:** The cascade-flip is REAL. Differential analysis works at the span-set level — `pass_traces.intersection_span_set - fail_traces.intersection_span_set` correctly identifies the missing protective step. In a production audit, this generalizes to: "given N failure traces, find the span pattern they share that the passing traces do NOT share. That pattern IS the root cause cluster."

This is the demo's killer moment, validated to work on real Phoenix data.

---

## Implementation findings (IF-9 through IF-14)

To be synthesized into `docs/audit-notes.md` "Implementation findings" section.

### IF-9 — ADK 2.1.0 A2A surface is marked EXPERIMENTAL

Every call to `to_a2a()`, `A2aAgentExecutor`, `RemoteA2aAgent`, and `AgentCardBuilder` emits a `UserWarning: [EXPERIMENTAL] ... ADK Implementation for A2A support is in experimental mode and is subject to breaking changes.` The underlying A2A protocol/SDK is NOT experimental (per the warning) — only ADK's wrapper layer is.

**Implication:** any ADK release between 2.1.x and 2.2.x could break the `to_a2a()` / `RemoteA2aAgent` surface. We must pin ADK exactly (already at `>=2.1.0,<3.0.0` per spec, but worth tightening to `==2.1.0` for the hackathon submission to avoid surprise upgrades).

### IF-10 — `google-adk[a2a]` does NOT pull in `sse-starlette`

The `[a2a]` extra resolves `a2a-sdk<0.4,>=0.3.4` but does NOT include `a2a-sdk[http-server]` which would provide `sse-starlette`. When `to_a2a()` builds an `A2AStarletteApplication`, it imports `sse-starlette` at startup and fails with:

```
ImportError: Packages `starlette` and `sse-starlette` are required to use the `JSONRPCApplication`.
They can be added as a part of `a2a-sdk` optional dependencies, `a2a-sdk[http-server]`.
```

**Fix:** add `sse-starlette` directly as a dev/runtime dep (we used `uv add --dev sse-starlette` in the RAT). Do NOT add `a2a-sdk[http-server]` directly — that re-pins a2a-sdk and reintroduces audit A3's resolver conflict.

### IF-11 — Phoenix REST `/v1/projects/{id}/spans` returns only top-level spans by default

In Test 3 we initially used the raw REST endpoint and got only the 6 outer `adversarial_test` spans — missing the nested `check_formulary` and `verify_benefits` spans we needed for clustering. The Phoenix Python client's `c.spans.get_spans_dataframe(project_identifier=PROJECT_NAME)` returns ALL span levels.

**Implication:** Phoenix Audit's Reporter sub-agent (the trace-tree clustering code) must use `phoenix.client.Client().spans.get_spans_dataframe(...)` not the raw REST `/spans` endpoint.

### IF-12 — `phoenix.client.spans.get_spans_dataframe` requires pandas as a transitive dep

Phoenix's base client install does NOT include pandas. Calling `get_spans_dataframe()` raises:

```
pandas is required to use get_spans_dataframe. Install it with 'pip install pandas'
```

**Fix:** add pandas explicitly to Phoenix Audit's deps. The pandas dep is significant (~50MB install) but necessary for trace clustering.

### IF-13 — Phoenix DataFrame column layout: standard attrs flattened, custom attrs nested

Phoenix's DataFrame collapses custom attribute namespaces into a single dict-typed column. Example: spans with attributes `rat2.outcome`, `rat2.test_id`, `rat2.failure_reason` all appear in ONE column `attributes.rat2` as a Python dict per row. But standard OpenInference attributes like `tool_call.function.name` and `openinference.span.kind` each get their own dedicated column.

**Implication:** Phoenix Audit's Reporter must handle both column shapes when extracting custom attributes from spans. Code pattern:

```python
def get_custom_attr(row, namespace: str, key: str):
    nested = row.get(f"attributes.{namespace}")
    if isinstance(nested, dict):
        return nested.get(key)
    return row.get(f"attributes.{namespace}.{key}")
```

### IF-14 — A2A round-trip latency is ~16s per call (no LLM, localhost)

Recorded during Test 2: a single no-LLM, localhost-loopback A2A round-trip from Phoenix Audit's `RemoteA2aAgent` to a target's `to_a2a()` server took **15.87 seconds**. Suspected breakdown (to be measured in a follow-up RAT): AgentCard well-known fetch + ADK Runner init + Session setup + A2A handshake. None of those should be 16s on localhost.

**Implication for the PRD demo claim "47 tests in 90 seconds":** at current performance, that's 47 × 16 = ~12.5 minutes, not 90 seconds. The headline metric must be revised OR we must parallelize OR optimize OR drop the test count.

**Open action:** profile the 16s breakdown before locking the demo headline metric. The spec PRD currently claims "90 seconds." That claim is empirically unsupported as of 2026-06-04.

---

## What this means for the spec

The PRD currently says (as of the 2026-06-04 cleanup commit):

> 47 adversarial tests run against a target prior-auth agent; 3 fail; root-cause clustering collapses them into 1 cluster; hardening recipe generated in 4 seconds. Headline: _"3 failures, 1 root cause, patch in 4 seconds."_

The first half ("47 adversarial tests") and the implied "90 seconds" headline are empirically NOT supported by today's RAT. The second half — root-cause clustering collapsing 3 failures into 1, and the patch-generation moment — IS supported (Test 3 PASS).

**Recommendation: revise the PRD's measurable outcome and demo arc.** Specifically:

1. Drop "47 adversarial tests" to a smaller number that we can actually run inside a 90-second demo window. Realistic at current performance: ~6 tests parallel, or ~8 sequential if we parallelize.
2. Update the "90 seconds" implied wall-clock claim. Honest options: "under 2 minutes," "under 5 minutes," or "real-time as you watch."
3. Keep the cascade-flip moment exactly as is — Test 3 proves it works.
4. Add a "Phoenix Cloud quota considerations" note to architecture.md acknowledging the 13-audit/month free-tier ceiling.

OR: invest engineering effort in the latency root-cause investigation BEFORE locking the spec. The 16s number is so far above expectation that it's likely a fixable issue (warm connection pool, skip AgentCard re-fetch, parallel test dispatch).

---

## Cross-references

- `RAT-results.md` — RAT-1 (2026-06-03): Phoenix-side validation only
- `brainstorm/21-trust-auditor-architecture.md` — the architecture this RAT was validating
- `docs/PRD.md` §"Demo moment" — the claims that need revision
- `docs/audit-notes.md` "Implementation findings" — destination for IF-9 through IF-14

---

## Status of Group 2 and Group 3 RATs (not yet executed)

**Group 2 (recoverable risks — fallback available):**

- Cloud KMS signing arbitrary PDF / JSON blobs
- GitLab MR hybrid (python-gitlab + official MCP `create_merge_request`)
- Phoenix `ClassificationEvaluator` on `gemini-3.5-flash` returning meaningful pass/fail on adversarial inputs (depends on Gemini key / Vertex ADC)

**Group 3 (low-risk-but-untested, can move to story-level smoke):**

- 3-line OpenInference snippet for LangChain / CrewAI / OpenAI Agents SDK (per-framework verification)
- Phoenix Cloud rate-limit behavior during the burst of a real audit (related to IF-14 risk B)
- EU AI Act Annex IV PDF rendering from real Phoenix data (templating layer)

Recommendation: pause RAT execution here. Abu to decide whether Group 2 runs now (before spec revisions) or after spec revisions land. Group 3 can be folded into the relevant build stories.
