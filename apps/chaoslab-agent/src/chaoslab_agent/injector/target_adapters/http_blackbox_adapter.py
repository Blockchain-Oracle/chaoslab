"""Tier-3 HTTP black-box adapter — for opaque agents with NO known framework.

Per ADR-002 + S3.6: discovers the target via a fallback chain (see
`_discovery.py`) and invokes it with a generic JSON shape. Tier-3 fault
injection is PROMPT-LEVEL ONLY — there's no callback registration surface
because the framework is unknown.

Wire path:
  1. ``connect()`` — `run_discovery_chain(http, base)`; raise
     ``AdapterDiscoveryError`` carrying `probes_attempted` if all fail.
  2. ``invoke()`` — POST `{"input": prompt, "prompt": prompt, "message": prompt}`
     directly to `base`. If `fault_config.kind == "prompt_injection"`, append
     the payload to the prompt before sending. Probe response fields in a
     fixed-priority list (output, response, answer, text, message, content,
     result) to extract a string response.
  3. ``fingerprint()`` — return Tier3 + the discovery_path + payload as
     agent_card; call `behavioral_fingerprint` (v0 stub).
  4. ``disconnect()`` — close the httpx client.
"""

from __future__ import annotations

import time
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
from chaoslab_agent.injector.target_adapters._discovery import (
    DiscoveryResult,
    run_discovery_chain,
)
from chaoslab_agent.injector.target_adapters._fingerprint import behavioral_fingerprint
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

_TRACER = trace.get_tracer(__name__)

# Response field priority — probed in this order. Picked from common
# chat-API conventions (LangServe, OpenAI Agents SDK, Anthropic, ad-hoc).
# Keep the list small and ordered: too many fields = more chance of
# returning the wrong substring (e.g., a debug field named `text` shadowing
# the real answer at `output`).
_RESPONSE_FIELDS: tuple[str, ...] = (
    "output",
    "response",
    "answer",
    "text",
    "message",
    "content",
    "result",
)

_PROMPT_INJECTION_KIND: str = "prompt_injection"


