"""Tier-2 OpenAI Agents SDK adapter — drives a target via POST /run.

Per ADR-002 + S3.5 + `architecture.md` "Banned patterns": this module MUST
NOT import OpenAI / Anthropic runtime LLM SDKs (`from openai import …`,
`from anthropic import …`). The ONLY OpenAI-Agents-related dependency
permitted in src/ is the `openinference-instrumentation-openai-agents`
instrumentor (wired in `observability.py`, not here).

Wire path:
  1. ``connect()`` — probe ``GET <url>/agents`` listing endpoint.
  2. ``invoke()`` — POST ``{"input": prompt, "agent_name": <first>}`` to
     ``/run``; if `fault_config.kind == "malformed_tool_output"`, register
     a `function_tool` hook via `/hooks/function_tool` for the duration.
  3. ``fingerprint()`` — return ``TIER2_OPENAI_SDK`` + `agent_count` so
     the Injector can shape future probes.
  4. ``disconnect()`` — close the httpx client.
"""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any

import httpx
from opentelemetry import trace

from chaoslab_agent.errors import (
    AdapterConnectionError,
    AdapterDiscoveryError,
    AdapterInvocationError,
)
from chaoslab_agent.injector.target_adapters._common import (
    bearer_headers,
    close_http_clean,
    close_http_in_error_path,
    coerce_output_text,
    raise_for_status,
    record_and_raise,
)
from chaoslab_agent.injector.target_adapters._webhook_fault_proxy import (
    webhook_fault_session,
)
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

_TRACER = trace.get_tracer(__name__)

_AGENTS_PATH: str = "/agents"
_RUN_PATH: str = "/run"
_HOOK_PATH: str = "/hooks/function_tool"
_FAULT_KIND: str = "malformed_tool_output"


class OpenAISDKAdapter(TargetAdapter):
    """Tier-2 adapter — drives an OpenAI Agents SDK target via `/run`."""

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._http: httpx.AsyncClient | None = None
        self._agents_info: list[dict[str, Any]] | None = None
        self._connected: bool = False

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        headers = bearer_headers(self.spec)
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s, headers=headers)
        try:
            resp = await self._http.get(f"{base}{_AGENTS_PATH}")
        except httpx.HTTPError as exc:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterConnectionError(
                f"failed to reach OpenAI Agents SDK target at {base}: {type(exc).__name__}"
            ) from exc
        if resp.status_code != HTTPStatus.OK.value:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"OpenAI Agents SDK target {base} returned HTTP "
                f"{resp.status_code} on {_AGENTS_PATH}"
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"OpenAI Agents SDK target {base} returned non-JSON on {_AGENTS_PATH}"
            ) from exc
        if not isinstance(payload, list) or len(payload) == 0:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"OpenAI Agents SDK target {base} returned empty / non-list "
                f"payload on {_AGENTS_PATH}: {payload!r}"
            )
        self._agents_info = payload
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        if self._http is None:
            raise AdapterConnectionError("OpenAISDKAdapter.invoke called without an active client")
        base = str(self.spec.url).rstrip("/")
        start = time.perf_counter()
        span_ids: list[str] = []

        async with webhook_fault_session(
            invocation.fault_config,
            http=self._http,
            target_url=base,
            hook_path=_HOOK_PATH,
            fault_kind=_FAULT_KIND,
        ) as registration_id:
            with _TRACER.start_as_current_span("chaoslab.adapter.openai_sdk.invoke") as span:
                span_ids.append(format(span.get_span_context().span_id, "016x"))
                response_text, output_coerced = await self._post_run(base, invocation.prompt, span)

        duration_ms = (time.perf_counter() - start) * 1000.0
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=duration_ms,
            metadata={
                "openai_sdk_endpoint": f"{base}{_RUN_PATH}",
                "agent_name": self._default_agent_name(),
                "output_coerced": output_coerced,
                "hook_registration_id": registration_id,
            },
        )

    async def _post_run(self, base: str, prompt: str, span: trace.Span) -> tuple[str, bool]:
        """POST /run and surface errors via span+ERROR-status helpers."""
        if self._http is None:
            raise AdapterConnectionError(
                "OpenAISDKAdapter._post_run called without an active client"
            )
        body: dict[str, Any] = {"input": prompt}
        agent_name = self._default_agent_name()
        if agent_name is not None:
            body["agent_name"] = agent_name
        try:
            resp = await self._http.post(f"{base}{_RUN_PATH}", json=body)
        except httpx.HTTPError as exc:
            record_and_raise(span, exc)
            raise AdapterConnectionError(
                f"transport error to {base}{_RUN_PATH}: {type(exc).__name__}"
            ) from exc
        try:
            raise_for_status(resp, target_url=base, operation=f"OpenAI Agents SDK {_RUN_PATH}")
        except (AdapterConnectionError, AdapterInvocationError) as exc:
            record_and_raise(span, exc)
            raise
        try:
            payload = resp.json()
        except ValueError as exc:
            record_and_raise(span, exc)
            raise AdapterInvocationError(
                f"OpenAI Agents SDK {_RUN_PATH} returned non-JSON body: {resp.text[:200]}"
            ) from exc
        return coerce_output_text(payload.get("output"))

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        agents = self._agents_info or []
        return AdapterFingerprint(
            tier=AdapterTier.TIER2_OPENAI_SDK,
            framework="openai-agents",
            agent_card=None,
            discovery_path="agents_listing",
            behavioral_signals={
                "agent_count": len(agents),
                "agent_names": [a.get("name") for a in agents if a.get("name")],
                # Same opt-in marker as the CrewAI adapter — S5.7 Injector
                # skips `malformed_tool_output` against targets without hooks.
                "hooks_available": any(a.get("hooks") for a in agents),
            },
        )

    async def disconnect(self) -> None:
        if self._http is not None:
            http, self._http = self._http, None
            await close_http_clean(http)
        self._agents_info = None
        self._connected = False

    def _default_agent_name(self) -> str | None:
        """Pick the first agent's name as the default for /run dispatch."""
        if not self._agents_info:
            return None
        first = self._agents_info[0]
        return first.get("name")


__all__ = ["OpenAISDKAdapter"]
