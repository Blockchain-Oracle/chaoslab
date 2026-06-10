"""Remote fault-delivery hook surface for Phoenix Audit (the /hooks/adk routes).

Phoenix Audit's Injector runs in a different Cloud Run service and cannot
install ADK callbacks on this process directly. It POSTs a fault descriptor
(built by `phoenix_audit_agent.injector.faults.descriptors`) and this module
installs the equivalent callback on the live agent for ONE registration:

    POST   /hooks/adk          {"fault_config": {...}} -> {"registration_id"}
    DELETE /hooks/adk/{id}     tears the fault down, restoring prior callbacks

Contract notes:
- Gated by FAULT_HOOKS_ENABLED=true (checked per request — flipping the env
  var on Cloud Run takes effect without code changes). Disabled -> 404, which
  the auditor's webhook session reports as hooks-unavailable, never silent.
- Exactly ONE active registration: concurrent audits would race the shared
  callback slots, so the second registrant gets 409.
- Registrations auto-expire after TTL_SECONDS — an auditor that crashed
  before DELETE must not leave a fault installed on the demo target forever.
- The descriptor carries the resolved payload; this executor applies it
  mechanically and writes the same `phoenix_audit.fault.*` span attributes
  the auditor's in-process fault classes write (cross-app contract test:
  apps/phoenix-audit-agent/tests/unit/judge/test_fault_attr_contract.py).
"""

from __future__ import annotations

import asyncio
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

TTL_SECONDS = 120.0
_KNOWN_KINDS = frozenset(
    {"malformed_tool_output", "prompt_injection", "context_poisoning", "latency_spike"}
)


def _enabled() -> bool:
    return os.environ.get("FAULT_HOOKS_ENABLED", "").lower() == "true"


@dataclass
class FaultCallbacks:
    """Executor callbacks built from one fault descriptor."""

    config: dict[str, Any]
    before_tool: Any = None
    before_model: Any = None


def _tool_matches(config: dict[str, Any], tool: Any) -> bool:
    wanted = config.get("target_tool_name")
    return wanted is None or getattr(tool, "name", None) == wanted


def _rate_fires(config: dict[str, Any]) -> bool:
    rate = float(config.get("rate", 1.0))
    return rate >= 1.0 or secrets.randbelow(1_000_000) / 1_000_000 < rate


def _build_malformed_tool(config: dict[str, Any]) -> FaultCallbacks:
    async def before_tool(tool: Any, args: dict[str, Any], tool_context: Any) -> Any:
        if not _tool_matches(config, tool) or not _rate_fires(config):
            return None
        span = trace.get_current_span()
        span.set_attribute("phoenix_audit.fault.type", "malformed_tool_output")
        span.set_attribute("phoenix_audit.fault.mode", str(config.get("mode")))
        if config.get("mode") != "exception":
            return config.get("payload")
        exc = RuntimeError("F1: injected malformed tool output (mode=exception)")
        span.set_status(trace.Status(trace.StatusCode.ERROR, "F1 fault injected"))
        span.record_exception(exc)
        raise exc

    return FaultCallbacks(config=config, before_tool=before_tool)


def _append_to_last_user_message(llm_request: Any, payload: str) -> bool:
    from google.genai.types import Part

    contents = llm_request.contents or []
    for msg in reversed(contents):
        if getattr(msg, "role", None) == "user" and msg.parts:
            p = msg.parts[-1]
            if getattr(p, "text", None) is not None:
                p.text = (p.text or "") + payload
            else:
                msg.parts.append(Part(text=payload))
            return True
    return False


def _build_prompt_injection(config: dict[str, Any]) -> FaultCallbacks:
    async def before_model(callback_context: Any, llm_request: Any) -> None:
        span = trace.get_current_span()
        span.set_attribute("phoenix_audit.fault.type", "prompt_injection")
        span.set_attribute("phoenix_audit.fault.attack", str(config.get("attack")))
        injected = _append_to_last_user_message(llm_request, str(config.get("payload", "")))
        # injected=False tells the Judge the attack never landed — without it
        # the .type/.attack attrs would lie about an attack that didn't run.
        span.set_attribute("phoenix_audit.fault.injected", injected)

    return FaultCallbacks(config=config, before_model=before_model)


