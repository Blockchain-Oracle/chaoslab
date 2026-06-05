"""End-to-end integration test: target-agent emits spans visible in Phoenix Cloud.

Skipped unless PHOENIX_API_KEY is set. Marked both @pytest.mark.integration
and @pytest.mark.online so cost-conscious CI runs can exclude it with
`-m "not online"`.

Test shape:
  1. Set a unique PHOENIX_PROJECT_NAME for this run (avoids polluting Phoenix
     Cloud with shared trash projects).
  2. Call setup_observability() to wire the Phoenix tracer + ADK instrumentor.
  3. Invoke `lookup_order` directly — emits a TOOL span tagged with the
     OpenInference convention attributes.
  4. Force a span flush via the tracer provider's processor.
  5. Poll Phoenix Cloud's REST API for spans tagged with our test project name.
  6. Assert at least one TOOL span surfaces within 30 seconds.
"""

from __future__ import annotations

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
def test_target_tool_span_lands_in_phoenix_cloud() -> None:
    """A real lookup_order call surfaces as an OpenInference TOOL span."""
    test_project = f"target-agent-test-{uuid.uuid4().hex[:8]}"
    os.environ["PHOENIX_PROJECT_NAME"] = test_project

    # setup_observability must run before any google.adk import in this test;
    # since we haven't imported target_agent.agent at module level, this order
    # is enforced naturally.
    from target_agent.observability import setup_observability

    tracer_provider = setup_observability(project_name=test_project)

    # NOW it's safe to import + invoke the target agent's tools.
    from target_agent.tools import lookup_order

    result = lookup_order("12345")
    assert result["status"] == "shipped", f"unexpected tool result: {result}"

    # Flush spans synchronously (batch=False already ensures this, but the
    # explicit shutdown forces any pending exports to complete).
    tracer_provider.force_flush(timeout_millis=5000)

    # Poll Phoenix Cloud's REST API for the TOOL span we just emitted.
    api_key = os.environ["PHOENIX_API_KEY"]
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com")
    # Spans endpoint per Phoenix REST API v1 (read-back path).
    spans_url = f"{endpoint.rstrip('/')}/v1/projects/{test_project}/spans"
    headers = {"Authorization": f"Bearer {api_key}"}

    deadline = time.monotonic() + 30.0
    tool_spans: list[dict] = []
    last_status: int | None = None
    last_body: str = ""
    while time.monotonic() < deadline:
        try:
            r = httpx.get(spans_url, headers=headers, timeout=5.0)
            last_status = r.status_code
            last_body = r.text[:500]
            if r.status_code == 200:
                spans = r.json().get("data", []) or r.json().get("spans", []) or []
                tool_spans = [
                    s
                    for s in spans
                    if isinstance(s, dict)
                    and (s.get("attributes") or {}).get("openinference.span.kind") == "TOOL"
                ]
                if tool_spans:
                    break
        except httpx.HTTPError:
            pass
        time.sleep(1.0)

    assert tool_spans, (
        f"No TOOL spans found at {spans_url} within 30s. "
        f"last status={last_status}, last body[:500]={last_body!r}. "
        f"If 404: the space-scoped URL form (https://app.phoenix.arize.com/s/<space>) "
        f"may be required — update PHOENIX_COLLECTOR_ENDPOINT in .env.example."
    )
