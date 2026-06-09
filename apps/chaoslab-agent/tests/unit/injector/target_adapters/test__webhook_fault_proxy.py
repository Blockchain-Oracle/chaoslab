"""Unit tests for the generalized `webhook_fault_session`.

The CrewAI- and OpenAI-SDK-specific shapes are covered by their adapter
tests + `test__crewai_hook_proxy.py` (which now delegates to this
module). Here we lock the parametric contract directly so adding a new
Tier-2 adapter that consumes the proxy has unambiguous documentation.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from chaoslab_agent.injector.target_adapters._webhook_fault_proxy import (
    webhook_fault_session,
)


async def test_yields_none_when_fault_kind_does_not_match() -> None:
    """Each adapter supplies its own `fault_kind`; non-matching fault_config
    yields None so the adapter takes the no-fault path."""
    async with (
        httpx.AsyncClient() as http,
        webhook_fault_session(
            {"kind": "prompt_injection"},
            http=http,
            target_url="http://x",
            hook_path="/hooks/whatever",
            fault_kind="malformed_tool_output",
        ) as reg,
    ):
        assert reg is None


@respx.mock
async def test_registration_uses_caller_supplied_hook_path_and_fault_kind() -> None:
    """Lock the parametrization: hook_path is forwarded; fault_kind drives
    whether we register at all."""
    register = respx.post("http://x/hooks/custom").mock(
        return_value=httpx.Response(200, json={"registration_id": "rX"})
    )
    delete = respx.delete("http://x/hooks/custom/rX").mock(return_value=httpx.Response(204))
    async with (
        httpx.AsyncClient() as http,
        webhook_fault_session(
            {"kind": "custom_fault"},
            http=http,
            target_url="http://x",
            hook_path="/hooks/custom",
            fault_kind="custom_fault",
        ) as reg,
    ):
        assert reg == "rX"
    assert register.call_count == 1
    assert delete.call_count == 1


@respx.mock
async def test_registration_failure_yields_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A target that doesn't expose the hook surface gets a graceful skip."""
    import logging as _logging

    respx.post("http://x/hooks/custom").mock(side_effect=httpx.ConnectError("no route"))
    _proxy_logger = "chaoslab_agent.injector.target_adapters._webhook_fault_proxy"
    with caplog.at_level(_logging.WARNING, logger=_proxy_logger):
        async with (
            httpx.AsyncClient() as http,
            webhook_fault_session(
                {"kind": "custom_fault"},
                http=http,
                target_url="http://x",
                hook_path="/hooks/custom",
                fault_kind="custom_fault",
            ) as reg,
        ):
            assert reg is None
    assert any("registration_failed" in r.message for r in caplog.records)
