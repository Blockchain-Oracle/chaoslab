# Story — Phoenix `write_span_annotation` Custom ADK FunctionTool

**ID:** story-4.4-phoenix-write-annotation-tool
**Epic:** Epic 4 — ChaosLab orchestrator + Phoenix tool wrappers
**Depends on:** story-4.1-agent-entrypoint
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, phoenix, adk, function-tool]

---

## User story

**As a** Judge sub-agent (E6) finishing a clustering pass
**I want to** call `write_span_annotation(span_id, score, reason, annotator)` as an ADK `FunctionTool` that wraps `phoenix.client.AsyncClient().spans.log_span_annotations(...)`
**So that** the failure-cluster score is durably written back to the original Phoenix span (the writeback channel the MCP server does NOT expose per ADR-005 + `architecture/02 §9.6`) — closing the recursive observability loop that the Arize track explicitly bonuses

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/phoenix_tools/write_annotation.py` — NEW — the tool body. Defines:
  - `AnnotationResult(BaseModel)` with `status: Literal["ok", "skipped"]`, `span_id: str = Field(min_length=8)`, `annotation_name: str`, `score: float = Field(ge=0.0, le=1.0)`, `wrote_at: str` (ISO 8601 UTC).
  - `write_span_annotation(span_id: str, score: float, reason: str, annotator: str = "chaoslab_judge", label: str = "auto") -> AnnotationResult` — async function. Validates inputs (`0.0 ≤ score ≤ 1.0`, `len(reason) > 0`, `annotator in {"chaoslab_judge", "human", "code"}`). Builds a `SpanAnnotationData` (from `phoenix.client.resources.spans`) with `name="chaoslab_cluster"` (annotation-config name, fixed per project), `annotator_kind` mapped from `annotator` ("chaoslab_judge"→"LLM", "human"→"HUMAN", "code"→"CODE"), `result={"label": label, "score": score, "explanation": reason}`, `metadata={"chaoslab_version": settings.service_version}`. Calls `await client.spans.log_span_annotations(span_annotations=[annotation])`. Returns `AnnotationResult`. Body ≤30 LOC per ADR-005 (excluding pydantic + imports + sanity-mapping which live above).
  - Module-level `phoenix_write_annotation_tool: FunctionTool = FunctionTool(func=write_span_annotation)` — the exported tool.
  - Total file ~130 lines.
- `apps/chaoslab-agent/tests/integration/test_phoenix_write_annotation.py` — NEW — at least 8 pytest cases:
  - `AnnotationResult` validates a sample dict.
  - `AnnotationResult` rejects `score=1.5` (ge/le bounds).
  - `phoenix_write_annotation_tool` is a `FunctionTool` instance; `.func.__name__ == "write_span_annotation"`.
  - **`respx`-mocked happy path:** intercepts Phoenix POST `/v1/span_annotations` (or whatever the actual REST path is — verify against pinned `arize-phoenix-client` version), returns 200. Tool returns `AnnotationResult(status="ok", ...)`.
  - **Score out of bounds raises ValidationError** before any HTTP call: tool input `score=-0.1` raises pydantic `ValidationError`; `respx` records zero outbound requests.
  - **Empty reason raises:** tool input `reason=""` raises `ValueError` (or pydantic `ValidationError`); zero HTTP calls.
  - **`respx`-mocked 500 path:** Phoenix returns 500. Tool raises `PhoenixAnnotationError`; message does not leak the API key.
  - **Annotator kind mapping:** `annotator="human"` produces a `SpanAnnotationData` with `annotator_kind="HUMAN"`; `annotator="chaoslab_judge"` produces `"LLM"`; `annotator="code"` produces `"CODE"`. Assert via inspecting the request body captured by respx.
  - **`@pytest.mark.online` real Phoenix hit:** if `PHOENIX_API_KEY` is set, the tool writes an annotation to a known existing span (env var `PHOENIX_TEST_SPAN_ID`, pre-created during Day-1 RAT runbook). Then a follow-up `client.spans.get_span(...)` call asserts the annotation is server-side visible. Skipped if env vars missing.
  ~180 lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given chaoslab_agent.phoenix_tools.write_annotation imports cleanly
When  pytest imports `from chaoslab_agent.phoenix_tools.write_annotation import phoenix_write_annotation_tool, AnnotationResult, write_span_annotation`
Then  no exception is raised
And   phoenix_write_annotation_tool is an instance of google.adk.tools.FunctionTool

Given the write_span_annotation function body
When  significant LOC is counted (excluding docstring/comments)
Then  the count is ≤ 30 per ADR-005

Given AnnotationResult(status="ok", span_id="span_abc123", annotation_name="chaoslab_cluster", score=0.85, wrote_at="2026-06-04T12:00:00Z")
When  the model is constructed
Then  no ValidationError is raised

Given AnnotationResult(..., score=1.5, ...)
When  the model is constructed
Then  pydantic.ValidationError is raised

Given write_span_annotation is invoked with score=-0.1
When  the call is awaited
Then  ValidationError or ValueError is raised BEFORE any HTTP request
And   respx records zero outbound requests

Given write_span_annotation is invoked with reason=""
When  the call is awaited
Then  ValidationError or ValueError is raised
And   respx records zero outbound requests

Given respx intercepts the Phoenix span-annotation endpoint and returns 200
When  `await write_span_annotation("span_abc123", 0.85, "tool returned 404", "chaoslab_judge")` is awaited
Then  the return is AnnotationResult(status="ok", span_id="span_abc123", score=0.85, ...)
And   respx captured exactly 1 request
And   the request body's annotator_kind == "LLM"

Given respx returns 500
When  the tool is invoked
Then  chaoslab_agent.errors.PhoenixAnnotationError is raised
And   the exception message does NOT contain the API key

Given write_span_annotation is invoked with annotator="human"
When  respx captures the outbound request body
Then  the body's annotator_kind == "HUMAN"

@pytest.mark.online
Given PHOENIX_API_KEY env var is set AND span PHOENIX_TEST_SPAN_ID exists in project chaoslab-test
When  the tool writes an annotation with score=0.85 + reason="rat-test"
Then  AnnotationResult(status="ok") returns
And   a follow-up get_span call shows the annotation server-side (annotation with name="chaoslab_cluster" and score=0.85)

Given `cd apps/chaoslab-agent && uv run pytest tests/integration/test_phoenix_write_annotation.py -v -m "not online"` runs
When  the test suite completes
Then  at least 7 behavioral test cases pass

Given the 400-line guard runs
When  `python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# 1) Offline tests pass with ≥7 cases
cd apps/chaoslab-agent && uv run pytest tests/integration/test_phoenix_write_annotation.py -v -m "not online" 2>&1 | tee /tmp/phoenix-ann.log
grep -E "PASSED" /tmp/phoenix-ann.log | wc -l
# Must output ≥ 7

