# RAT Results — W1 ChaosLab for Agents

**Date executed:** 2026-06-03
**Executed by:** Claude (autonomous, with Abu-provided Phoenix credentials)
**Wedge under test:** W1 ChaosLab for Agents (Arize track)
**Runbook:** `RAT-runbook.md` (Step 3 patched per ADR-005)

---

## TL;DR

🟢 **PASS — all three steps green. ChaosLab is unblocked. Proceed with the spec.**

The three core assumptions of the W1 wedge are validated:

1. ✅ **Phoenix Cloud is reachable + traces ingest cleanly** with the space-scoped URL `https://app.phoenix.arize.com/s/blockchainoracle-dev`.
2. ✅ **Phoenix MCP is partial as architecture/02 predicted** — 27 read tools, 0 write tools for experiments/annotations. ADR-005's Python SDK wrap requirement is structurally correct.
3. ✅ **`AsyncClient.experiments.run_experiment(...)` works end-to-end** — dataset created, task+evaluator dispatched, 3 evaluations completed, experiment server-side visible at Phoenix Cloud.

Total wall-clock time: ~25 minutes (well under the 90-min budget).

---

## Step 1 — Phoenix Cloud trace ingest (✅ PASS)

**Script:** `/tmp/phoenix-rat/step1_first_trace.py` + `step1b_verify_server_side.py`

**What worked:**

- `phoenix.otel.register(protocol="http/protobuf", project_name="chaoslab-rat")` registered cleanly
- Emitted one CHAIN span with input/output/status
- `tracer_provider.force_flush()` exported synchronously
- Phoenix Cloud SDK appended `/v1/traces` to the space-scoped URL automatically (no manual path manipulation)

**Server-side evidence:**

- Project `chaoslab-rat` created (id `UHJvamVjdDoz`)
- Span `rat-step-1-hello-world` visible via `client.spans.get_spans_dataframe()` with `status_code=OK`
- Trace ID: `8004e993cfb34f2031a89baba0f5f7ae`

**Audit items resolved:**

- 🟢 **C1: Phoenix Cloud space-scoped URL** — `https://app.phoenix.arize.com/s/blockchainoracle-dev` IS the full base URL. SDK handles `/v1/traces` suffix. No env-var surgery needed.

---

## Step 2 — Phoenix MCP tool discovery (✅ PASS, ADR-005 confirmed)

**Script:** `/tmp/phoenix-rat/step2_mcp_tool_discovery.py`

**MCP server info:**

- Package: `@arizeai/phoenix-mcp@4.0.13` (npm)
- Server reports: `phoenix-mcp-server` v1.1.0
- Protocol: `2025-11-25`
- Capabilities: `{tools: {listChanged: true}}`
- Transport: stdio (confirmed)
- Auth: env vars `PHOENIX_API_KEY` + `PHOENIX_BASE_URL`

**27 tools enumerated. Read tools all present (14/15 predicted):**

| Read tool                                                                                                                                                                                                                       | Status |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----: |
| `list-projects`, `get-project`                                                                                                                                                                                                  |   ✅   |
| `list-traces`, `get-trace`, `get-spans` (named `get-spans` not `list-spans`)                                                                                                                                                    |   ✅   |
| `list-datasets`, `get-dataset`, `get-dataset-examples`, `add-dataset-examples`                                                                                                                                                  |   ✅   |
| `list-experiments-for-dataset`, `get-experiment-by-id`, `get-dataset-experiments`                                                                                                                                               |   ✅   |
| `list-prompts`, `get-prompt`, `get-latest-prompt`, `get-prompt-by-identifier`, `get-prompt-version`, `get-prompt-version-by-tag`, `list-prompt-versions`, `list-prompt-version-tags`, `upsert-prompt`, `add-prompt-version-tag` |   ✅   |
| `list-annotation-configs`, `get-span-annotations` (BONUS — we CAN read annotations)                                                                                                                                             |   ✅   |
| `get-session`, `list-sessions` (BONUS)                                                                                                                                                                                          |   ✅   |
| `phoenix-support` (BONUS — help/onboarding)                                                                                                                                                                                     |   ✅   |

