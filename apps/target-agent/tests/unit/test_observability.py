"""Unit tests for target_agent.observability.

Tests the credential-resolution path WITHOUT calling Phoenix Cloud or Secret
Manager for real. Secret Manager is stubbed via monkeypatch under the §14
carve-out (test-side stubs are explicitly exempt from the no-mocks-in-hot-path
rule).

End-to-end "spans actually land in Phoenix" verification lives in the
@pytest.mark.online integration test next door.
"""

from __future__ import annotations

import pytest
import structlog
from opentelemetry.sdk.trace import TracerProvider

from target_agent.observability import (
    ConfigurationError,
    DegradedTracerProvider,
    _resolve_api_key,
    _should_fail_loud,
    setup_observability,
)


@pytest.fixture(autouse=True)
def _clear_phoenix_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a clean env so resolution order is deterministic.

    ADC unset is a defensive guard: if a test forgets to monkey-patch
    `SecretManagerServiceClient`, the underlying GCP client will fail loudly
    instead of silently authenticating against the developer's real GCP
    account.
    """
    for var in (
        "PHOENIX_API_KEY",
        "PHOENIX_COLLECTOR_ENDPOINT",
        "PHOENIX_PROJECT_NAME",
        "GCP_PROJECT_ID",
        "K_SERVICE",
        "PHOENIX_OBSERVABILITY_OPTIONAL",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(var, raising=False)


def test_resolve_api_key_uses_env_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOENIX_API_KEY", "px-from-env")
    assert _resolve_api_key() == "px-from-env"


def test_resolve_api_key_raises_when_neither_env_nor_gcp_project_set() -> None:
    with pytest.raises(ConfigurationError, match="GCP_PROJECT_ID also unset"):
        _resolve_api_key()


def test_resolve_api_key_falls_back_to_secret_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """When env is unset but GCP_PROJECT_ID is, Secret Manager is queried.

    Test stub increments a call counter so a silent monkeypatch failure (which
    would otherwise let _resolve_api_key hit real GCP) fails the test loudly.
    """
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    class _FakePayload:
        data = b"px-from-secret-manager"

    class _FakeResponse:
        payload = _FakePayload()

    # §14 carve-out: test-side stub of google.cloud.secretmanager
    class _FakeSecretManagerClient:
        call_count = 0

        def access_secret_version(self, name: str) -> _FakeResponse:
            del name
            type(self).call_count += 1
            return _FakeResponse()

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub of google.cloud.secretmanager
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeSecretManagerClient)
    assert _resolve_api_key() == "px-from-secret-manager"
    assert _FakeSecretManagerClient.call_count == 1, (
        "stub was bypassed — likely hit real GCP Secret Manager"
    )


def test_resolve_api_key_raises_when_secret_manager_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    class _FakeEmptyPayload:
        data = b""

    class _FakeResponse:
        payload = _FakeEmptyPayload()

    # §14 carve-out: test-side stub of google.cloud.secretmanager
    class _FakeSecretManagerClient:
        def access_secret_version(self, name: str) -> _FakeResponse:
            del name
            return _FakeResponse()

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub of google.cloud.secretmanager
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeSecretManagerClient)
    with pytest.raises(ConfigurationError, match="empty payload"):
        _resolve_api_key()


def test_resolve_api_key_translates_secret_manager_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NotFound from GCP API maps to an operator-actionable ConfigurationError."""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    from google.api_core import exceptions as gcp_exc

    # §14 carve-out: test-side stub raising the documented GCP exception type
    class _FakeNotFoundClient:
        def access_secret_version(self, name: str) -> object:
            raise gcp_exc.NotFound(f"Secret {name} not found")

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeNotFoundClient)
    with pytest.raises(ConfigurationError, match="gcloud secrets create"):
        _resolve_api_key()


def test_resolve_api_key_translates_secret_manager_permission_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PermissionDenied gives the operator the exact IAM role they need to grant."""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    from google.api_core import exceptions as gcp_exc

    # §14 carve-out: test-side stub raising the documented GCP exception type
    class _FakeDeniedClient:
        def access_secret_version(self, name: str) -> object:
            del name
            raise gcp_exc.PermissionDenied("nope")

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeDeniedClient)
    with pytest.raises(ConfigurationError, match=r"roles/secretmanager\.secretAccessor"):
        _resolve_api_key()


def test_resolve_api_key_translates_secret_manager_unauthenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unauthenticated points the operator at Workload Identity Federation."""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    from google.api_core import exceptions as gcp_exc

    # §14 carve-out: test-side stub raising Unauthenticated
    class _FakeUnauthClient:
        def access_secret_version(self, name: str) -> object:
            del name
            raise gcp_exc.Unauthenticated("token rejected")

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeUnauthClient)
    with pytest.raises(ConfigurationError, match="Workload Identity"):
        _resolve_api_key()


