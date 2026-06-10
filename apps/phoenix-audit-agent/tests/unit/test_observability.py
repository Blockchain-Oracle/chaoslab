"""Tests for `phoenix_audit_agent.observability` — structlog config + Phoenix register."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import pytest
import structlog
from opentelemetry import trace as _otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from phoenix_audit_agent.config import get_settings


@pytest.fixture(autouse=True)
def _reset_obs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Reset structlog + observability module state between tests."""
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
        if key in {"ENVIRONMENT", "SERVICE_VERSION"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_API_KEY", "test-phoenix-key-DO-NOT-LEAK")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()

    # Reset structlog config + the module's idempotency flag.
    from phoenix_audit_agent import observability as _obs

    _obs._STATE["logging_configured"] = False
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()
    get_settings.cache_clear()


# --- setup_logging ----------------------------------------------------------


def test_setup_logging_production_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    get_logger().info("test_event", foo="bar")

    output = capsys.readouterr().out.strip()
    assert output, "no log line captured"
    parsed = json.loads(output.splitlines()[-1])
    assert parsed["event"] == "test_event"
    assert parsed["foo"] == "bar"
    assert parsed["level"] == "info"


def test_setup_logging_prod_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    """`env="prod"` is what main.py actually passes (Environment Literal) —
    it must select the JSON renderer, not the dev console renderer."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="prod")
    get_logger().info("prod_event", foo="bar")

    output = capsys.readouterr().out.strip()
    assert output, "no log line captured"
    parsed = json.loads(output.splitlines()[-1])
    assert parsed["event"] == "prod_event"


def test_setup_logging_configures_stdlib_root_logger() -> None:
    """~17 modules use stdlib `logging.getLogger`; without a configured root
    logger their INFO lines (gitlab_mr_emitted, sse_client_disconnect, ...)
    are dropped by the lastResort handler in production."""
    import logging

    from phoenix_audit_agent.observability import setup_logging

    root = logging.getLogger()
    before_handlers = list(root.handlers)
    before_level = root.level
    try:
        for h in before_handlers:
            root.removeHandler(h)
        root.setLevel(logging.WARNING)
        setup_logging(env="prod")
        assert root.handlers, "setup_logging must attach a root stdlib handler"
        assert root.getEffectiveLevel() <= logging.INFO
        # End-to-end: an actual stdlib INFO line must reach the handler — the
        # original bug was INFO vanishing via the lastResort handler.
        import io

        capture = io.StringIO()
        probe_handler = logging.StreamHandler(capture)
        root.addHandler(probe_handler)
        logging.getLogger("phoenix_audit_agent.obs_probe").info("stdlib_info_visible")
        assert "stdlib_info_visible" in capture.getvalue()
    finally:
        for h in list(root.handlers):
            root.removeHandler(h)
        for h in before_handlers:
            root.addHandler(h)
        root.setLevel(before_level)


def test_setup_logging_dev_uses_console_renderer(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`env != 'production'` uses ConsoleRenderer (NOT JSON)."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="dev")
    get_logger().info("dev_event", k="v")
    output = capsys.readouterr().out
    assert "dev_event" in output
    # Console renderer output is not valid JSON.
    with pytest.raises(json.JSONDecodeError):
        json.loads(output.splitlines()[-1])


def test_setup_logging_is_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    """Second call to setup_logging is a no-op (no double-processing)."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    setup_logging(env="production")
    get_logger().info("once_only")
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(lines) == 1, lines


def test_setup_logging_filters_below_info(capsys: pytest.CaptureFixture[str]) -> None:
    """INFO+ filter — debug() produces nothing."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    get_logger().debug("invisible")
    assert capsys.readouterr().out.strip() == ""


def test_logged_messages_never_contain_phoenix_api_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Privacy check — even if a developer logs `settings`, the key must not leak."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    s = get_settings()
    get_logger().info("settings_repr", settings_repr=repr(s))
    output = capsys.readouterr().out
    assert "test-phoenix-key-DO-NOT-LEAK" not in output


def test_get_logger_with_name_records_logger_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Named loggers keep their name in the bound state."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    log = get_logger("phoenix_audit_agent.test")
    log.info("named")
    parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert parsed["event"] == "named"


# --- Phoenix trace_id processor ---------------------------------------------


def test_log_inside_otel_span_includes_trace_id_and_span_id(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """When called inside an active OTel span, the JSON carries trace_id + span_id."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    # Bypass the "tracer provider can only be set once" guard with monkeypatch.
    monkeypatch.setattr(_otel_trace, "_TRACER_PROVIDER", provider)
    monkeypatch.setattr(_otel_trace, "_TRACER_PROVIDER_SET_ONCE", lambda: None)

    setup_logging(env="production")
    tracer = _otel_trace.get_tracer("phoenix-audit.test")

    with tracer.start_as_current_span("test_span"):
        get_logger().info("inside_span")
    parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert parsed["event"] == "inside_span"
    assert "trace_id" in parsed, parsed
    assert len(parsed["trace_id"]) == 32, parsed["trace_id"]
    assert all(c in "0123456789abcdef" for c in parsed["trace_id"])
    assert "span_id" in parsed
    assert len(parsed["span_id"]) == 16


def test_log_outside_span_has_no_trace_id(capsys: pytest.CaptureFixture[str]) -> None:
    """When no span is recording, the processor adds nothing — log lines stay clean."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    get_logger().info("outside_span")
    parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "trace_id" not in parsed, parsed
    assert "span_id" not in parsed


def test_phoenix_trace_id_processor_is_idempotent() -> None:
    """Calling `_add_phoenix_trace_id` twice doesn't duplicate keys."""
    from phoenix_audit_agent.observability import _add_phoenix_trace_id

    event_dict = {"event": "test"}
    out_a = _add_phoenix_trace_id(None, "info", event_dict)
    out_b = _add_phoenix_trace_id(None, "info", out_a)
    # Outside a span both calls are no-ops; outputs identical.
    assert out_a == out_b


# --- setup_phoenix_otel -----------------------------------------------------


def test_setup_phoenix_otel_registers_instrumentor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`setup_phoenix_otel` calls register() AND installs the GoogleADKInstrumentor."""
    from phoenix_audit_agent import observability as _obs

    captured: dict = {"register_called": False, "instrumented": False}

    def fake_register(**kwargs):
        captured["register_called"] = True
        captured["register_kwargs"] = kwargs

    class FakeInstrumentor:
        def instrument(self) -> None:
            captured["instrumented"] = True

    # Patch the local-imports inside setup_phoenix_otel.
    monkeypatch.setattr("phoenix.otel.register", fake_register)
    monkeypatch.setattr(
        "openinference.instrumentation.google_adk.GoogleADKInstrumentor",
        FakeInstrumentor,
    )

    _obs.setup_phoenix_otel(get_settings())
    assert captured["register_called"]
    assert captured["instrumented"]
    assert captured["register_kwargs"]["project_name"] == "phoenix-audit"
    assert captured["register_kwargs"]["api_key"] == "test-phoenix-key-DO-NOT-LEAK"


def test_setup_phoenix_otel_propagates_register_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any error inside register() must bubble — no silent observability loss."""
    from phoenix_audit_agent import observability as _obs

    def boom(**_kwargs):
        raise RuntimeError("phoenix unreachable")

    monkeypatch.setattr("phoenix.otel.register", boom)
    with pytest.raises(RuntimeError, match=r"phoenix unreachable"):
        _obs.setup_phoenix_otel(get_settings())


def test_setup_phoenix_otel_fails_fast_before_mutating_tracer_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If openinference is missing, ImportError surfaces BEFORE Phoenix mutates global tracer state.

    Round-2 silent-failure-hunter CRITICAL: a half-installed "Phoenix tracer
    registered, ADK NOT instrumented" state silently fails open. Solution is
    to resolve both imports BEFORE register() is called.
    """
    from phoenix_audit_agent import observability as _obs

    register_called = {"yes": False}

    def fake_register(**_kwargs):
        register_called["yes"] = True

    # phoenix.otel.register patched to a benign fake — but the instrumentor
    # import is patched to raise. Should surface ImportError WITHOUT register()
    # ever being called.
    monkeypatch.setattr("phoenix.otel.register", fake_register)

    import sys

    monkeypatch.setitem(sys.modules, "openinference.instrumentation.google_adk", None)
    with pytest.raises(ImportError, match=r"openinference-instrumentation-google-adk"):
        _obs.setup_phoenix_otel(get_settings())
    assert not register_called["yes"], (
        "register() ran despite instrumentor import failing — tracer state half-installed"
    )


def test_setup_phoenix_otel_actionable_error_when_phoenix_otel_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing `phoenix.otel` surfaces with install instructions, not a raw ModuleNotFoundError."""
    import sys

    from phoenix_audit_agent import observability as _obs

    monkeypatch.setitem(sys.modules, "phoenix.otel", None)
    with pytest.raises(ImportError, match=r"arize-phoenix-otel"):
        _obs.setup_phoenix_otel(get_settings())


def test_setup_logging_raises_on_env_change(capsys: pytest.CaptureFixture[str]) -> None:
    """Second call with a DIFFERENT env value raises — silent reconfigure is a foot-gun."""
    from phoenix_audit_agent.observability import setup_logging

    setup_logging(env="production")
    with pytest.raises(RuntimeError, match=r"already configured"):
        setup_logging(env="dev")


def test_kwargs_with_secret_named_key_are_masked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Foot-gun defense: `log.info(..., api_key=get_secret_value())` must not leak the key."""
    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    get_logger().info(
        "phoenix_call",
        api_key="test-phoenix-key-DO-NOT-LEAK",
        authorization="Bearer test-phoenix-key-DO-NOT-LEAK",
        token="test-phoenix-key-DO-NOT-LEAK",
    )
    parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert parsed["api_key"] == "***", parsed
    assert parsed["authorization"] == "***", parsed
    assert parsed["token"] == "***", parsed
    assert "test-phoenix-key-DO-NOT-LEAK" not in json.dumps(parsed)


def test_kwargs_with_secretstr_value_are_masked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A SecretStr value bound to ANY kwarg name is replaced with '***'."""
    from pydantic import SecretStr

    from phoenix_audit_agent.observability import get_logger, setup_logging

    setup_logging(env="production")
    get_logger().info("phoenix_call", some_field=SecretStr("leaky"))
    parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert parsed["some_field"] == "***"
    assert "leaky" not in json.dumps(parsed)


def test_phoenix_trace_id_processor_with_invalid_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a span exists but its context is INVALID (e.g., NonRecordingSpan), no trace_id."""
    from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, set_span_in_context

    from phoenix_audit_agent.observability import _add_phoenix_trace_id

    # Build a span context with is_remote=False but ALL-ZEROS trace_id => is_valid=False.
    invalid_ctx = SpanContext(trace_id=0, span_id=0, is_remote=False, trace_flags=TraceFlags(0))
    invalid_span = NonRecordingSpan(invalid_ctx)
    token = _otel_trace.context_api.attach(set_span_in_context(invalid_span))
    try:
        ed = _add_phoenix_trace_id(None, "info", {"event": "test"})
    finally:
        _otel_trace.context_api.detach(token)
    assert "trace_id" not in ed
    assert "span_id" not in ed
