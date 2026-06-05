"""End-to-end integration test: target-agent emits spans visible in Phoenix Cloud.

Skipped unless PHOENIX_API_KEY is set. Marked both @pytest.mark.integration
and @pytest.mark.online so cost-conscious CI runs can exclude it with
`-m "not online"`. The S2.3 acceptance test asserts that, WHEN
PHOENIX_API_KEY is set, this test actually PASSES (not just collected) —
"no skipping" is explicit: skipping is mocking by another name.

Test shape:
  1. Set a unique PHOENIX_PROJECT_NAME for this run (avoids polluting Phoenix
     Cloud with shared trash projects).
  2. Call setup_observability() to wire the Phoenix tracer + ADK instrumentor.
  3. Invoke `lookup_order` directly — emits a TOOL span tagged with the
     OpenInference convention attributes.
  4. Force a span flush via the tracer provider's processor; assert the
     flush actually completed (catches local-pipeline failures so they
     don't masquerade as Phoenix-side problems).
  5. Poll Phoenix Cloud's REST API for spans tagged with our test project.
  6. Assert at least one TOOL span surfaces within 30 seconds.
"""

from __future__ import annotations

import json
import os
import time
import uuid

import httpx
import pytest

_REQUIRES_PHOENIX_KEY = not bool(os.environ.get("PHOENIX_API_KEY"))


@pytest.mark.integration
@pytest.mark.online
@pytest.mark.skipif(
    _REQUIRES_PHOENIX_KEY,
    reason="Requires PHOENIX_API_KEY env var pointing at a real Phoenix Cloud workspace",
)
def test_target_tool_span_lands_in_phoenix_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real lookup_order call surfaces as an OpenInference TOOL span."""
    test_project = f"target-agent-test-{uuid.uuid4().hex[:8]}"
    # Use monkeypatch.setenv so the project name doesn't leak into the
    # pytest session env after this test finishes.
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", test_project)

    # setup_observability must run before any google.adk import in this test;
    # since we haven't imported target_agent.agent at module level, this order
    # is enforced naturally.
    from target_agent.observability import setup_observability

    tracer_provider = setup_observability(project_name=test_project)

    # NOW it's safe to import + invoke the target agent's tools.
    from target_agent.tools import lookup_order

    result = lookup_order("12345")
    assert result["status"] == "shipped", f"unexpected tool result: {result}"

    # force_flush blocks until pending exports complete. If it returns False,
    # the local OTel pipeline is broken (timeout) — fail fast here so a
    # downstream 30s poll for Phoenix spans doesn't mask the real cause.
    flushed = tracer_provider.force_flush(timeout_millis=5000)
    assert flushed, (
        "tracer_provider.force_flush(5000ms) returned False — local export "
        "pipeline is broken before Phoenix even saw the span. Check the OTel "
        "exporter logs above."
    )

    # Poll Phoenix Cloud's REST API for the TOOL span we just emitted.
    api_key = os.environ["PHOENIX_API_KEY"]
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com")
    spans_url = f"{endpoint.rstrip('/')}/v1/projects/{test_project}/spans"
    headers = {"Authorization": f"Bearer {api_key}"}

    deadline = time.monotonic() + 30.0
    tool_spans: list[dict] = []
    saw_any_span = False
    last_status: int | None = None
    last_body: str = ""
    last_error: str = ""
    first_span_sample: str = ""
    while time.monotonic() < deadline:
        try:
            r = httpx.get(spans_url, headers=headers, timeout=5.0)
        except httpx.HTTPError as e:
            last_error = f"{type(e).__name__}: {e}"
            time.sleep(1.0)
            continue

        last_status = r.status_code
        last_body = r.text[:500]
        # Fail-fast on auth errors instead of looping for 30s pretending
        # things might recover.
        if r.status_code in (401, 403):
            pytest.fail(
                f"Phoenix Cloud auth failed: HTTP {r.status_code} at {spans_url}. "
                f"Verify PHOENIX_API_KEY scope matches the workspace. Body: {last_body}"
            )
        if r.status_code == 200:
            spans = r.json().get("data", []) or r.json().get("spans", []) or []
            if spans:
                saw_any_span = True
                if not first_span_sample:
                    first_span_sample = json.dumps(spans[0], indent=2)[:1000]
            # Empirical observation from this S2.3 test run: Phoenix Cloud's
            # /v1/projects/{name}/spans REST endpoint returns OpenInference
            # span kind as a top-level `span_kind` field (e.g.
            # `"span_kind": "TOOL"`). Defensive: also check the nested
            # `attributes.openinference.span.kind` path in case other
            # endpoints or future Phoenix versions surface it that way.
            tool_spans = [
                s
                for s in spans
                if isinstance(s, dict)
                and (
                    s.get("span_kind") == "TOOL"
                    or (s.get("attributes") or {}).get("openinference.span.kind") == "TOOL"
                )
            ]
            if tool_spans:
                break
        time.sleep(1.0)

    # Distinguish the three failure modes:
    #   1. Never reached the project (404 throughout) — emission/wire failed
    #   2. Reached the project but no spans landed (200 with empty data) —
    #      Phoenix is up but our spans aren't getting ingested
    #   3. Spans landed but none had span_kind=TOOL — instrumentor broken
    if not tool_spans:
        if not saw_any_span:
            failure_mode = (
                "no spans visible in Phoenix project — either emission/wire "
                "failed (force_flush returned True but spans didn't land), or "
                "Phoenix Cloud project never created"
            )
        else:
            failure_mode = (
                "spans landed in Phoenix but NONE had span_kind=TOOL — the "
                "GoogleADKInstrumentor or tools.py manual span emission is broken"
            )
        pytest.fail(
            f"No TOOL spans found at {spans_url} within 30s. "
            f"Failure mode: {failure_mode}. "
            f"last_status={last_status}, last_body[:500]={last_body!r}, "
            f"last_error={last_error!r}, first_span_sample={first_span_sample!r}"
        )
