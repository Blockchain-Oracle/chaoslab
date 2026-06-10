"""Tier 1 ADK adapter — drives an ADK target via the A2A protocol.

Implements the ``TargetAdapter`` ABC against ``a2a-sdk``'s ``ClientFactory``.
The target side is an ADK agent exposed via ``to_a2a()`` (story 2.2) which
serves its AgentCard at ``/.well-known/agent-card.json``.

Spec deviation: story-3.2 specifies ``from google.adk.agents import RemoteA2aAgent``,
but that symbol is not shipped in our pinned ``google-adk>=2.1.0,<3.0.0``. The
actual client lives in ``a2a-sdk`` (transitively pulled by ``google-adk[a2a]``).
See ``docs/audit-notes.md`` IF-10 — and note that ``a2a-sdk`` 0.3.x exposes both
``a2a.client.ClientFactory`` (modern, used here) and ``a2a.client.legacy.A2AClient``
(same-version deprecated — do NOT use).

ADK quarantine note: ``a2a`` is a separate top-level distribution, not a
submodule of ``google.adk``. The ``google.adk.*`` quarantine rule (CLAUDE.md)
therefore does NOT cover ``a2a.*``; this module imports from ``a2a.client``
and ``a2a.types`` directly.

Failure convention (per the frozen ``AdapterResult`` contract — base.py:79-97):
adapters MUST raise on transport / protocol / framework errors. The
``error`` field is reserved for Epic 5+ soft-failure semantics (a fault
deliberately caused the target to misbehave while the transport completed).
Today, S3.2 only RAISES; ``AdapterResult.error`` is always ``None``.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any

import httpx
from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientEvent,
    ClientFactory,
    create_text_message_object,
)
from a2a.client.client import Client
from a2a.client.errors import A2AClientError, A2AClientHTTPError, A2AClientJSONError
from a2a.types import Message, Role, Task, TextPart, TransportProtocol
from opentelemetry import trace

from phoenix_audit_agent.errors import AdapterConnectionError, AdapterDiscoveryError
from phoenix_audit_agent.injector.target_adapters.base import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

_WELL_KNOWN_AGENT_CARD = "/.well-known/agent-card.json"
_HTTP_NOT_FOUND = 404
_TRACER = trace.get_tracer(__name__)


def _bearer_headers(spec: TargetSpec) -> dict[str, str] | None:
    """Build an Authorization header dict from spec.auth, or None if absent.

    Delegates to the shared helper in `_common.py` so ADK + Tier-2 adapters
    have one consistent auth shape (and one consistent raise on a wrong-
    key auth dict — round-2 review SFH-B2). Returns None on empty so the
    existing ADK call sites keep their `or {}` fallback.
    """
    from phoenix_audit_agent.injector.target_adapters._common import bearer_headers

    headers = bearer_headers(spec)
    return headers or None


def _extract_text_from_message(message: Message) -> str:
    """Concatenate every TextPart in the message; ignore non-text parts."""
    return "".join(p.root.text for p in message.parts if isinstance(p.root, TextPart))


def _extract_text_from_task(task: Task) -> str:
    """Pull text from a Task: prefer status.message, else agent messages in history.

    ``task.history`` includes the original user prompt. Echoing it back would be
    wrong, so the fallback filters to ``Role.agent`` only. Returns "" if the task
    carried no agent text — caller treats that as an empty response, not an error.
    """
    if task.status.message is not None:
        return _extract_text_from_message(task.status.message)
    if not task.history:
        return ""
    agent_messages = [m for m in task.history if m.role is Role.agent]
    return "".join(_extract_text_from_message(m) for m in agent_messages)


async def _safe_aclose(client: httpx.AsyncClient | None) -> None:
    """Close an httpx client without letting its own errors mask the cause.

    httpx.aclose() can raise on already-closed transports or network-teardown
    races. We must run it on every error path of connect(), but if it raises
    the secondary exception unwinds before we get to wrap the original failure.
    Swallow + log instead so the caller sees the real error.
    """
    if client is None:
        return
    # Suppress is intentional: we're in an error-recovery path and any
    # secondary aclose() failure (already-closed transport, teardown race)
    # would mask the original A2A/transport error the caller needs to see.
    with contextlib.suppress(Exception):
        await client.aclose()


class ADKAdapter(TargetAdapter):
    """Tier 1 adapter: drives an ADK target exposed via ``to_a2a()``."""

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._agent_card: dict[str, Any] | None = None
        self._client: Client | None = None
        self._http: httpx.AsyncClient | None = None
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        headers = _bearer_headers(self.spec) or {}
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s, headers=headers)
        resolver = A2ACardResolver(
            httpx_client=self._http,
            base_url=base,
            agent_card_path=_WELL_KNOWN_AGENT_CARD,
        )
        try:
            card = await resolver.get_agent_card()
        except A2AClientHTTPError as e:
            # A2ACardResolver wraps every httpx.RequestError as
            # A2AClientHTTPError(status_code=503) too — so connect-refused /
            # DNS failure / ELOOP all surface here, not as raw httpx.* below.
            http, self._http = self._http, None
            await _safe_aclose(http)
            if e.status_code == _HTTP_NOT_FOUND:
                raise AdapterDiscoveryError(
                    f"no AgentCard at {base}{_WELL_KNOWN_AGENT_CARD}"
                ) from e
            raise AdapterConnectionError(f"failed to reach {base}: HTTP {e.status_code}") from e
        except A2AClientJSONError as e:
            http, self._http = self._http, None
            await _safe_aclose(http)
            raise AdapterDiscoveryError(
                f"malformed AgentCard at {base}{_WELL_KNOWN_AGENT_CARD}"
            ) from e
        self._agent_card = card.model_dump(mode="json", by_alias=True)
        # streaming=False asks send_message to yield aggregated terminal events
        # (a bare Message for synchronous replies, or a ClientEvent carrying a
        # terminal Task — see `_text_from_event`). supported_transports is
        # restricted to JSONRPC because that's what `to_a2a()` advertises today.
        factory = ClientFactory(
            ClientConfig(
                httpx_client=self._http,
                streaming=False,
                supported_transports=[TransportProtocol.jsonrpc],
            )
        )
        self._client = factory.create(card)
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        # Real guard (not assert) — `python -O` strips asserts in production.
        if self._client is None:
            raise AdapterConnectionError("ADKAdapter.invoke called without an active client")

        start = time.perf_counter()
        span_ids: list[str] = []

        with _TRACER.start_as_current_span("phoenix-audit.adapter.adk.invoke") as span:
            span_ids.append(format(span.get_span_context().span_id, "016x"))
            message = create_text_message_object(content=invocation.prompt)
            if invocation.session_id is not None:
                message.context_id = invocation.session_id
            try:
                # With streaming=False the iterator yields ONE terminal event;
                # we still iterate to drain it but only keep the last emitted
                # text (defends against a future SDK quirk emitting partials).
                response_text = ""
                async for event in self._client.send_message(message):
                    response_text = _text_from_event(event)
            except A2AClientError as e:
                # round-2: record_and_raise sets StatusCode.ERROR on the span
                # so Phoenix doesn't show "OK" with a recorded exception inside.
                from phoenix_audit_agent.injector.target_adapters._common import record_and_raise

                record_and_raise(span, e)
                raise AdapterConnectionError(
                    f"A2A protocol error from {self.spec.url}: {type(e).__name__}"
                ) from e
            except httpx.HTTPError as e:
                from phoenix_audit_agent.injector.target_adapters._common import record_and_raise

                record_and_raise(span, e)
                raise AdapterConnectionError(
                    f"transport error to {self.spec.url}: {type(e).__name__}"
                ) from e

        duration_ms = (time.perf_counter() - start) * 1000.0
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=duration_ms,
            error=None,
            metadata={"agent_card_name": (self._agent_card or {}).get("name")},
        )

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        return AdapterFingerprint(
            tier=AdapterTier.TIER1_ADK,
            framework="google-adk",
            agent_card=self._agent_card,
            discovery_path="agent_card",
        )

    async def disconnect(self) -> None:
        http, self._http = self._http, None
        await _safe_aclose(http)
        self._client = None
        self._agent_card = None
        self._connected = False


def _text_from_event(event: ClientEvent | Message) -> str:
    """Pull display text from one streamed event.

    The ``Client.send_message`` async iterator yields either:
    - a bare ``Message`` (synchronous reply, no task lifecycle), or
    - a ``ClientEvent`` tuple ``(Task, update | None)`` where the update is
      an artifact / status delta. For ``streaming=False`` the task carries
      the terminal state and the update is typically ``None``.

    Non-text parts (files, structured data) are out of scope for Tier 1.
    """
    if isinstance(event, Message):
        return _extract_text_from_message(event)
    task, _update = event
    return _extract_text_from_task(task)
