"""Unit tests for shared adapter primitives in `_common.py`.

These helpers are consumed by every Tier (ADK, LangChain, future CrewAI /
OpenAI Agents SDK / HTTP black-box) — testing them ONCE here pins the
behavior for the whole adapter family.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from opentelemetry.trace import Status, StatusCode

from chaoslab_agent.errors import (
    AdapterConnectionError,
    AdapterDiscoveryError,
    AdapterInvocationError,
)
from chaoslab_agent.injector.target_adapters._common import (
    MAX_ERROR_BODY,
    bearer_headers,
    close_http_clean,
    close_http_in_error_path,
    coerce_output_text,
    raise_for_status,
    record_and_raise,
)
from chaoslab_agent.injector.target_adapters.base import TargetSpec


def _spec(**overrides: object) -> TargetSpec:
    payload: dict[str, object] = {"tier": "tier2_langchain", "url": "http://localhost:8002/agent"}
    payload.update(overrides)
    return TargetSpec.model_validate(payload)


# ---------------------------------------------------------------------------
# bearer_headers — SFH-B2 + CR-#3 (shared shape, explicit raise)
# ---------------------------------------------------------------------------


def test_bearer_headers_returns_empty_dict_when_auth_absent() -> None:
    assert bearer_headers(_spec()) == {}


def test_bearer_headers_returns_authorization_header_when_bearer_set() -> None:
    from pydantic import SecretStr

    headers = bearer_headers(_spec(auth={"bearer": SecretStr("tok")}))
    assert headers == {"Authorization": "Bearer tok"}


def test_bearer_headers_raises_on_non_bearer_key() -> None:
    """Round-1 silently sent NO auth here — pattern #2. Now raises so the
    operator sees the typo immediately."""
    from pydantic import SecretStr

    with pytest.raises(AdapterDiscoveryError, match="no 'bearer' key"):
        bearer_headers(_spec(auth={"api_key": SecretStr("x")}))


# ---------------------------------------------------------------------------
# coerce_output_text — SFH-B1 + CR-#4 (canonical JSON, no Python repr)
# ---------------------------------------------------------------------------


def test_coerce_string_passes_through_uncoerced() -> None:
    text, coerced = coerce_output_text("hello")
    assert text == "hello"
    assert coerced is False


def test_coerce_none_becomes_empty_string_uncoerced() -> None:
    text, coerced = coerce_output_text(None)
    assert text == ""
    assert coerced is False


def test_coerce_dict_renders_canonical_json_with_marker() -> None:
    """Round-1 used `str(dict)` → Python repr with single quotes. Now
    `json.dumps(sort_keys=True)` so the regulator-facing audit sees
    canonical JSON, not Python syntax."""
    text, coerced = coerce_output_text({"answer": 4})
    assert text == '{"answer": 4}'
    assert coerced is True


def test_coerce_list_renders_canonical_json() -> None:
    text, coerced = coerce_output_text(["a", "b"])
    assert text == '["a", "b"]'
    assert coerced is True


def test_coerce_dict_keys_sorted_for_determinism() -> None:
    """Coerced output must be byte-deterministic across runs — keys sorted."""
    text_a, _ = coerce_output_text({"b": 1, "a": 2})
    text_b, _ = coerce_output_text({"a": 2, "b": 1})
    assert text_a == text_b == '{"a": 2, "b": 1}'


def test_coerce_int_falls_back_to_str_with_marker() -> None:
    text, coerced = coerce_output_text(42)
    assert text == "42"
    assert coerced is True


# ---------------------------------------------------------------------------
# raise_for_status — SFH-I1 (5xx → ConnectionError, 4xx → InvocationError)
# ---------------------------------------------------------------------------


def test_raise_for_status_passes_2xx_silently() -> None:
    resp = httpx.Response(200, text="ok")
    # No exception → passes.
    raise_for_status(resp, target_url="http://x", operation="test")


@pytest.mark.parametrize("status", [502, 503, 504])
def test_raise_for_status_5xx_maps_to_connection_error(status: int) -> None:
    """Round-2 SFH-I1: 5xx is semantically transport-failure (retry)."""
    resp = httpx.Response(status, text="upstream")
    with pytest.raises(AdapterConnectionError, match=str(status)):
        raise_for_status(resp, target_url="http://x", operation="test")


@pytest.mark.parametrize("status", [400, 403, 404, 422])
def test_raise_for_status_4xx_maps_to_invocation_error(status: int) -> None:
    """Round-2 SFH-I1: 4xx is caller-fault (do not retry)."""
    resp = httpx.Response(status, text="bad request")
    with pytest.raises(AdapterInvocationError, match=str(status)):
        raise_for_status(resp, target_url="http://x", operation="test")


def test_raise_for_status_truncates_long_bodies() -> None:
    """A 1MB error page would blow the log line — bodies clip to MAX_ERROR_BODY."""
    long_body = "X" * (MAX_ERROR_BODY * 10)
    resp = httpx.Response(500, text=long_body)
    with pytest.raises(AdapterConnectionError) as exc_info:
        raise_for_status(resp, target_url="http://x", operation="test")
    # Error message includes truncated body — never the full 1MB.
    assert "X" * MAX_ERROR_BODY in str(exc_info.value)
    assert long_body not in str(exc_info.value)


# ---------------------------------------------------------------------------
# record_and_raise — SFH-I3 + CR-#1 (set span ERROR status)
# ---------------------------------------------------------------------------


def test_record_and_raise_calls_record_exception_and_set_status_error() -> None:
    """Round-2 review: round-1 called only `record_exception`, leaving the
    span at StatusCode.UNSET — Phoenix showed OK with a buried exception.
    Helper now sets status to ERROR so the span reflects reality."""
    span = MagicMock()
    exc = RuntimeError("kaboom")
    record_and_raise(span, exc)
    span.record_exception.assert_called_once_with(exc)
    span.set_status.assert_called_once()
    status_arg = span.set_status.call_args[0][0]
    assert isinstance(status_arg, Status)
    assert status_arg.status_code == StatusCode.ERROR
    assert "kaboom" in (status_arg.description or "")


# ---------------------------------------------------------------------------
# close_http variants — SFH-B3 (separate happy vs error paths)
# ---------------------------------------------------------------------------


async def test_close_http_clean_handles_none() -> None:
    """No-op on None — adapters may call disconnect() before connect()."""
    await close_http_clean(None)


async def test_close_http_clean_logs_warning_on_aclose_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Round-2 SFH-B3: happy-path aclose failure is LOGGED (not silently
    swallowed) so connection-pool leaks on disconnect are observable."""
    import logging as _logging

    http = MagicMock()
    failed_close = MagicMock(side_effect=RuntimeError("aclose dead"))

    async def _aclose() -> None:
        failed_close()

    http.aclose = _aclose
    _common_logger = "chaoslab_agent.injector.target_adapters._common"
    with caplog.at_level(_logging.WARNING, logger=_common_logger):
        await close_http_clean(http)
    assert any("httpx_aclose_failed_on_disconnect" in r.message for r in caplog.records)


async def test_close_http_in_error_path_suppresses_silently() -> None:
    """Error path: secondary failure here would mask the ORIGINAL exception."""
    http = MagicMock()

    async def _aclose() -> None:
        raise RuntimeError("aclose dead in error path")

    http.aclose = _aclose
    # No exception expected — suppressed by design.
    await close_http_in_error_path(http)


async def test_close_http_in_error_path_handles_none() -> None:
    await close_http_in_error_path(None)