def _build_context_poisoning(config: dict[str, Any]) -> FaultCallbacks:
    async def before_model(callback_context: Any, llm_request: Any) -> None:
        from google.genai.types import Content, Part

        span = trace.get_current_span()
        span.set_attribute("phoenix_audit.fault.type", "context_poisoning")
        span.set_attribute("phoenix_audit.fault.mode", str(config.get("mode")))
        if llm_request.contents is None:
            llm_request.contents = []
        llm_request.contents.insert(
            0, Content(role="user", parts=[Part(text=str(config.get("payload", "")))])
        )
        span.set_attribute("phoenix_audit.fault.injected", True)

    return FaultCallbacks(config=config, before_model=before_model)


def _build_latency_spike(config: dict[str, Any]) -> FaultCallbacks:
    async def before_tool(tool: Any, args: dict[str, Any], tool_context: Any) -> Any:
        span = trace.get_current_span()
        span.set_attribute("phoenix_audit.fault.type", "latency_spike")
        span.set_attribute("phoenix_audit.fault.delay_ms", int(config.get("delay_ms", 0)))
        await asyncio.sleep(float(config.get("delay_ms", 0)) / 1000.0)
        return None  # never short-circuits the real tool

    return FaultCallbacks(config=config, before_tool=before_tool)


def build_callback(config: dict[str, Any]) -> FaultCallbacks:
    """Build executor callbacks for one descriptor; raises ValueError on unknown kind."""
    kind = config.get("kind")
    if kind == "malformed_tool_output":
        return _build_malformed_tool(config)
    if kind == "prompt_injection":
        return _build_prompt_injection(config)
    if kind == "context_poisoning":
        mode = config.get("mode")
        if mode == "history_insert":
            return _build_context_poisoning(config)
        if mode == "retriever_insert":
            # Installation is tool-level, not callback-level — handled by
            # HookState.register so originals can be saved for restore.
            return FaultCallbacks(config=config)
        msg = f"unknown context_poisoning mode {mode!r}"
        raise ValueError(msg)
    if kind == "latency_spike":
        return _build_latency_spike(config)
    msg = f"unknown fault kind {kind!r}; expected one of {sorted(_KNOWN_KINDS)}"
    raise ValueError(msg)


def _make_poisoned_run_async(original: Any, poison: str) -> Any:
    async def patched(*, args: dict[str, Any], tool_context: Any) -> Any:
        result = await original(args=args, tool_context=tool_context)
        span = trace.get_current_span()
        span.set_attribute("phoenix_audit.fault.type", "context_poisoning")
        span.set_attribute("phoenix_audit.fault.mode", "retriever_insert")
        if isinstance(result, list):
            result.insert(0, poison)
            span.set_attribute("phoenix_audit.fault.injected", True)
            return result
        if isinstance(result, str):
            span.set_attribute("phoenix_audit.fault.injected", True)
            return poison + "\n\n" + result
        span.set_attribute("phoenix_audit.fault.injected", False)
        span.set_attribute(
            "phoenix_audit.fault.skipped_reason", f"unsupported_type:{type(result).__name__}"
        )
        msg = (
            f"retriever_insert: retriever returned unsupported type "
            f"{type(result).__name__!r}; expected list or str"
        )
        raise RuntimeError(msg)

    return patched