def test_resolve_api_key_translates_default_credentials_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DefaultCredentialsError (raised at client construction) maps the same way.

    Catches the F-1 finding: previously this exception bypassed the narrowed
    catches because the client constructor was outside the try-block AND
    DefaultCredentialsError is NOT a subclass of GoogleAPIError.
    """
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    from google.auth import exceptions as gcp_auth_exc

    # §14 carve-out: test-side stub whose CONSTRUCTOR raises (mimics ADC failure)
    class _FakeADCBrokenClient:
        def __init__(self) -> None:
            raise gcp_auth_exc.DefaultCredentialsError(
                "could not automatically determine credentials"
            )

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeADCBrokenClient)
    with pytest.raises(ConfigurationError, match="Workload Identity"):
        _resolve_api_key()


def test_resolve_api_key_translates_generic_google_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any other GoogleAPIError falls into the broad catch with structured logging."""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    from google.api_core import exceptions as gcp_exc

    # §14 carve-out: test-side stub raising a generic transport-layer error
    class _FakeDeadlineClient:
        def access_secret_version(self, name: str) -> object:
            del name
            raise gcp_exc.DeadlineExceeded("rpc deadline")

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeDeadlineClient)
    with pytest.raises(ConfigurationError, match="Secret Manager API error"):
        _resolve_api_key()


def test_setup_observability_default_collector_endpoint_constant() -> None:
    """The default endpoint constant IS the canonical Phoenix Cloud URL.

    Verified by inspecting source rather than calling register() — running
    register() during unit tests installs Phoenix as the OTel global, which
    OTel allows-with-warning but poisons the conftest-based S2.1 tool-span
    tests in the same session. The integration test against real Phoenix
    in test_phoenix_instrumentation.py exercises the live path.
    """
    import pathlib

    src = pathlib.Path(__file__).parent.parent.parent / "src" / "target_agent" / "observability.py"
    contents = src.read_text()
    assert '_DEFAULT_COLLECTOR_ENDPOINT = "https://app.phoenix.arize.com"' in contents, (
        "default Phoenix collector endpoint constant must be the canonical URL"
    )


def test_setup_observability_uses_cloud_run_default_flags() -> None:
    """register() must use Cloud Run defaults per architecture/02 §3.5.

    Source-shape check: the register() call must NOT pass
    set_global_tracer_provider=False or batch=False (those are Agent Engine
    flags; Cloud Run uses the defaults). Previous code did the wrong thing
    and had to manually re-install the global as a workaround — the tidy-up
    PR removed both anti-patterns. See audit-notes D4-8.
    """
    import pathlib

    src = pathlib.Path(__file__).parent.parent.parent / "src" / "target_agent" / "observability.py"
    contents = src.read_text()
    assert "set_global_tracer_provider=False" not in contents, (
        "must not pass set_global_tracer_provider=False on Cloud Run — see audit-notes D4-8"
    )
    assert "batch=False" not in contents, (
        "must not pass batch=False on Cloud Run — see audit-notes D4-8"
    )


def test_setup_observability_degrades_in_local_dev_without_credentials() -> None:
    """No credentials + not Cloud Run → DegradedTracerProvider sentinel."""
    provider = setup_observability(project_name="unit-test-noop")
    assert isinstance(provider, DegradedTracerProvider), (
        f"expected DegradedTracerProvider sentinel, got {type(provider)}"
    )


def test_setup_observability_fails_loud_on_cloud_run_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud Run (K_SERVICE set) + no creds → raise + log fail-loud event.

    Asserts BOTH that ConfigurationError is raised AND that the fail-loud
    branch specifically fired (not just _resolve_api_key's independent
    raise). Without the log assertion, this test could pass even if
    _should_fail_loud() were dead code (G1 finding from test-analyzer).
    """
    monkeypatch.setenv("K_SERVICE", "target-agent")
    with structlog.testing.capture_logs() as captured, pytest.raises(ConfigurationError):
        setup_observability(project_name="unit-test-cloud-run")
    # G1: the fail-loud branch emits this specific event with env="cloud_run".
    # If _should_fail_loud() returns False (broken), the warning event fires
    # instead, and this assertion catches the regression.
    fail_loud_events = [
        e for e in captured if e.get("event") == "phoenix_observability_required_but_missing"
    ]
    assert len(fail_loud_events) == 1, (
        f"fail-loud branch did not fire as expected; logs were: {captured}"
    )
    assert fail_loud_events[0].get("env") == "cloud_run"


def test_setup_observability_allows_opt_in_to_no_op_on_cloud_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even on Cloud Run, PHOENIX_OBSERVABILITY_OPTIONAL=1 opts back into no-op."""
    monkeypatch.setenv("K_SERVICE", "target-agent")
    monkeypatch.setenv("PHOENIX_OBSERVABILITY_OPTIONAL", "1")
    provider = setup_observability(project_name="unit-test-cloud-run-optional")
    assert isinstance(provider, DegradedTracerProvider)


