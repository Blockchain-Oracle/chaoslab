"""Unit tests for the shared LiteLLM proxy session.

Lives in its own file (not inside test_langchain_adapter_unit.py) so the
context-manager contract is tested ONCE — CrewAI / OpenAI Agents SDK / HTTP
black-box adapters all consume the same `litellm_proxy_session` symbol.
"""

from __future__ import annotations

import pytest

from phoenix_audit_agent.injector.target_adapters._litellm_proxy import (
    ProxyContext,
    litellm_proxy_session,
)


async def test_yields_none_when_fault_config_is_none() -> None:
    async with litellm_proxy_session(None) as proxy:
        assert proxy is None


async def test_yields_none_when_fault_config_kind_is_not_prompt_injection() -> None:
    """Round-2 SFH-I4: a fault_config of a different kind (latency_spike,
    malformed_tool_output, …) must NOT activate the proxy."""
    async with litellm_proxy_session({"kind": "latency_spike"}) as proxy:
        assert proxy is None


async def test_yields_none_when_fault_config_is_empty_dict() -> None:
    """Round-2 SFH-I4 explicit-state: empty dict ≠ "no fault". Adapters
    that build fault_config={} then mutate it later must still see None
    when the kind is missing, not silently activate the proxy."""
    async with litellm_proxy_session({}) as proxy:
        assert proxy is None


async def test_yields_none_when_kind_field_is_null() -> None:
    """Round-2 SFH-I4 explicit-state: `{"kind": None}` is silently
    pattern-#2 — the round-1 `if not fault_config` short-circuit collapsed
    this with the no-fault path. Now `kind != "prompt_injection"` catches it."""
    async with litellm_proxy_session({"kind": None}) as proxy:
        assert proxy is None


async def test_yields_active_context_on_prompt_injection() -> None:
    """Round-2 CR-#2 / SFH-I5: ProxyContext is base_url-only now; the
    speculative `custom_logger_active` field was deleted. Adapters key off
    `proxy is not None` truthiness, not internal flags."""
    async with litellm_proxy_session({"kind": "prompt_injection"}) as proxy:
        assert proxy is not None
        assert isinstance(proxy, ProxyContext)
        assert proxy.base_url.startswith("http")


async def test_proxy_context_is_frozen_dataclass() -> None:
    """Round-2 SFH-I5: ProxyContext is `@dataclass(frozen=True)` so a caller
    can't mutate base_url mid-flight. Lock the immutability invariant."""
    from dataclasses import FrozenInstanceError

    proxy = ProxyContext(base_url="http://example/")
    with pytest.raises(FrozenInstanceError):
        proxy.base_url = "http://other/"  # ty: ignore[invalid-assignment]


async def _raise_inside_proxy_block() -> None:
    """Helper — keeps `pytest.raises` block a single-statement per PT012."""
    async with litellm_proxy_session({"kind": "prompt_injection"}) as proxy:
        assert proxy is not None
        raise RuntimeError("caller fault")


async def test_exception_inside_block_propagates_after_finally_runs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Round-2 TQ-HIGH: an exception raised INSIDE the `async with` block
    propagates cleanly AND the `finally` (teardown log) still runs. Locks
    the cleanup invariant so a future refactor can't accidentally swallow
    the caller's exception by adding an `except` instead of `finally`."""
    import logging as _logging

    _proxy_logger = "phoenix_audit_agent.injector.target_adapters._litellm_proxy"
    with (
        caplog.at_level(_logging.INFO, logger=_proxy_logger),
        pytest.raises(RuntimeError, match="caller fault"),
    ):
        await _raise_inside_proxy_block()
    # The teardown log line MUST appear — proves the `finally` block ran
    # even though the caller's exception propagated.
    assert any("torn_down" in r.message for r in caplog.records), [
        r.message for r in caplog.records
    ]