# 2) ≤30 LOC body check (ADR-005)
cd apps/chaoslab-agent && uv run python -c "
import inspect
from chaoslab_agent.phoenix_tools.write_annotation import write_span_annotation
src = inspect.getsource(write_span_annotation).split('\n')
sig_lines = [l for l in src if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('\"\"\"') and not l.strip().startswith(\"'''\")]
print(f'LOC: {len(sig_lines)}')
assert len(sig_lines) <= 30, f'Wrapper body must be ≤30 LOC per ADR-005, got {len(sig_lines)}'
print('OK')
"
# Must print OK

# 3) Tool is a real FunctionTool
cd apps/chaoslab-agent && uv run python -c "
from google.adk.tools import FunctionTool
from chaoslab_agent.phoenix_tools.write_annotation import phoenix_write_annotation_tool
assert isinstance(phoenix_write_annotation_tool, FunctionTool), type(phoenix_write_annotation_tool)
assert phoenix_write_annotation_tool.func.__name__ == 'write_span_annotation'
print('OK')
"
# Must print OK

# 4) Optional online test (CI tagged job only)
if [ -n "$PHOENIX_API_KEY" ] && [ -n "$PHOENIX_TEST_SPAN_ID" ]; then
  cd apps/chaoslab-agent && uv run pytest tests/integration/test_phoenix_write_annotation.py -v -m "online"
fi

# 5) §14 clean
git diff main...HEAD -- 'apps/chaoslab-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing

# 6) 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/
# Must exit 0

# 7) ruff + ty
cd apps/chaoslab-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# Must exit 0

# 8) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Why this wrapper exists.** Per ADR-005 + `architecture/02 §9.6`: the Phoenix MCP server exposes `list-annotation-configs` but NOT `log-span-annotation`. To close the recursive observability loop (the explicit Arize-track bonus, per PRD "Sponsor-native fit"), ChaosLab MUST wrap the Python SDK as a custom ADK `FunctionTool`. This + S4.3 are the two keystone tools of ADR-005.
- **The 30-LOC budget is a hard rule.** Same as S4.3 — the wrapper body itself ≤30 significant LOC. Pydantic models, annotator-kind mapping, and `SpanAnnotationData` construction live above the function or as a small helper.
- **Reference canonical wrapper shape** (per `architecture/02 §9.6` — adapt, do not paste verbatim):
  ```python
  ANNOTATOR_KIND = {"chaoslab_judge": "LLM", "human": "HUMAN", "code": "CODE"}

  async def write_span_annotation(
      span_id: str,
      score: float,
      reason: str,
      annotator: str = "chaoslab_judge",
      label: str = "auto",
  ) -> AnnotationResult:
      """Attach a ChaosLab failure-cluster annotation to a Phoenix span.

      ADR-005 keystone tool. Wraps phoenix.client.AsyncClient().spans.log_span_annotations.
      """
      if not reason:
          raise ValueError("reason must be non-empty")
      if annotator not in ANNOTATOR_KIND:
          raise ValueError(f"annotator must be one of {set(ANNOTATOR_KIND)}, got {annotator}")
      client = AsyncClient(api_key=get_settings().phoenix_api_key.get_secret_value())
      annotation = SpanAnnotationData(
          name="chaoslab_cluster",
          span_id=span_id,
          annotator_kind=ANNOTATOR_KIND[annotator],
          result={"label": label, "score": score, "explanation": reason},
          metadata={"chaoslab_version": get_settings().service_version},
      )
      try:
          await client.spans.log_span_annotations(span_annotations=[annotation])
      except Exception as e:
          raise PhoenixAnnotationError(f"annotation write failed: span={span_id}") from e
      return AnnotationResult(status="ok", span_id=span_id, annotation_name="chaoslab_cluster",
                              score=score, wrote_at=datetime.utcnow().isoformat() + "Z")
  ```
  Body is ~20 LOC significant; well under 30.
- **Score bounds via pydantic `Field(ge=0.0, le=1.0)`** on the `AnnotationResult` model — but the input `score` parameter on the function also needs validation. Use a `@pydantic.validate_call` decorator on the function OR an explicit `if not 0.0 <= score <= 1.0: raise ValueError(...)` early-return. Either works; pick one and document it. The BDD asserts the score-out-of-bounds case raises BEFORE any HTTP call.
- **Empty reason validation.** The BDD asserts empty `reason` raises. Per `architecture/02 §9.6` the annotation's `explanation` field is the primary semantic content — empty is useless. Raise `ValueError("reason must be non-empty")` early.
- **`annotator_kind` mapping is load-bearing.** Phoenix's `SpanAnnotationData` accepts exactly `"LLM" | "HUMAN" | "CODE"` per `architecture/02 §1, §9.6`. The mapping dict makes ChaosLab's internal vocabulary stable while letting Phoenix get the strings it wants. Tests assert on the actual request body (via respx capture) — implementation must produce the canonical Phoenix strings.
- **Annotation config pre-creation gotcha.** Per `architecture/02-phoenix-deep-dive.md §10` open question: it is unverified whether `log_span_annotations` auto-creates the annotation config on first call OR requires the user to pre-create it in the UI. Day-1 RAT runbook validates this. For this story: if `online` test fails with "annotation config not found," the fix is to either (a) call `client.spans.create_annotation_config(name="chaoslab_cluster")` once at module load, or (b) document a one-time UI setup step in `apps/chaoslab-agent/README.md`. Pick (a) if the SDK exposes it; else (b).
- **`PhoenixAnnotationError` sanitization.** Same rule as S4.3 — never leak the API key. `from e` preserves traceback for debug.
- **`AsyncClient` reuse.** Both S4.3 and S4.4 construct an `AsyncClient` per call. For now this is fine (negligible overhead). Future optimization: cache a single client at module load via `@functools.lru_cache` — but only after S4.5 lands and we have a clean lifecycle hook to close it on shutdown.
- **`@pytest.mark.online` carve-out.** Same pattern as S4.3 — skipped in default CI; runs on a tagged nightly job. The offline-respx tests gate every PR.
- **400-line vigilance.** File should land at ~130 lines. Watch the imports list — `phoenix.client.resources.spans.SpanAnnotationData` is the canonical type; if the import path changes between `arize-phoenix-client` versions, pin and document.
- **Cross-reference docs:**
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/02-phoenix-deep-dive.md` §1 (MCP asymmetry), §9.6 (Pattern F — canonical wrapper), §10 open question on annotation-config auto-create
  - `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` ADR-005 (Phoenix MCP partial)
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/06-test-strategy.md` §5.1 (trace-as-assertion + writeback)