def test_setup_observability_emits_disabled_log_when_degrading() -> None:
    """The graceful-degradation path emits a discoverable structlog event."""
    with structlog.testing.capture_logs() as captured:
        setup_observability(project_name="unit-test-log-check")
    events = [e for e in captured if e.get("event") == "phoenix_observability_disabled"]
    assert len(events) == 1, f"expected phoenix_observability_disabled log, got: {captured}"


def test_should_fail_loud_returns_true_only_on_cloud_run_without_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Behavioral coverage of the env-var gating logic itself.

    Splits the 4-state truth table into one matrix-style assertion. If this
    drifts, every other Cloud-Run-vs-local-dev test in the file silently
    re-interprets its environment.
    """
    # Local dev, no opt-in → degrade
    assert _should_fail_loud() is False

    # Local dev with opt-in → also degrade (opt-in doesn't matter off Cloud Run)
    monkeypatch.setenv("PHOENIX_OBSERVABILITY_OPTIONAL", "1")
    assert _should_fail_loud() is False
    monkeypatch.delenv("PHOENIX_OBSERVABILITY_OPTIONAL")

    # Cloud Run, no opt-in → fail loud
    monkeypatch.setenv("K_SERVICE", "target-agent")
    assert _should_fail_loud() is True

    # Cloud Run with opt-in → degrade (opt-in wins)
    monkeypatch.setenv("PHOENIX_OBSERVABILITY_OPTIONAL", "1")
    assert _should_fail_loud() is False


def test_degraded_tracer_provider_delegates_force_flush() -> None:
    """G2: DegradedTracerProvider must transparently delegate TracerProvider API.

    The sentinel wraps a real TracerProvider and proxies via __getattr__.
    If the proxy breaks (recursion, missing _inner), production code that
    calls force_flush() on the sentinel during graceful shutdown crashes
    silently. Verify the three load-bearing methods delegate correctly.
    """
    inner = TracerProvider()
    sentinel = DegradedTracerProvider(inner)

    # force_flush — used during demo / shutdown
    assert sentinel.force_flush(timeout_millis=100) is True

    # get_tracer — used by tools.py at module load
    tracer = sentinel.get_tracer("test-module")
    assert tracer is not None

    # add_span_processor — used by some test fixtures + future code
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    # Should not raise
    sentinel.add_span_processor(SimpleSpanProcessor(exporter))


def test_resolve_api_key_translates_grpc_rpc_error_by_type_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F-2 transport-error catch: gRPC channel-shutdown races surface as
    `RpcError` / `_InactiveRpcError` (type-name match because `grpc` is
    only a transitive dep). Synthesize an exception with that type name.
    """
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    # Synthesize an exception class whose type-name matches the grpc one.
    # Real grpc.RpcError is non-trivial to instantiate; type-name match
    # is what observability.py uses so we test it directly.
    class RpcError(Exception):
        pass

    # §14 carve-out: test-side stub raising a fake transport error
    class _FakeRpcErrorClient:
        def access_secret_version(self, name: str) -> object:
            del name
            raise RpcError("channel reset mid-call")

    import google.cloud.secretmanager as sm

    # §14 carve-out: test-side stub
    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeRpcErrorClient)
    with pytest.raises(ConfigurationError, match="transport error"):
        _resolve_api_key()