class HTTPBlackboxAdapter(TargetAdapter):
    """Tier-3 adapter — discovers + drives any HTTP agent via opaque probing."""

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._http: httpx.AsyncClient | None = None
        self._discovery_result: DiscoveryResult | None = None
        self._fingerprint_cache: dict[str, Any] | None = None
        self._connected: bool = False

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        # follow_redirects=True — many enterprise targets redirect
        # `/.well-known/...` to a CDN-served path.
        headers = bearer_headers(self.spec)
        self._http = httpx.AsyncClient(
            timeout=self.spec.timeout_s,
            headers=headers,
            follow_redirects=True,
        )
        try:
            result = await run_discovery_chain(self._http, base)
        except Exception:
            await close_http_in_error_path(self._http)
            self._http = None
            raise
        if result.discovery_path is None:
            await close_http_in_error_path(self._http)
            self._http = None
            raise AdapterDiscoveryError(
                f"all discovery probes failed for {base}; "
                f"attempted={result.probes_attempted!r}; "
                f"raw_responses={result.raw_responses!r}"
            )
        self._discovery_result = result
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        if self._http is None or self._discovery_result is None:
            raise AdapterConnectionError(
                "HTTPBlackboxAdapter.invoke called without an active client"
            )
        base = str(self.spec.url).rstrip("/")
        start = time.perf_counter()
        span_ids: list[str] = []

        with _TRACER.start_as_current_span("chaoslab.adapter.http_blackbox.invoke") as span:
            span_ids.append(format(span.get_span_context().span_id, "016x"))
            response_text, output_coerced = await self._post_opaque(base, invocation, span)

        duration_ms = (time.perf_counter() - start) * 1000.0
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=duration_ms,
            metadata={
                "discovery_path": self._discovery_result.discovery_path,
                "output_coerced": output_coerced,
                "fault_applied": _fault_kind_or_none(invocation.fault_config),
            },
        )

    async def _post_opaque(
        self,
        base: str,
        invocation: AdapterInvocation,
        span: trace.Span,
    ) -> tuple[str, bool]:
        """POST a generic chat-shape body; extract the first known response field."""
        if self._http is None:
            raise AdapterConnectionError(
                "HTTPBlackboxAdapter._post_opaque called without an active client"
            )
        # Tier-3 fault: prompt-level only (no callback surface available).
        final_prompt = _apply_prompt_injection(invocation.prompt, invocation.fault_config)
        # Generic body — set every common key so the target's deserializer
        # finds at least one. Unknown keys are ignored by typical Pydantic
        # / FastAPI / Flask validators.
        body: dict[str, Any] = {
            "input": final_prompt,
            "prompt": final_prompt,
            "message": final_prompt,
        }
        try:
            resp = await self._http.post(base, json=body)
        except httpx.HTTPError as exc:
            record_and_raise(span, exc)
            raise AdapterConnectionError(
                f"transport error to {base}: {type(exc).__name__}"
            ) from exc
        try:
            raise_for_status(resp, target_url=base, operation="HTTP black-box POST")
        except (AdapterConnectionError, AdapterInvocationError) as exc:
            record_and_raise(span, exc)
            raise
        payload = _decode_response(resp)
        extracted = _extract_response_text(payload)
        if extracted is not None:
            return extracted, False
        # No known field hit — coerce the whole payload via the shared
        # helper so the regulator-facing audit gets canonical JSON, not
        # Python repr.
        return coerce_output_text(payload)

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        if self._http is None or self._discovery_result is None:
            raise AdapterConnectionError(
                "HTTPBlackboxAdapter.fingerprint called without an active client"
            )
        agent_card = (
            self._discovery_result.payload
            if self._discovery_result.discovery_path == "agent_card"
            else None
        )
        if self._fingerprint_cache is None:
            base = str(self.spec.url).rstrip("/")
            self._fingerprint_cache = await behavioral_fingerprint(
                self._http,
                base,
                opts={"system_prompt": True, "style": True, "streaming": False},
            )
        return AdapterFingerprint(
            tier=AdapterTier.TIER3_HTTP_BLACKBOX,
            framework=None,
            agent_card=agent_card,
            discovery_path=self._discovery_result.discovery_path,
            behavioral_signals={
                "probes_attempted": self._discovery_result.probes_attempted,
                "behavioral": self._fingerprint_cache,
                # Tier 3 has NO callback surface — Injector must not
                # schedule tool-hook faults.
                "hooks_available": False,
            },
        )

    async def disconnect(self) -> None:
        if self._http is not None:
            http, self._http = self._http, None
            await close_http_clean(http)
        self._discovery_result = None
        self._fingerprint_cache = None
        self._connected = False


def _apply_prompt_injection(prompt: str, fault_config: dict[str, Any] | None) -> str:
    """If fault_config is prompt_injection, append the payload to the prompt."""
    if fault_config is None or fault_config.get("kind") != _PROMPT_INJECTION_KIND:
        return prompt
    payload = fault_config.get("payload") or ""
    if not payload:
        return prompt
    return f"{prompt}\n\n{payload}"


def _fault_kind_or_none(fault_config: dict[str, Any] | None) -> str | None:
    if fault_config is None:
        return None
    return fault_config.get("kind")


def _decode_response(resp: httpx.Response) -> Any:
    """Decode response as JSON when the content-type advertises it; else raw text.

    Defensive: some targets return `text/plain` even when the body IS JSON.
    On `application/json` we attempt `.json()` and fall back to raw text
    on parse failure (regulator gets the actual bytes, not nothing).
    """
    content_type = resp.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            return resp.json()
        except ValueError:
            return resp.text
    return resp.text


def _extract_response_text(payload: Any) -> str | None:
    """Probe the response payload for a known field; return None if none hit."""
    if not isinstance(payload, dict):
        return None
    for field in _RESPONSE_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value:
            return value
    return None


__all__ = ["HTTPBlackboxAdapter"]
