"""Integration tests for ADKAdapter against the live target_agent service.

These tests REQUIRE the target_agent service to be running at
``${TARGET_AGENT_URL:-http://localhost:8001}``. They are marked
``@pytest.mark.integration`` so the standard PR run (``-m "not integration
and not online"``) skips them. CI's integration matrix stands up the
target via docker-compose; locally, run:

    GOOGLE_API_KEY=... uv run --project apps/target-agent python -m target_agent.server &

The module-level skip-if-target-down check makes this graceful: when the
target isn't reachable, all tests in this file ``pytest.skip`` rather than
fail. This matches the spec's "≥10 integration tests pass when target is
up" criterion without breaking dev loops that don't have the target running.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest

from phoenix_audit_agent.errors import AdapterConnectionError
from phoenix_audit_agent.injector.target_adapters import AdapterTier, ADKAdapter, TargetSpec
from phoenix_audit_agent.injector.target_adapters.base import AdapterInvocation

_TARGET_URL = os.environ.get("TARGET_AGENT_URL", "http://localhost:8001")


def _target_reachable() -> bool:
    """Return True if the target's TCP+HTTP stack responds at all.

    We deliberately only treat transport-level failures (``httpx.RequestError``
    — connect refused, DNS, timeout, ELOOP) as "down". A 4xx or 5xx means the
    target IS up and the test should run + assert on the actual behaviour; a
    broken AgentCard endpoint should surface as a failed integration test,
    NOT be silently skipped as "target down" (test-analyzer PR #41 Round-1).
    """
    try:
        httpx.get(f"{_TARGET_URL}/.well-known/agent-card.json", timeout=2.0)
    except httpx.RequestError:
        return False
    return True


_SKIP_REASON = (
    f"target_agent not reachable at {_TARGET_URL}; start it via "
    "`uv run --project apps/target-agent python -m target_agent.server`"
)

# Single pytestmark assignment (the earlier draft assigned it twice — harmless
# but visually misleading, flagged by code-reviewer).
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _target_reachable(), reason=_SKIP_REASON),
]


def _spec(**overrides: object) -> TargetSpec:
    payload: dict[str, object] = {"tier": "tier1_adk", "url": _TARGET_URL}
    payload.update(overrides)
    return TargetSpec.model_validate(payload)


async def test_connect_parses_live_agent_card() -> None:
    adapter = ADKAdapter(_spec())
    try:
        await adapter.connect()
        assert adapter._connected is True
        assert adapter._agent_card is not None
        assert isinstance(adapter._agent_card.get("name"), str)
        assert adapter._agent_card["name"]  # non-empty
    finally:
        await adapter.disconnect()


async def test_invoke_returns_span_ids_and_duration() -> None:
    adapter = ADKAdapter(_spec())
    try:
        await adapter.connect()
        result = await adapter.invoke(
            AdapterInvocation(prompt="What's my order status for order #ORD-1?")
        )
        assert result.error is None, f"unexpected error: {result.error}"
        assert isinstance(result.response, str)
        assert len(result.response) > 0
        assert len(result.span_ids) >= 1
        assert result.duration_ms > 0.0
    finally:
        await adapter.disconnect()


async def test_invoke_captures_agent_card_name_in_metadata() -> None:
    adapter = ADKAdapter(_spec())
    try:
        await adapter.connect()
        result = await adapter.invoke(AdapterInvocation(prompt="hi"))
        assert result.metadata.get("agent_card_name")
    finally:
        await adapter.disconnect()


async def test_fingerprint_returns_tier1_adk_with_card() -> None:
    adapter = ADKAdapter(_spec())
    try:
        fp = await adapter.fingerprint()
        assert fp.tier is AdapterTier.TIER1_ADK
        assert fp.framework == "google-adk"
        assert fp.discovery_path == "agent_card"
        assert fp.agent_card is not None
        assert fp.agent_card.get("name")
    finally:
        await adapter.disconnect()


async def test_invoke_without_prior_connect_auto_connects() -> None:
    adapter = ADKAdapter(_spec())
    try:
        assert adapter._connected is False
        result = await adapter.invoke(AdapterInvocation(prompt="hello"))
        assert adapter._connected is True
        assert result.error is None
    finally:
        await adapter.disconnect()


async def test_connect_is_idempotent_on_live_target() -> None:
    adapter = ADKAdapter(_spec())
    try:
        await adapter.connect()
        first_card = adapter._agent_card
        await adapter.connect()
        # Idempotent: card identity unchanged, no re-fetch effects observable.
        assert adapter._agent_card is first_card
    finally:
        await adapter.disconnect()


async def test_disconnect_then_reconnect_is_safe() -> None:
    adapter = ADKAdapter(_spec())
    try:
        await adapter.connect()
        await adapter.disconnect()
        assert adapter._connected is False
        await adapter.connect()
        assert adapter._connected is True
    finally:
        await adapter.disconnect()


async def test_disconnect_without_connect_does_not_raise() -> None:
    adapter = ADKAdapter(_spec())
    await adapter.disconnect()
    assert adapter._connected is False


async def test_unreachable_url_raises_connection_error() -> None:
    """Pointing at a port nothing's listening on must fail loud, not hang."""
    adapter = ADKAdapter(
        TargetSpec.model_validate(
            {"tier": "tier1_adk", "url": "http://localhost:9", "timeout_s": 2.0}
        )
    )
    with pytest.raises(AdapterConnectionError, match="localhost:9"):
        await adapter.connect()


async def test_concurrent_invocations_each_capture_own_span() -> None:
    """Two concurrent invokes must each get a span_id; no clobbering."""
    adapter = ADKAdapter(_spec())
    try:
        await adapter.connect()
        results = await asyncio.gather(
            adapter.invoke(AdapterInvocation(prompt=f"probe-{uuid.uuid4().hex[:8]}")),
            adapter.invoke(AdapterInvocation(prompt=f"probe-{uuid.uuid4().hex[:8]}")),
        )
        assert len(results) == 2
        for r in results:
            assert r.error is None, f"unexpected error: {r.error}"
            assert len(r.span_ids) >= 1
        # Each invoke creates a fresh outer span — IDs must differ.
        assert results[0].span_ids[0] != results[1].span_ids[0]
    finally:
        await adapter.disconnect()