def _install_no_op_phoenix_stubs(monkeypatch: pytest.MonkeyPatch) -> TracerProvider:
    """Replace phoenix.otel.register + GoogleADKInstrumentor with no-op stubs.

    Without this, calling setup_observability() during unit tests causes
    register() to install Phoenix as the global tracer provider AND attach
    a real Phoenix exporter — both of which poison the conftest-managed
    in-memory exporter that S2.1 tool tests depend on. Returns the stub
    TracerProvider that register() will yield, so the test can compare
    against `_otel_trace.get_tracer_provider()` results.
    """
    stub_provider = TracerProvider()

    # §14 carve-out: test-side stub of phoenix.otel.register
    import phoenix.otel as phx_otel

    def _stub_register(**_kw: object) -> TracerProvider:
        return stub_provider

    # §14 carve-out: test-side stub
    monkeypatch.setattr(phx_otel, "register", _stub_register)

    # §14 carve-out: test-side stub of GoogleADKInstrumentor so it doesn't
    # actually monkey-patch ADK during these tests.
    import openinference.instrumentation.google_adk as adk_instr

    class _StubInstrumentor:
        def instrument(self, **_kw: object) -> None:
            pass

    # §14 carve-out: test-side stub
    monkeypatch.setattr(adk_instr, "GoogleADKInstrumentor", _StubInstrumentor)

    return stub_provider


def test_setup_observability_raises_on_cloud_run_when_global_provider_was_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Behavioral coverage for the runtime check + Cloud Run fail-loud escalation.

    Simulates OTel's "set-once" silent no-op by making
    `opentelemetry.trace.get_tracer_provider()` return a sentinel that is
    NOT the one register() returned. On Cloud Run this should raise
    ConfigurationError (the H1 fail-loud pattern).

    Covers Gap #1 (test-analyzer's HIGH finding): the defensive runtime
    check would otherwise have no behavioral coverage.
    """
    monkeypatch.setenv("PHOENIX_API_KEY", "px-unit-dummy")
    monkeypatch.setenv("K_SERVICE", "target-agent")
    _install_no_op_phoenix_stubs(monkeypatch)

    # §14 carve-out: make get_tracer_provider return a DIFFERENT provider
    # than the one register() returned, simulating the set-once silent no-op
    sentinel_global = TracerProvider()
    import opentelemetry.trace as ot

    # §14 carve-out: test-side stub
    monkeypatch.setattr(ot, "get_tracer_provider", lambda: sentinel_global)

    with (
        structlog.testing.capture_logs() as captured,
        pytest.raises(ConfigurationError, match="NOT installed as the OTel"),
    ):
        setup_observability(project_name="unit-test-runtime-check-raise")

    raise_events = [
        e
        for e in captured
        if e.get("event") == "phoenix_global_tracer_provider_not_installed_cloud_run"
    ]
    assert len(raise_events) == 1, f"expected fail-loud log event before raise; got: {captured}"
    assert raise_events[0].get("env") == "cloud_run"


def test_setup_observability_logs_warning_on_local_dev_when_global_provider_was_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counterpart to the Cloud Run raise test: on local dev (no K_SERVICE),
    the runtime check logs a warning but does NOT raise.
    """
    monkeypatch.setenv("PHOENIX_API_KEY", "px-unit-dummy")
    # Deliberately NOT setting K_SERVICE — this is the local-dev path.
    _install_no_op_phoenix_stubs(monkeypatch)

    sentinel_global = TracerProvider()
    import opentelemetry.trace as ot

    # §14 carve-out: test-side stub
    monkeypatch.setattr(ot, "get_tracer_provider", lambda: sentinel_global)

    with structlog.testing.capture_logs() as captured:
        # Should NOT raise on local dev
        setup_observability(project_name="unit-test-runtime-check-warn")

    warn_events = [
        e for e in captured if e.get("event") == "phoenix_global_tracer_provider_not_installed"
    ]
    assert len(warn_events) == 1, f"expected local-dev warning log event; got: {captured}"


def test_setup_observability_installs_global_tracer_provider_code_shape() -> None:
    """Regression guard for the empirical bug test-analyzer Gap #1 caught.

    With Option A (Cloud Run defaults), `set_global_tracer_provider=True` is
    the default behavior — register() installs Phoenix globally automatically.
    The manual `trace.set_tracer_provider()` workaround that existed during
    the pre-tidy-up code is REMOVED here; this test guards that the
    architectural fix sticks (no resurrection of the workaround means no
    return of the underlying bug it was patching).
    """
    import pathlib

    src = pathlib.Path(__file__).parent.parent.parent / "src" / "target_agent" / "observability.py"
    contents = src.read_text()
    # Cloud Run defaults are the right path. The explicit set_tracer_provider
    # WORKAROUND should NOT be reintroduced (its presence implied the wrong
    # flags above it).
    assert "set_tracer_provider(tracer_provider)" not in contents, (
        "manual trace.set_tracer_provider workaround should not exist with "
        "Cloud Run defaults — see audit-notes D4-8"
    )
