"""Tier 1 ADK adapter — drives an ADK target via the A2A protocol.

Implements the ``TargetAdapter`` ABC against ``a2a-sdk``'s ``ClientFactory``.
The target side is an ADK agent exposed via ``to_a2a()`` (story 2.2) which
serves its AgentCard at ``/.well-known/agent-card.json``.

Spec deviation: story-3.2 specifies ``from google.adk.agents import RemoteA2aAgent``,
but that symbol is not shipped in our pinned ``google-adk>=2.1.0,<3.0.0``. The
actual client lives in ``a2a-sdk`` (transitively pulled by ``google-adk[a2a]``).
See docs/audit-notes.md IF-10.

ADK quarantine note: ``a2a.*`` is NOT under the ``google.adk.*`` quarantine rule
(CLAUDE.md). This module imports from ``a2a.client`` and ``a2a.types`` directly.
"""

from __future__ import annotations

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
from a2a.client.errors import A2AClientHTTPError, A2AClientJSONError
from a2a.types import Message, Task, TextPart, TransportProtocol
from opentelemetry import trace

from chaoslab_agent.errors import AdapterConnectionError, AdapterDiscoveryError
from chaoslab_agent.injector.target_adapters.base import (
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
    """Build an Authorization header dict from spec.auth, or None if absent."""
    if spec.auth is None or "bearer" not in spec.auth:
        return None
    return {"Authorization": f"Bearer {spec.auth['bearer'].get_secret_value()}"}


def _extract_text_from_message(message: Message) -> str:
    """Concatenate every TextPart in the message; ignore non-text parts."""
    return "".join(p.root.text for p in message.parts if isinstance(p.root, TextPart))


def _extract_text_from_task(task: Task) -> str:
    """Pull text from a Task: prefer status.message, fall back to history."""
    if task.status.message is not None:
        return _extract_text_from_message(task.status.message)
    if task.history:
        return "".join(_extract_text_from_message(m) for m in task.history)
    return ""


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
            await self._http.aclose()
            self._http = None
            if e.status_code == _HTTP_NOT_FOUND:
                raise AdapterDiscoveryError(
                    f"no AgentCard at {base}{_WELL_KNOWN_AGENT_CARD}"
                ) from e
            raise AdapterConnectionError(f"failed to reach {base}: HTTP {e.status_code}") from e
        except A2AClientJSONError as e:
            await self._http.aclose()
            self._http = None
            raise AdapterDiscoveryError(
                f"malformed AgentCard at {base}{_WELL_KNOWN_AGENT_CARD}"
            ) from e
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            await self._http.aclose()
            self._http = None
            raise AdapterConnectionError(f"failed to reach {base}: {type(e).__name__}") from e
        self._agent_card = card.model_dump(mode="json", by_alias=True)
        # ClientFactory + the resolved card → a transport-negotiated Client.
        # `streaming=False` makes send_message yield aggregated terminal events
        # rather than partial Task updates; the JSONRPC transport is the only
        # one our target advertises, but listing it explicitly is forward-safe.
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
        assert self._client is not None

        start = time.perf_counter()
        span_ids: list[str] = []
        response_text = ""
        error: str | None = None

        with _TRACER.start_as_current_span("chaoslab.adapter.adk.invoke") as span:
            span_ids.append(format(span.get_span_context().span_id, "016x"))
            message = create_text_message_object(content=invocation.prompt)
            if invocation.session_id is not None:
                message.context_id = invocation.session_id
            try:
                parts: list[str] = []
                async for event in self._client.send_message(message):
                    parts.append(_text_from_event(event))
                response_text = "".join(parts)
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                span.record_exception(e)

        duration_ms = (time.perf_counter() - start) * 1000.0
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=duration_ms,
            error=error,
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
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._client = None
        self._agent_card = None
        self._connected = False


def _text_from_event(event: ClientEvent | Message) -> str:
    """Pull display text from one streamed event.

    The ``Client.send_message`` async iterator yields either:
    - a bare ``Message`` (synchronous reply, no task lifecycle), or
    - a ``ClientEvent`` tuple ``(Task, update | None)`` where the update is
      an artifact / status delta — for ``streaming=False`` the task already
      carries the terminal state and the update is typically ``None``.

    We extract conversational text from whichever shape arrives; non-text
    parts (files, structured data) are out of scope for Tier 1.
    """
    if isinstance(event, Message):
        return _extract_text_from_message(event)
    task, _update = event
    return _extract_text_from_task(task)
