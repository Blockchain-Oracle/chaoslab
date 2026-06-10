"""Shared adapter primitives — used by Tier-1 (ADK), Tier-2, Tier-3 alike.

Extracted as part of S3.3 round-2 review (PR #76) so Tier-2 adapters
(LangChain, CrewAI, OpenAI Agents SDK) and Tier-3 (HTTP black-box) inherit
the same auth / output-coercion / span-error / status-mapping shapes
instead of forking 4 subtly-different copies.

Anything that lives here MUST be framework-agnostic — no LangChain, CrewAI,
ADK, or OpenAI imports. The TargetSpec / AdapterError / opentelemetry
surface is the entire dependency set.
"""

from __future__ import annotations

import contextlib
import json
import logging
from http import HTTPStatus
from typing import Any

import httpx
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from phoenix_audit_agent.errors import (
    AdapterConnectionError,
    AdapterDiscoveryError,
    AdapterError,
    AdapterInvocationError,
)
from phoenix_audit_agent.injector.target_adapters.base import TargetSpec

logger = logging.getLogger(__name__)

# Error-body truncation — used by every adapter that surfaces an HTTP
# status mismatch. Picked one constant so 4 adapters can't drift to
# 200/500/1000-char variants over time.
MAX_ERROR_BODY: int = 500

# HTTP status sets — codes the adapter MUST map to specific exception
# types regardless of which Tier-2 endpoint produced them. Keeping these
# at module scope avoids 4 adapters defining their own constants.
_RETRYABLE_5XX: frozenset[int] = frozenset(
    {
        HTTPStatus.BAD_GATEWAY.value,
        HTTPStatus.SERVICE_UNAVAILABLE.value,
        HTTPStatus.GATEWAY_TIMEOUT.value,
    }
)


def bearer_headers(spec: TargetSpec) -> dict[str, str]:
    """Resolve `spec.auth['bearer']` into an Authorization header dict.

    Round-2 review finding (SFH-B2 + CR-#3): the previous shape silently
    sent NO auth when callers passed `auth={"api_key": "x"}` or any other
    non-`bearer` key — pattern #2 (`dict.get` returns None). Now we
    distinguish three states explicitly:

    - ``spec.auth`` is None / empty → empty dict (no auth requested)
    - ``spec.auth`` has `bearer` key → ``{"Authorization": "Bearer <token>"}``
    - ``spec.auth`` is set but missing `bearer` → ``AdapterDiscoveryError``
      naming the keys that WERE provided, so the operator sees the typo.
    """
    if not spec.auth:
        return {}
    bearer = spec.auth.get("bearer")
    if bearer is None:
        msg = (
            "spec.auth provided but no 'bearer' key — got "
            f"{sorted(spec.auth.keys())!r}. Adapters currently only accept "
            "`auth={'bearer': SecretStr(...)}`; other shapes silently send "
            "no auth header without this guard."
        )
        raise AdapterDiscoveryError(msg)
    return {"Authorization": f"Bearer {bearer.get_secret_value()}"}


def coerce_output_text(value: Any) -> tuple[str, bool]:
    """Turn a runnable/agent result of any shape into (text, was_coerced).

    LangServe wraps results as ``{"output": <string | dict | list | None>}``;
    CrewAI's ``kickoff()`` returns ``str | CrewOutput``; OpenAI Agents SDK
    returns ``Runner.run().final_output: Any``. All Tier-2/3 adapters need
    one canonical coercion so the Judge LLM downstream isn't seeing a
    Python-repr stringified dict (``"{'answer': 4}"``) and treating it as
    target output.

    Round-2 review finding (SFH-B1 + CR-#4): the previous ``str(value)``
    fallback rendered dicts with single quotes — pattern #4 (fallback
    indistinguishable from real). Now: real-string values pass through;
    dicts/lists land as ``json.dumps(sort_keys=True)``; ``None`` becomes ``""``.
    The second return value lets the caller set ``metadata["output_coerced"]``
    so Epic 6's pattern-finder can filter clusters whose evidence came
    from coerced output.
    """
    if isinstance(value, str):
        return value, False
    if value is None:
        return "", False
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False), True
    return str(value), True


