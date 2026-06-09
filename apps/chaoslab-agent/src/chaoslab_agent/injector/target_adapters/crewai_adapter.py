"""Tier-2 CrewAI adapter — drives a CrewAI crew via its HTTP kickoff convention.

Per ADR-002 + S3.4 + `architecture.md` "Banned patterns": this module MUST
NOT import CrewAI orchestration symbols (`from crewai import …`). The ONLY
CrewAI-related dependency permitted in src/ is the
`openinference-instrumentation-crewai` instrumentor (wired in
`observability.py`, not here).

Wire path:
  1. ``connect()`` — probe ``GET <url>/crew/info`` for the crew name + tools.
  2. ``invoke()`` — POST ``{"inputs": {"prompt": prompt}}`` to ``/kickoff``;
     receive ``{"kickoff_id": ...}`` and poll ``/kickoff/<id>`` until
     ``status in {completed, failed}`` or timeout. If
     ``fault_config.kind == "malformed_tool_output"``, register a
     ``@before_tool_call`` hook on the target's webhook surface for the
     invocation duration via ``crewai_hook_session``.
  3. ``fingerprint()`` — return ``TIER2_CREWAI`` + ``tool_count`` + ``crew_name``
     so the Injector can decide which faults to schedule.
  4. ``disconnect()`` — close the httpx client.

Round-2 shared primitives (from S3.3): bearer auth, output coercion, span
ERROR status, status-mapping, close-http variants. CrewAI inherits the
same correctness shapes.
"""

from __future__ import annotations

import asyncio
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
from chaoslab_agent.injector.target_adapters._crewai_hook_proxy import crewai_hook_session
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

_TRACER = trace.get_tracer(__name__)

# CrewAI Enterprise-style endpoints — both paths land under TargetSpec.url.
_CREW_INFO_PATH: str = "/crew/info"
_KICKOFF_PATH: str = "/kickoff"

# Polling cadence. Deliberately a small constant — the per-tick wait is
# bounded by `spec.timeout_s` overall, and the unit tests assert exact
# call counts. POLL_MAX_S caps the absolute wall-clock the adapter will
# wait before raising AdapterInvocationError("timed out") even when the
# user passed a much higher spec.timeout_s — kickoff workflows that don't
# converge in 60s are pathological from the auditor's perspective.
POLL_INTERVAL_S: float = 0.5
POLL_MAX_S: float = 60.0

_STATUS_COMPLETED: str = "completed"
_STATUS_FAILED: str = "failed"


