"""Settings loader unit tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from pydantic import SecretStr, ValidationError

from phoenix_audit_agent.config import JUDGE_LLM_LOCKED, Settings, get_settings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Strip every PHOENIX_* / GEMINI_* / etc. var + point env_file at an empty tmp file.

    Without this, the test would inherit Abu's actual `.env` (with real PHOENIX_API_KEY etc.),
    making 'defaults load' tests non-deterministic.
    """
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
        if key in {"ENVIRONMENT", "SERVICE_VERSION"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)  # ensure pydantic-settings doesn't pick up repo-root .env
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_load_with_minimum_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-017 default mode: only GEMINI_API_KEY is required; phoenix_api_key is optional."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    s = Settings()
    assert s.phoenix_provider == "phoenix-audit"
    assert s.phoenix_api_key is None
    assert s.phoenix_collector_endpoint == "http://localhost:6006/v1/traces"
    assert s.judge_llm == JUDGE_LLM_LOCKED
    assert s.environment == "dev"


def test_judge_llm_validator_rejects_non_flash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("JUDGE_LLM", "gemini-3.1-pro-preview")
    with pytest.raises(ValidationError) as exc:
        Settings()
    assert "judge_llm" in str(exc.value)
    assert JUDGE_LLM_LOCKED in str(exc.value)


def test_phoenix_api_key_is_secretstr_when_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    """Per docs/architecture.md hard rule + Patch #20 schema rule 4a:
    api_key MUST be SecretStr-redacted."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_API_KEY", "sk-real-secret-key-do-not-leak")
    s = Settings()
    assert isinstance(s.phoenix_api_key, SecretStr)
    # repr() MUST redact the key.
    assert "sk-real-secret-key-do-not-leak" not in repr(s)
    assert "sk-real-secret-key-do-not-leak" not in repr(s.phoenix_api_key)
    # get_secret_value() unwraps for actual use.
    assert s.phoenix_api_key.get_secret_value() == "sk-real-secret-key-do-not-leak"


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    a = get_settings()
    b = get_settings()
    assert a is b  # lru_cache returns the same instance


def test_env_override_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("TARGET_DEFAULT_URL", "http://target.example:9999")
    monkeypatch.setenv("ENVIRONMENT", "prod")
    s = Settings()
    assert s.target_default_url == "http://target.example:9999"
    assert s.environment == "prod"


def test_missing_gemini_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env -> ValidationError because gemini_api_key has no default."""
    with pytest.raises(ValidationError):
        Settings()


def test_byo_mode_requires_phoenix_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-017 hybrid: phoenix_provider == 'customer' MUST come with phoenix_api_key."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_PROVIDER", "customer")
    # Intentionally omit PHOENIX_API_KEY.
    with pytest.raises(ValidationError) as exc:
        Settings()
    assert "phoenix_api_key" in str(exc.value)
    assert "customer" in str(exc.value).lower() or "BYO" in str(exc.value)


def test_byo_mode_with_key_loads_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_PROVIDER", "customer")
    monkeypatch.setenv("PHOENIX_API_KEY", "byo-key")
    s = Settings()
    assert s.phoenix_provider == "customer"
    assert s.phoenix_api_key is not None
    assert s.phoenix_api_key.get_secret_value() == "byo-key"


def test_invalid_phoenix_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_PROVIDER", "self-hosted")  # not in the Literal set
    with pytest.raises(ValidationError):
        Settings()


def test_default_mode_with_api_key_warns(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """PHOENIX_API_KEY set under default mode is a misconfig — must warn loudly."""
    import logging

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_API_KEY", "accidental-byo-key")
    # phoenix_provider left at default ("phoenix-audit")
    with caplog.at_level(logging.WARNING, logger="phoenix_audit_agent.config"):
        s = Settings()
    assert s.phoenix_provider == "phoenix-audit"
    assert any(
        "phoenix_api_key" in r.message and "ignored" in r.message.lower() for r in caplog.records
    ), [r.message for r in caplog.records]