async def close_http_clean(http: httpx.AsyncClient | None) -> None:
    """Close an httpx client on the HAPPY path — logs WARNING on aclose() error.

    Round-2 review finding (SFH-B3): the previous helper suppressed all
    exceptions, hiding connection-pool leaks on disconnect(). The happy
    path NEEDS to know if aclose() failed (so the operator sees the leak
    in Cloud Logging); the error path does NOT (the original error must
    propagate). Use this on disconnect(); use ``close_http_in_error_path``
    when already unwinding from another exception.
    """
    if http is None:
        return
    try:
        await http.aclose()
    except Exception:
        # Logged not suppressed — connection-pool leak on disconnect is a
        # real correctness signal, not just teardown noise.
        logger.warning("httpx_aclose_failed_on_disconnect", exc_info=True)


async def close_http_in_error_path(http: httpx.AsyncClient | None) -> None:
    """Close an httpx client while ALREADY unwinding from another exception.

    Suppresses aclose() failures so the ORIGINAL error propagates as the
    root cause. Pair with `close_http_clean` (happy path) — never use
    the same helper for both because they have different observability
    needs.
    """
    if http is None:
        return
    with contextlib.suppress(Exception):
        await http.aclose()


def record_and_raise(span: trace.Span, exc: BaseException) -> None:
    """Record `exc` on `span` AND set the span status to ERROR.

    Round-2 review finding (SFH-I3 + CR-#1): the previous adapters called
    ``span.record_exception(exc)`` only. By OTel convention that records
    the event but leaves ``StatusCode.UNSET`` — Phoenix shows the span as
    "OK" while a recorded exception sits inside. Arize alerts also key off
    ERROR status. Always set status before re-raising so the Phoenix UI
    + downstream judge eval reflect reality.

    This helper records-and-sets only; the caller raises. That keeps the
    `raise <exc>` syntax visible at the adapter call site (mypy / ty
    flow-analysis sees the raise without an extra indirection).
    """
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))


def raise_for_status(
    response: httpx.Response,
    *,
    target_url: str,
    operation: str,
) -> None:
    """Map non-2xx HTTP status to the right Adapter*Error.

    Round-2 review finding (SFH-I1): a 502/503/504 from `/invoke` is
    semantically a transport-failure (retry) — call surface needs
    ``AdapterConnectionError`` so the upstream injector retries. A
    400/403/404/422 is the caller's fault (malformed request, bad creds,
    missing resource, schema mismatch) — ``AdapterInvocationError``.
    A 401 is handled separately by callers that want auth-specific UX.

    The body is truncated to ``MAX_ERROR_BODY`` chars so a 1MB error page
    doesn't blow the log line.
    """
    status = response.status_code
    if 200 <= status < 300:  # noqa: PLR2004
        return
    body = response.text[:MAX_ERROR_BODY]
    if status in _RETRYABLE_5XX or status >= HTTPStatus.INTERNAL_SERVER_ERROR.value:
        msg = (
            f"{operation} returned HTTP {status} from {target_url} (transient — retryable): {body}"
        )
        raise AdapterConnectionError(msg)
    # 4xx (caller fault, including 401 — but callers can special-case
    # before reaching here if they want different UX).
    msg = f"{operation} returned HTTP {status} from {target_url}: {body}"
    raise AdapterInvocationError(msg)


__all__ = [
    "MAX_ERROR_BODY",
    "AdapterConnectionError",
    "AdapterDiscoveryError",
    "AdapterError",
    "AdapterInvocationError",
    "bearer_headers",
    "close_http_clean",
    "close_http_in_error_path",
    "coerce_output_text",
    "raise_for_status",
    "record_and_raise",
]