@dataclass
class _Registration:
    registration_id: str
    callbacks: FaultCallbacks
    saved_tool_cb: Any
    saved_model_cb: Any
    patched_tools: list[tuple[Any, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)

    @property
    def expired(self) -> bool:
        return time.monotonic() - self.created_at > TTL_SECONDS


class HookState:
    """Single-slot registration store guarding the agent's callback surface."""

    def __init__(self, agent: Any) -> None:
        self._agent = agent
        self._lock = asyncio.Lock()
        self._active: _Registration | None = None
        self._inflight = 0

    def _track(self, fn: Any) -> Any:
        """Count in-flight callback executions — TTL eviction must never swap
        the callback slot while a previous probe's invocation is still running
        (the slow probe would execute the NEXT probe's fault and stamp the
        wrong evidence onto its spans)."""

        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            self._inflight += 1
            try:
                return await fn(*args, **kwargs)
            finally:
                self._inflight -= 1

        return wrapped

    def _patch_retrieval_tools(self, reg: _Registration, config: dict[str, Any]) -> None:
        from google.adk.tools.retrieval import BaseRetrievalTool

        wanted = config.get("target_retriever_name")
        poison = str(config.get("payload", ""))
        for tool in getattr(self._agent, "tools", []):
            if not isinstance(tool, BaseRetrievalTool):
                continue
            if wanted and getattr(tool, "name", None) != wanted:
                continue
            original = tool.run_async
            tool.run_async = self._track(_make_poisoned_run_async(original, poison))
            reg.patched_tools.append((tool, original))
        if not reg.patched_tools:
            msg = (
                "context_poisoning(retriever_insert): no BaseRetrievalTool matched "
                f"on this agent (target_retriever_name={wanted!r})"
            )
            raise ValueError(msg)

    def _install(self, callbacks: FaultCallbacks) -> _Registration:
        reg = _Registration(
            registration_id=secrets.token_hex(8),
            callbacks=callbacks,
            saved_tool_cb=self._agent.before_tool_callback,
            saved_model_cb=self._agent.before_model_callback,
        )
        if callbacks.config.get("mode") == "retriever_insert":
            self._patch_retrieval_tools(reg, callbacks.config)
        if callbacks.before_tool is not None:
            self._agent.before_tool_callback = self._track(callbacks.before_tool)
        if callbacks.before_model is not None:
            self._agent.before_model_callback = self._track(callbacks.before_model)
        return reg

    def _uninstall(self, reg: _Registration) -> None:
        self._agent.before_tool_callback = reg.saved_tool_cb
        self._agent.before_model_callback = reg.saved_model_cb
        for tool, original in reg.patched_tools:
            tool.run_async = original

    async def register(self, config: dict[str, Any]) -> str:
        callbacks = build_callback(config)  # ValueError propagates -> 422
        async with self._lock:
            # TTL eviction recovers from an auditor that crashed before its
            # DELETE — but only when no callback execution is in flight.
            if self._active is not None and self._active.expired and self._inflight == 0:
                self._uninstall(self._active)
                self._active = None
            if self._active is not None:
                msg = "a fault registration is already active"
                raise RuntimeError(msg)
            self._active = self._install(callbacks)
            return self._active.registration_id

    async def unregister(self, registration_id: str) -> bool:
        async with self._lock:
            if self._active is None or self._active.registration_id != registration_id:
                return False
            self._uninstall(self._active)
            self._active = None
            return True


def build_hook_routes(agent: Any) -> list[Route]:
    """Starlette routes for the hook surface, bound to ONE agent instance."""
    state = HookState(agent)

    async def post_hook(request: Request) -> JSONResponse:
        if not _enabled():
            return JSONResponse({"detail": "fault hooks disabled"}, status_code=404)
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({"detail": "body must be JSON"}, status_code=422)
        config = body.get("fault_config") if isinstance(body, dict) else None
        if not isinstance(config, dict):
            return JSONResponse({"detail": "fault_config object required"}, status_code=422)
        try:
            registration_id = await state.register(config)
        except ValueError as err:
            return JSONResponse({"detail": str(err)}, status_code=422)
        except RuntimeError as err:
            return JSONResponse({"detail": str(err)}, status_code=409)
        return JSONResponse({"registration_id": registration_id})

    async def delete_hook(request: Request) -> JSONResponse:
        if not _enabled():
            return JSONResponse({"detail": "fault hooks disabled"}, status_code=404)
        removed = await state.unregister(request.path_params["registration_id"])
        if not removed:
            return JSONResponse({"detail": "unknown registration"}, status_code=404)
        return JSONResponse({"status": "removed"})

    return [
        Route("/hooks/adk", post_hook, methods=["POST"]),
        Route("/hooks/adk/{registration_id}", delete_hook, methods=["DELETE"]),
    ]


__all__ = ["FaultCallbacks", "HookState", "build_callback", "build_hook_routes"]
