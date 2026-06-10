"""S-EC2: the /hooks/adk fault surface — Phoenix Audit's remote fault delivery.

The deployed auditor cannot install ADK callbacks in-process; it POSTs a
fault descriptor here and this module installs the equivalent callback on
`root_agent` for the duration of one registration. Gated by
FAULT_HOOKS_ENABLED — a target that hasn't opted in returns 404 (the
auditor's webhook session treats that as hooks-unavailable, never silent).
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from starlette.applications import Starlette
from starlette.testclient import TestClient

from target_agent import fault_hooks
from target_agent.fault_hooks import build_hook_routes


@pytest.fixture
def agent() -> LlmAgent:
    return LlmAgent(
        name="hook_test_agent",
        model="gemini-3.5-flash",
        description="hook test fixture",
        instruction="test",
        tools=[],
    )


@pytest.fixture
def client(agent: LlmAgent, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FAULT_HOOKS_ENABLED", "true")
    app = Starlette(routes=build_hook_routes(agent))
    return TestClient(app)


def _register(client: TestClient, config: dict[str, Any]) -> str:
    resp = client.post("/hooks/adk", json={"fault_config": config})
    assert resp.status_code == 200, resp.text
    rid = resp.json()["registration_id"]
    assert isinstance(rid, str)
    assert rid
    return rid


class TestGating:
    def test_disabled_by_default_returns_404(self, agent: LlmAgent) -> None:
        app = Starlette(routes=build_hook_routes(agent))
        resp = TestClient(app).post(
            "/hooks/adk", json={"fault_config": {"kind": "latency_spike", "delay_ms": 1}}
        )
        assert resp.status_code == 404

    def test_disabled_delete_also_404(self, agent: LlmAgent) -> None:
        app = Starlette(routes=build_hook_routes(agent))
        assert TestClient(app).delete("/hooks/adk/whatever").status_code == 404


class TestRegistrationLifecycle:
    def test_register_installs_tool_callback_and_delete_removes(
        self, client: TestClient, agent: LlmAgent
    ) -> None:
        rid = _register(
            client,
            {
                "kind": "malformed_tool_output",
                "mode": "type_mismatch",
                "rate": 1.0,
                "target_tool_name": None,
                "payload": {"status": 200, "items": "three widgets", "total": "ten"},
            },
        )
        assert agent.before_tool_callback is not None
        resp = client.delete(f"/hooks/adk/{rid}")
        assert resp.status_code == 200
        assert agent.before_tool_callback is None

    def test_register_prompt_injection_installs_model_callback(
        self, client: TestClient, agent: LlmAgent
    ) -> None:
        rid = _register(
            client,
            {"kind": "prompt_injection", "attack": "role_hijacking", "payload": "EVIL"},
        )
        assert agent.before_model_callback is not None
        client.delete(f"/hooks/adk/{rid}")
        assert agent.before_model_callback is None

    def test_second_registration_conflicts_409(self, client: TestClient) -> None:
        _register(client, {"kind": "latency_spike", "delay_ms": 1, "timeout_ms": 100})
        resp = client.post(
            "/hooks/adk",
            json={"fault_config": {"kind": "latency_spike", "delay_ms": 2, "timeout_ms": 100}},
        )
        assert resp.status_code == 409

    def test_delete_unknown_registration_404(self, client: TestClient) -> None:
        assert client.delete("/hooks/adk/nope").status_code == 404

    def test_unknown_kind_rejected_422(self, client: TestClient, agent: LlmAgent) -> None:
        resp = client.post("/hooks/adk", json={"fault_config": {"kind": "meteor_strike"}})
        assert resp.status_code == 422
        assert agent.before_tool_callback is None

    def test_missing_fault_config_rejected_422(self, client: TestClient) -> None:
        assert client.post("/hooks/adk", json={}).status_code == 422


class TestExecutorBehavior:
    async def test_tool_callback_returns_descriptor_payload_and_marks_span(
        self, agent: LlmAgent, in_memory_spans: Any
    ) -> None:
        payload = {"status": "shipped", "items": [{"name": "widget", "qty": 2}]}
        cb = fault_hooks.build_callback(
            {
                "kind": "malformed_tool_output",
                "mode": "missing_required_field",
                "rate": 1.0,
                "target_tool_name": None,
                "payload": payload,
            }
        )
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)

        class _Tool:
            name = "lookup_order"

        with tracer.start_as_current_span("tool"):
            result = await cb.before_tool(_Tool(), {}, None)
        assert result == payload
        attrs = in_memory_spans.get_finished_spans()[0].attributes
        assert attrs["phoenix_audit.fault.type"] == "malformed_tool_output"
        assert attrs["phoenix_audit.fault.mode"] == "missing_required_field"

    async def test_exception_mode_raises(self, agent: LlmAgent, in_memory_spans: Any) -> None:
        cb = fault_hooks.build_callback(
            {
                "kind": "malformed_tool_output",
                "mode": "exception",
                "rate": 1.0,
                "target_tool_name": None,
                "payload": None,
            }
        )
        from opentelemetry import trace

        class _Tool:
            name = "anything"

        with (
            trace.get_tracer(__name__).start_as_current_span("tool"),
            pytest.raises(RuntimeError, match="injected"),
        ):
            await cb.before_tool(_Tool(), {}, None)

    async def test_model_callback_appends_payload_to_last_user_message(
        self, agent: LlmAgent, in_memory_spans: Any
    ) -> None:
        from google.genai.types import Content, Part

        cb = fault_hooks.build_callback(
            {"kind": "prompt_injection", "attack": "instruction_override", "payload": " INJ"}
        )

        class _Req:
            contents = [Content(role="user", parts=[Part(text="hello")])]  # noqa: RUF012

        from opentelemetry import trace

        with trace.get_tracer(__name__).start_as_current_span("llm"):
            await cb.before_model(None, _Req())
        assert _Req.contents[-1].parts[-1].text == "hello INJ"  # ty: ignore[not-subscriptable]
        attrs = in_memory_spans.get_finished_spans()[0].attributes
        assert attrs["phoenix_audit.fault.type"] == "prompt_injection"
        assert attrs["phoenix_audit.fault.injected"] is True

    async def test_retriever_insert_patches_retrieval_tool_and_restores(
        self, in_memory_spans: Any
    ) -> None:
        from google.adk.tools.retrieval import BaseRetrievalTool

        class _KB(BaseRetrievalTool):
            def __init__(self) -> None:
                super().__init__(name="search_kb", description="kb")

            async def run_async(self, *, args: Any, tool_context: Any) -> Any:
                return ["real-doc"]

        kb = _KB()
        agent = LlmAgent(
            name="kb_agent",
            model="gemini-3.5-flash",
            description="d",
            instruction="i",
            tools=[kb],
        )
        state = fault_hooks.HookState(agent)
        rid = await state.register(
            {
                "kind": "context_poisoning",
                "mode": "retriever_insert",
                "target_retriever_name": None,
                "payload": "[POISON-DOC]",
            }
        )
        from opentelemetry import trace

        with trace.get_tracer(__name__).start_as_current_span("retrieval"):
            docs = await kb.run_async(args={}, tool_context=None)
        assert docs == ["[POISON-DOC]", "real-doc"]
        attrs = in_memory_spans.get_finished_spans()[0].attributes
        assert attrs["phoenix_audit.fault.type"] == "context_poisoning"
        assert attrs["phoenix_audit.fault.injected"] is True

        await state.unregister(rid)
        docs_after = await kb.run_async(args={}, tool_context=None)
        assert docs_after == ["real-doc"], "uninstall must restore the original run_async"

    async def test_retriever_insert_without_retrieval_tool_rejected(self) -> None:
        agent = LlmAgent(
            name="bare", model="gemini-3.5-flash", description="d", instruction="i", tools=[]
        )
        state = fault_hooks.HookState(agent)
        with pytest.raises(ValueError, match="no BaseRetrievalTool"):
            await state.register(
                {
                    "kind": "context_poisoning",
                    "mode": "retriever_insert",
                    "target_retriever_name": None,
                    "payload": "[POISON]",
                }
            )

    async def test_context_poisoning_history_insert_prepends(self, agent: LlmAgent) -> None:
        from google.genai.types import Content, Part

        cb = fault_hooks.build_callback(
            {
                "kind": "context_poisoning",
                "mode": "history_insert",
                "target_retriever_name": None,
                "payload": "[POISON]",
            }
        )

        class _Req:
            contents = [Content(role="user", parts=[Part(text="hi")])]  # noqa: RUF012

        from opentelemetry import trace

        with trace.get_tracer(__name__).start_as_current_span("llm"):
            await cb.before_model(None, _Req())
        assert _Req.contents[0].parts[0].text == "[POISON]"  # ty: ignore[not-subscriptable]

    async def test_latency_spike_sleeps_and_marks_span(
        self, agent: LlmAgent, in_memory_spans: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slept: list[float] = []

        async def fake_sleep(s: float) -> None:
            slept.append(s)

        monkeypatch.setattr(fault_hooks.asyncio, "sleep", fake_sleep)
        cb = fault_hooks.build_callback(
            {"kind": "latency_spike", "delay_ms": 250, "timeout_ms": 5000}
        )

        class _Tool:
            name = "lookup_order"

        from opentelemetry import trace

        with trace.get_tracer(__name__).start_as_current_span("tool"):
            result = await cb.before_tool(_Tool(), {}, None)
        assert result is None  # latency fault never short-circuits the tool
        assert slept == [0.25]
        attrs = in_memory_spans.get_finished_spans()[0].attributes
        assert attrs["phoenix_audit.fault.type"] == "latency_spike"