class CrewAIAdapter(TargetAdapter):
    """Tier-2 adapter — drives a CrewAI crew via its HTTP kickoff convention."""

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._http: httpx.AsyncClient | None = None
        self._crew_info: dict[str, Any] | None = None
        self._connected: bool = False

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        headers = bearer_headers(self.spec)
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s, headers=headers)
        try:
            resp = await self._http.get(f"{base}{_CREW_INFO_PATH}")
        except httpx.HTTPError as exc:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterConnectionError(
                f"failed to reach CrewAI target at {base}: {type(exc).__name__}"
            ) from exc
        if resp.status_code != HTTPStatus.OK.value:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"CrewAI target {base} returned HTTP {resp.status_code} on {_CREW_INFO_PATH}"
            )
        try:
            self._crew_info = resp.json()
        except ValueError as exc:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"CrewAI target {base} returned non-JSON on {_CREW_INFO_PATH}"
            ) from exc
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        if self._http is None:
            raise AdapterConnectionError("CrewAIAdapter.invoke called without an active client")
        base = str(self.spec.url).rstrip("/")
        start = time.perf_counter()
        span_ids: list[str] = []

        async with crewai_hook_session(
            invocation.fault_config, http=self._http, target_url=base
        ) as registration_id:
            with _TRACER.start_as_current_span("chaoslab.adapter.crewai.invoke") as span:
                span_ids.append(format(span.get_span_context().span_id, "016x"))
                response_text, output_coerced = await self._kickoff_and_poll(
                    base, invocation.prompt, span
                )

        duration_ms = (time.perf_counter() - start) * 1000.0
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=duration_ms,
            metadata={
                "crewai_endpoint": f"{base}{_KICKOFF_PATH}",
                "crew_name": (self._crew_info or {}).get("name"),
                "output_coerced": output_coerced,
                "hook_registration_id": registration_id,
            },
        )

    async def _kickoff_and_poll(self, base: str, prompt: str, span: trace.Span) -> tuple[str, bool]:
        """POST /kickoff → poll /kickoff/<id> → return coerced result text."""
        if self._http is None:
            raise AdapterConnectionError(
                "CrewAIAdapter._kickoff_and_poll called without an active client"
            )
        try:
            kickoff_resp = await self._http.post(
                f"{base}{_KICKOFF_PATH}",
                json={"inputs": {"prompt": prompt}},
            )
        except httpx.HTTPError as exc:
            record_and_raise(span, exc)
            raise AdapterConnectionError(
                f"transport error to {base}{_KICKOFF_PATH}: {type(exc).__name__}"
            ) from exc
        # CrewAI Enterprise returns 202 on accepted; some self-hosted shapes
        # return 200. Both are success — anything else maps via raise_for_status.
        if kickoff_resp.status_code not in (HTTPStatus.OK.value, HTTPStatus.ACCEPTED.value):
            try:
                raise_for_status(kickoff_resp, target_url=base, operation=f"CrewAI {_KICKOFF_PATH}")
            except (AdapterConnectionError, AdapterInvocationError) as exc:
                record_and_raise(span, exc)
                raise
        try:
            payload = kickoff_resp.json()
        except ValueError as exc:
            record_and_raise(span, exc)
            raise AdapterInvocationError(
                f"CrewAI {_KICKOFF_PATH} returned non-JSON body: {kickoff_resp.text[:200]}"
            ) from exc
        kickoff_id = payload.get("kickoff_id")
        if not kickoff_id:
            err = AdapterInvocationError(
                f"CrewAI {_KICKOFF_PATH} response missing kickoff_id: {payload}"
            )
            record_and_raise(span, err)
            raise err
        return await self._poll(base, kickoff_id, span)

    async def _poll(self, base: str, kickoff_id: str, span: trace.Span) -> tuple[str, bool]:
        """Poll `/kickoff/<id>` until status==completed | failed or timeout."""
        if self._http is None:
            raise AdapterConnectionError("CrewAIAdapter._poll called without an active client")
        # Deadline: min(POLL_MAX_S, spec.timeout_s) so a generous spec.timeout
        # doesn't accidentally allow a kickoff to hang for 5 minutes.
        deadline = time.perf_counter() + min(POLL_MAX_S, self.spec.timeout_s)
        while time.perf_counter() < deadline:
            try:
                resp = await self._http.get(f"{base}{_KICKOFF_PATH}/{kickoff_id}")
            except httpx.HTTPError as exc:
                record_and_raise(span, exc)
                raise AdapterConnectionError(
                    f"transport error polling {base}{_KICKOFF_PATH}/{kickoff_id}: "
                    f"{type(exc).__name__}"
                ) from exc
            try:
                raise_for_status(resp, target_url=base, operation=f"CrewAI {_KICKOFF_PATH}/<id>")
            except (AdapterConnectionError, AdapterInvocationError) as exc:
                record_and_raise(span, exc)
                raise
            try:
                data = resp.json()
            except ValueError as exc:
                record_and_raise(span, exc)
                raise AdapterInvocationError(
                    f"CrewAI status poll returned non-JSON: {resp.text[:200]}"
                ) from exc
            status = data.get("status")
            if status == _STATUS_COMPLETED:
                return coerce_output_text(data.get("result"))
            if status == _STATUS_FAILED:
                err = AdapterInvocationError(f"crew kickoff failed: {data}")
                record_and_raise(span, err)
                raise err
            await asyncio.sleep(POLL_INTERVAL_S)
        err = AdapterInvocationError(
            f"CrewAI kickoff {kickoff_id} timed out after "
            f"{min(POLL_MAX_S, self.spec.timeout_s):.1f}s"
        )
        record_and_raise(span, err)
        raise err

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        info = self._crew_info or {}
        tools = info.get("tools") or []
        return AdapterFingerprint(
            tier=AdapterTier.TIER2_CREWAI,
            framework="crewai",
            agent_card=None,
            discovery_path="crew_info",
            behavioral_signals={
                "crew_name": info.get("name"),
                "tool_count": len(tools),
                # Allow Injector to skip malformed_tool_output faults against
                # targets that don't opt in to the hook surface — when this
                # is False S5.7 must NOT schedule that fault.
                "hooks_available": "hooks" in info,
            },
        )

    async def disconnect(self) -> None:
        if self._http is not None:
            http, self._http = self._http, None
            await close_http_clean(http)
        self._crew_info = None
        self._connected = False


__all__ = ["CrewAIAdapter"]
