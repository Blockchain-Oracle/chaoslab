"""Unit tests for the shared CrewAI hook proxy session.

Pattern mirrors test__litellm_proxy.py: tested ONCE so multiple Tier-2
adapters consuming the hook surface have one consistent context-manager
contract.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from chaoslab_agent.injector.target_adapters._crewai_hook_proxy import crewai_hook_session


async def test_yields_none_when_fault_config_is_none() -> None:
    async with (
        httpx.AsyncClient() as http,
        crewai_hook_session(None, http=http, target_url="http://x") as reg,
    ):
        assert reg is None


async def test_yields_none_when_fault_kind_is_not_malformed_tool_output() -> None:
    async with (
        httpx.AsyncClient() as http,
        crewai_hook_session({"kind": "prompt_injection"}, http=http, target_url="http://x") as reg,
    ):
        assert reg is None


async def test_yields_none_when_http_client_is_none() -> None:
    """Defensive: if the caller hands None for http (no active connection),
    skip registration silently. The adapter would never do this in practice
    but the contract is explicit so future callers can't trip on it."""
    async with crewai_hook_session(
        {"kind": "malformed_tool_output", "tool_name": "calc"},
        http=None,
        target_url="http://x",
    ) as reg:
        assert reg is None


@respx.mock
async def test_yields_registration_id_on_matching_fault_and_tears_down() -> None:
    """Happy path — POST returns registration_id, DELETE fires on exit."""
    register = respx.post("http://x/hooks/before_tool_call").mock(
        return_value=httpx.Response(200, json={"registration_id": "reg-7"})
    )
    delete = respx.delete("http://x/hooks/before_tool_call/reg-7").mock(
        return_value=httpx.Response(204)
    )
    async with (
        httpx.AsyncClient() as http,
        crewai_hook_session(
            {"kind": "malformed_tool_output", "tool_name": "calc"},
            http=http,
            target_url="http://x",
        ) as reg,
    ):
        assert reg == "reg-7"
    assert register.call_count == 1
    assert delete.call_count == 1


@respx.mock
async def test_yields_none_when_registration_fails_with_transport_error() -> None:
    """Defensive: a target that doesn't expose the hook surface should not
    abort the invoke — log + carry on with the no-fault path."""
    respx.post("http://x/hooks/before_tool_call").mock(side_effect=httpx.ConnectError("no route"))
    async with (
        httpx.AsyncClient() as http,
        crewai_hook_session(
            {"kind": "malformed_tool_output"},
            http=http,
            target_url="http://x",
        ) as reg,
    ):
        assert reg is None


@respx.mock
async def test_yields_none_when_registration_returns_non_200() -> None:
    """Target accepted the protocol but rejected the descriptor — log + carry on."""
    respx.post("http://x/hooks/before_tool_call").mock(
        return_value=httpx.Response(403, text="forbidden")
    )
    async with (
        httpx.AsyncClient() as http,
        crewai_hook_session(
            {"kind": "malformed_tool_output"},
            http=http,
            target_url="http://x",
        ) as reg,
    ):
        assert reg is None


@respx.mock
async def test_teardown_failure_is_logged_but_swallowed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If DELETE fails during teardown, the original invoke() error path
    must NOT be masked. Log the teardown error but don't raise."""
    import logging as _logging

    respx.post("http://x/hooks/before_tool_call").mock(
        return_value=httpx.Response(200, json={"registration_id": "r1"})
    )
    respx.delete("http://x/hooks/before_tool_call/r1").mock(side_effect=httpx.ConnectError("dead"))
    _hook_logger = "chaoslab_agent.injector.target_adapters._crewai_hook_proxy"
    with caplog.at_level(_logging.WARNING, logger=_hook_logger):
        async with httpx.AsyncClient() as http:
            async with crewai_hook_session(
                {"kind": "malformed_tool_output"},
                http=http,
                target_url="http://x",
            ) as reg:
                assert reg == "r1"
    assert any("teardown_failed" in r.message for r in caplog.records)


@respx.mock
async def test_exception_inside_block_propagates_and_teardown_still_runs() -> None:
    """If the caller's `async with` block raises, the DELETE still fires
    (cleanup invariant) and the caller's exception propagates cleanly."""
    respx.post("http://x/hooks/before_tool_call").mock(
        return_value=httpx.Response(200, json={"registration_id": "r9"})
    )
    delete_route = respx.delete("http://x/hooks/before_tool_call/r9").mock(
        return_value=httpx.Response(204)
    )

    async def _raise_inside() -> None:
        async with (
            httpx.AsyncClient() as http,
            crewai_hook_session(
                {"kind": "malformed_tool_output"}, http=http, target_url="http://x"
            ) as reg,
        ):
            assert reg == "r9"
            raise RuntimeError("caller fault")

    with pytest.raises(RuntimeError, match="caller fault"):
        await _raise_inside()
    assert delete_route.call_count == 1
