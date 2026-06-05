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

from target_agent.observability import (
    ConfigurationError,
    DegradedTracerProvider,
    _resolve_api_key,
    setup_observability,
)


@pytest.fixture(autouse=True)
def _clear_phoenix_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a clean env so resolution order is deterministic.

    Also asserts no real GCP credentials are exposed to the process — protects
    against the test stub silently leaking to real Secret Manager if monkeypatch
    were ever to fail. ADC is unset to force the GCP client to fail loudly
    rather than authenticate transparently.
    """
    for var in (
        "PHOENIX_API_KEY",
        "PHOENIX_COLLECTOR_ENDPOINT",
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
            del name  # unused — test only verifies fallback path
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


def test_setup_observability_default_collector_endpoint_constant() -> None:
    """The default endpoint constant IS the canonical Phoenix Cloud URL.

    Verified by inspecting source rather than calling register() — running
    register() during unit tests installs Phoenix as the OTel global, which
    OTel allows-with-warning but then poisons the conftest-based S2.1 tool
    span tests in the same session. The integration test against real
    Phoenix in test_phoenix_instrumentation.py exercises the live path.
    """
    import pathlib

    src = pathlib.Path(__file__).parent.parent.parent / "src" / "target_agent" / "observability.py"
    contents = src.read_text()
    assert '_DEFAULT_COLLECTOR_ENDPOINT = "https://app.phoenix.arize.com"' in contents, (
        "default Phoenix collector endpoint constant must be the canonical URL"
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
    """Cloud Run (K_SERVICE set) + no creds → raise; do NOT degrade silently."""
    monkeypatch.setenv("K_SERVICE", "target-agent")  # Cloud Run sets this
    with pytest.raises(ConfigurationError):
        setup_observability(project_name="unit-test-cloud-run")


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


def test_setup_observability_installs_global_tracer_provider_code_shape() -> None:
    """Regression check for the bug Reviewer #1 (test-analyzer) caught.

    setup_observability() MUST call trace.set_tracer_provider(tracer_provider)
    after register() — otherwise tools.py's module-level `_tracer` binds to
    the no-op default and spans never reach Phoenix. The behavioral check
    lives in the integration test (which actually runs against Phoenix
    Cloud); this unit-level check guards the source-shape so a refactor
    that drops the call fails fast in CI without needing live credentials.

    Why not behavioral here: register() during unit tests installs Phoenix
    as the OTel global despite the "set-once" warning, which then poisons
    the conftest-managed S2.1 tool-span tests in the same session.
    """
    import pathlib

    src = pathlib.Path(__file__).parent.parent.parent / "src" / "target_agent" / "observability.py"
    assert "set_tracer_provider(tracer_provider)" in src.read_text(), (
        "observability.py must call trace.set_tracer_provider(tracer_provider) "
        "after register() — see audit-notes D4-8."
    )
