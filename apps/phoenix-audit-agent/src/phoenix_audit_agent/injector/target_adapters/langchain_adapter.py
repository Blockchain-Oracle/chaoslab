"""Tier-2 LangChain adapter — drives a LangServe target via POST /invoke.

Per ADR-002 + S3.3 + `architecture.md` "Banned patterns": this module
MUST NOT import LangChain orchestration symbols (`from langchain import …`
or `from langchain_core …`) — that lands on every commit's banned-import
grep. The ONLY LangChain-related dependency permitted in src/ is the
`openinference-instrumentation-langchain` instrumentor (wired in
`observability.py`, not here).

Wire path:
  1. ``connect()`` — probe ``GET <url>/input_schema`` (LangServe discovery).
  2. ``invoke()`` — POST ``{"input": prompt}`` to ``<url>/invoke``; if
     ``fault_config.kind == "prompt_injection"``, wrap the call in a
     ``litellm_proxy_session`` and pass ``X-LiteLLM-Base-Url`` so the
     target's LiteLLM-routed model goes through our interception point.
  3. ``fingerprint()`` — return `TIER2_LANGCHAIN` + the `input_schema`
     key set (lets S5.6 baseline-check shape future probes).
  4. ``disconnect()`` — close the httpx client.

Round-2: status mapping, output coercion, bearer headers, span error-status,
and close-http variants all live in `_common.py` so S3.4-3.6 inherit the
fixed shapes instead of forking.
"""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any

import httpx
from opentelemetry import trace

from phoenix_audit_agent.errors import (
    AdapterConnectionError,
    AdapterDiscoveryError,
    AdapterInvocationError,
)
from phoenix_audit_agent.injector.target_adapters._common import (
    bearer_headers,
    close_http_clean,
    close_http_in_error_path,
    coerce_output_text,
    raise_for_status,
    record_and_raise,
)
from phoenix_audit_agent.injector.target_adapters._litellm_proxy import litellm_proxy_session
from phoenix_audit_agent.injector.target_adapters.base import (
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
        # bearer_headers raises AdapterDiscoveryError if spec.auth has keys
        # other than 'bearer' — failing here is BETTER than silently sending
        # no auth and chasing a 401 later (SFH-B2).
        headers = bearer_headers(self.spec)
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s, headers=headers)
        try:
            resp = await self._http.get(f"{base}{_INPUT_SCHEMA_PATH}")
        except httpx.HTTPError as exc:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterConnectionError(
                f"failed to reach LangServe target at {base}: {type(exc).__name__}"
            ) from exc
        if resp.status_code == HTTPStatus.METHOD_NOT_ALLOWED.value:
            # The LangServe deployment disabled schema endpoints. Distinct
            # from 404 — surface a clear remediation hint so an operator
            # doesn't waste time chasing networking.
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"LangServe target {base} has {_INPUT_SCHEMA_PATH} disabled — "
                "set `enabled_endpoints=['invoke','input_schema']` on add_routes"
            )
        if resp.status_code != HTTPStatus.OK.value:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"LangServe target {base} returned HTTP {resp.status_code} on {_INPUT_SCHEMA_PATH}"
            )
        try:
            self._input_schema = resp.json()
        except ValueError as exc:
            await close_http_in_error_path(self._http)
            self._http = None
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

        async with litellm_proxy_session(invocation.fault_config) as proxy:
            with _TRACER.start_as_current_span("phoenix-audit.adapter.langchain.invoke") as span:
                span_ids.append(format(span.get_span_context().span_id, "016x"))
                response_text, output_coerced = await self._post_invoke(
                    base, invocation.prompt, span, proxy_base_url=getattr(proxy, "base_url", None)
                )

        duration_ms = (time.perf_counter() - start) * 1000.0
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=duration_ms,
            metadata={
                "langserve_endpoint": f"{base}{_INVOKE_PATH}",
                "output_coerced": output_coerced,
            },
        )

    async def _post_invoke(
        self,
        base: str,
        prompt: str,
        span: trace.Span,
        *,
        proxy_base_url: str | None,
    ) -> tuple[str, bool]:
        """POST /invoke, surface errors via span+error-status, return coerced text."""
        if self._http is None:
            raise AdapterConnectionError(
                "LangChainAdapter._post_invoke called without an active client"
            )
        headers: dict[str, str] = {}
        if proxy_base_url is not None:
            headers["X-LiteLLM-Base-Url"] = proxy_base_url
        try:
            resp = await self._http.post(
                f"{base}{_INVOKE_PATH}",
                json={"input": prompt},
                headers=headers or None,
            )
        except httpx.HTTPError as exc:
            record_and_raise(span, exc)
            raise AdapterConnectionError(
                f"transport error to {base}{_INVOKE_PATH}: {type(exc).__name__}"
            ) from exc
        # raise_for_status maps 5xx → AdapterConnectionError (retryable),
        # 4xx → AdapterInvocationError (caller fault). Records on span too.
        try:
            raise_for_status(resp, target_url=base, operation=f"LangServe {_INVOKE_PATH}")
        except (AdapterConnectionError, AdapterInvocationError) as exc:
            record_and_raise(span, exc)
            raise
        try:
            payload = resp.json()
        except ValueError as exc:
            record_and_raise(span, exc)
            raise AdapterInvocationError(
                f"LangServe {_INVOKE_PATH} returned non-JSON body: {resp.text[:200]}"
            ) from exc
        return coerce_output_text(payload.get("output"))

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
        # Happy-path teardown — close_http_clean LOGS WARNING on aclose
        # failure rather than swallowing it silently (SFH-B3). Connection-
        # pool leaks on disconnect deserve to be observable.
        if self._http is not None:
            http, self._http = self._http, None
            await close_http_clean(http)
        self._input_schema = None
        self._connected = False


__all__ = ["LangChainAdapter"]