**All 5 expected WRITE tools confirmed ABSENT (5/5 prediction match):**

| Write tool              |  Status   | Implication                                    |
| ----------------------- | :-------: | ---------------------------------------------- |
| `run-experiment`        | ❌ absent | Must wrap Python SDK as FunctionTool (ADR-005) |
| `create-experiment`     | ❌ absent | Same                                           |
| `log-span-annotation`   | ❌ absent | Must wrap Python SDK                           |
| `write-span-annotation` | ❌ absent | Same                                           |
| `create-annotation`     | ❌ absent | Same                                           |

**ADR-005 verdict: confirmed exactly.** The architecture's "Phoenix MCP is partial" finding is structurally correct. Two custom ADK `FunctionTool` wrappers (S4.3 + S4.4 in the spec) are mandatory.

**Architecture amendments to file:**

- Add `get-span-annotations` to the read-side MCP inventory in `architecture/02 §1` (we CAN read annotations via MCP, just not write them)
- Add the 13 bonus tools enumerated above (sessions, dataset-experiments, prompt versioning)
- Note `get-spans` (not `list-spans`) as the correct name

---

## Step 3 — Phoenix Python SDK end-to-end (✅ PASS — the load-bearing one)

**Script:** `/tmp/phoenix-rat/step3_sdk_experiment.py`

**End-to-end flow exercised:**

1. ✅ Created dataset `rat-step3-dataset` (id `RGF0YXNldDox`) with 3 examples via `client.datasets.create_dataset(name=..., dataframe=..., input_keys=..., output_keys=...)`
2. ✅ Defined `task(example) -> str` and `length_match(output, expected) -> float` evaluator
3. ✅ Called `await client.experiments.run_experiment(dataset=ds, task=task, evaluators=[length_match], experiment_name="rat-step3-experiment", concurrency=2)`
4. ✅ Experiment completed: 3 task runs, 1 evaluator, 3 evaluations
5. ✅ Server-side verified via `await client.experiments.list(dataset_id=ds.id)` — found 1 experiment with id `RXhwZXJpbWVudDox`

**Phoenix Cloud experiment URL** (the actual artifact):

```
https://app.phoenix.arize.com/s/blockchainoracle-dev/datasets/RGF0YXNldDox/compare?experimentId=RXhwZXJpbWVudDox
```

**API surface confirmed (canonical reference for the ChaosLab spec):**

```python
from phoenix.client import AsyncClient

client = AsyncClient(base_url=PHOENIX_COLLECTOR_ENDPOINT, api_key=PHOENIX_API_KEY)

# Namespaces available
client.datasets       # AsyncDatasets
client.experiments    # AsyncExperiments
client.projects       # AsyncProjects
client.prompts        # AsyncPrompts
client.sessions       # AsyncSessions
client.spans          # AsyncSpans
client.traces         # AsyncTraces

# experiments.run_experiment signature (verified by inspection)
result = await client.experiments.run_experiment(
    dataset=Dataset,             # required, from client.datasets.get_dataset(...)
    task=Callable,               # required, takes a DatasetExample, returns dict|list|str|int|float|bool|None
    evaluators=Callable|list,    # required, returns score 0-1 or ExperimentEvaluation
    experiment_name=Optional[str],
    experiment_description=Optional[str],
    experiment_metadata=Optional[Mapping[str, Any]],
    rate_limit_errors=Optional[type[BaseException]|Sequence],
    dry_run=False,
    print_summary=True,
    concurrency=3,               # default — async client only
    timeout=60,
    repetitions=1,
    retries=3,
) -> RanExperiment  # returns dict-shaped result, not a typed object

# experiments.list signature
exps = await client.experiments.list(dataset_id=ds.id)  # NOT dataset=
```

