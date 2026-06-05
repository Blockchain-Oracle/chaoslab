"""Unit tests for target_agent.observability.

Tests the credential-resolution path WITHOUT calling Phoenix Cloud or Secret
Manager for real — both are stubbed via monkeypatch under the §14 carve-out
(test-side stubs are explicitly exempt from the no-mocks-in-hot-path rule).

The actual end-to-end "spans land in Phoenix" verification lives in the
@pytest.mark.online integration test next door.
"""

from __future__ import annotations

import os

import pytest

from target_agent.observability import (
    ConfigurationError,
    _resolve_api_key,
    setup_observability,
)


@pytest.fixture(autouse=True)
def _clear_phoenix_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a clean Phoenix env so resolution order is deterministic."""
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)


def test_resolve_api_key_uses_env_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOENIX_API_KEY", "px-from-env")
    assert _resolve_api_key() == "px-from-env"


def test_resolve_api_key_raises_when_neither_env_nor_gcp_project_set() -> None:
    with pytest.raises(ConfigurationError, match="GCP_PROJECT_ID also unset"):
        _resolve_api_key()


def test_resolve_api_key_falls_back_to_secret_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """When env is unset but GCP_PROJECT_ID is, Secret Manager is queried.

    §14 carve-out: test-side stub of google.cloud.secretmanager — required to
    exercise the fallback path without hitting real GCP from a unit test.
    """
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    class _FakePayload:
        data = b"px-from-secret-manager"

    class _FakeResponse:
        payload = _FakePayload()

    class _FakeSecretManagerClient:
        def access_secret_version(self, name: str) -> _FakeResponse:
            del name  # unused — test only verifies fallback path
            return _FakeResponse()

    import google.cloud.secretmanager as sm

    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeSecretManagerClient)
    assert _resolve_api_key() == "px-from-secret-manager"


def test_resolve_api_key_raises_when_secret_manager_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project-123")

    class _FakeEmptyPayload:
        data = b""

    class _FakeResponse:
        payload = _FakeEmptyPayload()

    class _FakeSecretManagerClient:
        def access_secret_version(self, name: str) -> _FakeResponse:
            del name  # unused — test only verifies fallback path
            return _FakeResponse()

    import google.cloud.secretmanager as sm

    monkeypatch.setattr(sm, "SecretManagerServiceClient", _FakeSecretManagerClient)
    with pytest.raises(ConfigurationError, match="empty payload"):
        _resolve_api_key()


def test_setup_observability_returns_tracer_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end smoke: setup_observability returns a TracerProvider.

    Uses a never-bound localhost endpoint — OTel will queue spans on send
    failures but won't error during register().
    """
    monkeypatch.setenv("PHOENIX_API_KEY", "px-unit-dummy")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://127.0.0.1:1")

    from opentelemetry.sdk.trace import TracerProvider

    provider = setup_observability(project_name="unit-test-project")
    assert provider is not None
    assert isinstance(provider, TracerProvider), f"unexpected type: {type(provider)}"


def test_setup_observability_sets_default_endpoint_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If PHOENIX_COLLECTOR_ENDPOINT is unset, setup populates it from the default."""
    monkeypatch.setenv("PHOENIX_API_KEY", "px-unit-dummy")
    # Deliberately do NOT set PHOENIX_COLLECTOR_ENDPOINT.

    setup_observability(project_name="unit-test-default-endpoint")
    # After setup, env var should be set to the default.
    assert os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") == "https://app.phoenix.arize.com"


def test_setup_observability_degrades_gracefully_without_credentials() -> None:
    """No credentials anywhere → no-op TracerProvider, no exception.

    Matches the S2.2 contract that the server still starts in local dev
    without Phoenix credentials. Production Cloud Run hits the real path
    via Secret Manager and never lands here.
    """
    # autouse _clear_phoenix_env fixture already wiped PHOENIX_API_KEY +
    # GCP_PROJECT_ID, so _resolve_api_key() will raise ConfigurationError
    # and setup_observability() must swallow it.
    from opentelemetry.sdk.trace import TracerProvider

    provider = setup_observability(project_name="unit-test-noop")
    assert isinstance(provider, TracerProvider), f"unexpected type: {type(provider)}"
