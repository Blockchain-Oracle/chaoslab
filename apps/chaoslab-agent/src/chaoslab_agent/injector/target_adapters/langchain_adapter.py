"""Tier-2 LangChain adapter — drives a LangServe target via POST /invoke.

Per ADR-002 + S3.3 + `architecture.md` "Banned patterns": this module
MUST NOT import LangChain orchestration symbols (`from langchain import …`
or `from langchain_core …`) — that lands on every commit's banned-import
grep. The ONLY LangChain-related dependency permitted in src/ is the
`openinference-instrumentation-langchain` instrumentor (which is wired
in `observability.py`, not here).

The wire path is:
  1. ``connect()`` — probe ``GET <url>/input_schema`` (LangServe discovery).
  2. ``invoke()`` — POST ``{"input": prompt}`` to ``<url>/invoke``; if
     ``fault_config.kind == "prompt_injection"``, wrap the call in a
     ``litellm_proxy_session`` and pass ``X-LiteLLM-Base-Url`` so the
     target's LiteLLM-routed model goes through our interception point.
  3. ``fingerprint()`` — return `TIER2_LANGCHAIN` + the `input_schema`
     key set (lets S5.6 baseline-check shape future probes).
  4. ``disconnect()`` — close the httpx client.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any

import httpx
from opentelemetry import trace

from chaoslab_agent.errors import (
    AdapterConnectionError,
    AdapterDiscoveryError,
    AdapterInvocationError,
)
from chaoslab_agent.injector.target_adapters._litellm_proxy import litellm_proxy_session
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

_TRACER = trace.get_tracer(__name__)

# LangServe HTTP convention — both paths land relative to TargetSpec.url
# (which may itself include a runnable mount, e.g., `/agent`).
_INPUT_SCHEMA_PATH: str = "/input_schema"
_INVOKE_PATH: str = "/invoke"

_HTTP_OK: int = 200
_HTTP_METHOD_NOT_ALLOWED: int = 405


def _bearer_headers(spec: TargetSpec) -> dict[str, str]:
    """Pull a Bearer token from the typed `auth` dict if one was supplied."""
    if not spec.auth:
        return {}
    bearer = spec.auth.get("bearer")
    if bearer is None:
        return {}
    return {"Authorization": f"Bearer {bearer.get_secret_value()}"}


def _extract_output_text(payload: dict[str, Any]) -> str:
    """LangServe wraps the runnable result as ``{"output": <str | object>}``."""
    output = payload.get("output")
    if isinstance(output, str):
        return output
    if output is None:
        return ""
    return str(output)


class LangChainAdapter(TargetAdapter):
    """Tier-2 adapter — drives a LangServe target through its native HTTP convention."""

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._http: httpx.AsyncClient | None = None
        self._input_schema: dict[str, Any] | None = None
        self._connected: bool = False

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        headers = _bearer_headers(self.spec)
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s, headers=headers)
        try:
            resp = await self._http.get(f"{base}{_INPUT_SCHEMA_PATH}")
        except httpx.HTTPError as exc:
            await self._close_http()
            raise AdapterConnectionError(
                f"failed to reach LangServe target at {base}: {type(exc).__name__}"
            ) from exc
        if resp.status_code == _HTTP_METHOD_NOT_ALLOWED:
            # The LangServe deployment disabled schema endpoints. Distinct
            # from 404 — surface a clear remediation hint so an operator
            # doesn't waste time chasing networking.
            await self._close_http()
            raise AdapterDiscoveryError(
                f"LangServe target {base} has {_INPUT_SCHEMA_PATH} disabled — "
                "set `enabled_endpoints=['invoke','input_schema']` on add_routes"
            )
        if resp.status_code != _HTTP_OK:
            await self._close_http()
            raise AdapterDiscoveryError(
                f"LangServe target {base} returned HTTP {resp.status_code} on {_INPUT_SCHEMA_PATH}"
            )
        try:
            self._input_schema = resp.json()
        except ValueError as exc:
            await self._close_http()
            raise AdapterDiscoveryError(
                f"LangServe target {base} returned non-JSON on {_INPUT_SCHEMA_PATH}"
            ) from exc
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        # Real guard (not assert) — `python -O` strips asserts in production.
        if self._http is None:
            raise AdapterConnectionError("LangChainAdapter.invoke called without an active client")
        base = str(self.spec.url).rstrip("/")
        start = time.perf_counter()
        span_ids: list[str] = []
        response_text = ""
        error: str | None = None

        async with litellm_proxy_session(invocation.fault_config) as proxy:
            with _TRACER.start_as_current_span("chaoslab.adapter.langchain.invoke") as span:
                span_ids.append(format(span.get_span_context().span_id, "016x"))
                headers: dict[str, str] = {}
                if proxy is not None:
                    headers["X-LiteLLM-Base-Url"] = proxy.base_url
                try:
                    resp = await self._http.post(
                        f"{base}{_INVOKE_PATH}",
                        json={"input": invocation.prompt},
                        headers=headers or None,
                    )
                except httpx.HTTPError as exc:
                    span.record_exception(exc)
                    raise AdapterConnectionError(
                        f"transport error to {base}{_INVOKE_PATH}: {type(exc).__name__}"
                    ) from exc
                if resp.status_code != _HTTP_OK:
                    err = AdapterInvocationError(
                        f"LangServe {_INVOKE_PATH} returned HTTP {resp.status_code}: "
                        f"{resp.text[:500]}"
                    )
                    span.record_exception(err)
                    raise err
                try:
                    payload = resp.json()
                except ValueError as exc:
                    span.record_exception(exc)
                    raise AdapterInvocationError(
                        f"LangServe {_INVOKE_PATH} returned non-JSON body: {resp.text[:200]}"
                    ) from exc
                response_text = _extract_output_text(payload)

        duration_ms = (time.perf_counter() - start) * 1000.0
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=duration_ms,
            error=error,
            metadata={"langserve_endpoint": f"{base}{_INVOKE_PATH}"},
        )

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        return AdapterFingerprint(
            tier=AdapterTier.TIER2_LANGCHAIN,
            framework="langchain",
            agent_card=None,
            discovery_path="input_schema",
            behavioral_signals={
                "input_schema_keys": sorted((self._input_schema or {}).keys()),
            },
        )

    async def disconnect(self) -> None:
        await self._close_http()
        self._input_schema = None
        self._connected = False

    async def _close_http(self) -> None:
        if self._http is None:
            return
        http, self._http = self._http, None
        # Best-effort cleanup — adapter is already in a teardown path; a
        # secondary failure here would mask the original error.
        with contextlib.suppress(Exception):
            await http.aclose()


__all__ = ["LangChainAdapter"]