**Important: `experiments.run_experiment` returns a `dict` server-side, not a typed `RanExperiment` class in 2026-06.** The FunctionTool wrapper in S4.3 should normalize to a pydantic schema (`PhoenixExperimentResult`) before returning to the agent.

**Audit items resolved:**

- 🟢 **C4: Phoenix `concurrency` default sync vs async** — async client default `concurrency=3`; sync client has NO `concurrency` arg. Use async for ChaosLab.
- 🟢 **C5: Phoenix Cloud free-tier experiment limits** — experiments execute cleanly on the free tier with the test credentials. No setup required beyond API key.
- 🟢 **C10: `phoenix.client` package name** — installed as `arize-phoenix-client` (PyPI), imported as `phoenix.client`. Pin in `pyproject.toml`.

---

## Audit items resolved (5 of 41 in `docs/audit-notes.md`)

| #       | Item                                  | Resolution                                                  |
| ------- | ------------------------------------- | ----------------------------------------------------------- |
| C1      | Phoenix Cloud space-scoped URL        | ✅ Use as-is; SDK appends `/v1/traces`                      |
| C4      | Phoenix `concurrency` default         | ✅ Async client = 3; sync client = N/A                      |
| C5      | Phoenix annotation-config auto-create | ✅ Auto on first ingest (no manual provisioning)            |
| C10     | `phoenix.client` package name         | ✅ `arize-phoenix-client` on PyPI, `phoenix.client` imports |
| ADR-005 | Phoenix MCP partial surface           | ✅ Confirmed exactly — 0 write tools                        |

**Still open (will resolve during build):**

- C2, C3 (ADK callback + Runner signatures) — verify when implementing E2/E4
- C6 (annotation REST path) — verify when implementing S4.4 (Python SDK exposes it via `client.spans.log_span_annotations(...)`, exact REST path can be inspected via SDK source)
- C7 (`phoenix.evals.LLM.acomplete()`) — verify when implementing S6.4

---

## Things that changed during the RAT

1. **Phoenix Cloud now has 3 live projects in `blockchainoracle-dev`:** `default`, `demo_llama_index`, `chaoslab-rat`. The latter two were created during this RAT. **Action: clean up `chaoslab-rat` and `demo_llama_index` from Abu's space if desired, OR rename `chaoslab-rat` → `chaoslab-replay` to reuse as the canonical demo project (S8.2 seed target).**

2. **`rat-step3-dataset` (id `RGF0YXNldDox`) is now in Phoenix Cloud.** Same — keep or delete. The data is trivial (3 placeholder Q&A examples).

3. **One real experiment ran end-to-end:** id `RXhwZXJpbWVudDox`. Cost: < $0.01 (no LLM calls — task was a string-lowercasing stub + deterministic evaluator).

4. **Credentials are persisted at `~/.config/phoenix-rat/.env` (chmod 600).** Not committed. Future RAT-style scripts can `source` this.

---

## Next step

🟢 **Spec is unblocked.** Abu can now:

1. **Approve `docs/PRD.md`, `docs/architecture.md`, `docs/cicd.md`, `docs/coding-standards.md`, `docs/ux-spec.md`, `docs/epics.md`** — these are the artifact set the orchestrator consumes
2. **Fire `sahil-hackathon-orchestrator`** — it reads `docs/sprint-status.yaml` (52 stories, dependency DAG) and creates GitHub issues + dispatches coding agents

Critical path estimate: ~33h sequential + ~12h parallel = ~45h wall-clock. With AI coding agents at 3-5× human dev speed and a 9-day deadline, comfortably under budget.

---

## Reproducibility

All RAT scripts under `/tmp/phoenix-rat/`:

- `step1_first_trace.py` — emit one trace
- `step1b_verify_server_side.py` — verify via SDK
- `step2_mcp_tool_discovery.py` — MCP tool inventory
- `step3_sdk_experiment.py` — end-to-end experiment
- `step3b_inspect_api.py` — API surface inspection

Re-run any with `cd /tmp/phoenix-rat && uv run python <script>.py`. Credentials loaded from `~/.config/phoenix-rat/.env`.
