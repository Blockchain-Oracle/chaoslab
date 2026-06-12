"""SSRF guard for operator-supplied target URLs (`api._url_guard`).

The auditor invokes whatever URL the operator submits — without a guard,
anyone reaching the API can aim it at the GCP metadata server or
link-local/loopback services. Metadata + link-local are blocked
unconditionally; loopback is allowed only in dev or with
ALLOW_LOCAL_TARGETS=true (local demo target runs on localhost:8001).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from phoenix_audit_agent.api._url_guard import validate_target_url
from phoenix_audit_agent.config import get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    prefixes = ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "ALLOW_")
    for key in list(os.environ):
        if key.startswith(prefixes):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_public_https_url_passes_unchanged() -> None:
    url = "https://target-agent-abc.a.run.app/invoke"
    assert validate_target_url(url) == url


@pytest.mark.parametrize(
    "bad",
    [
        "not-a-url",
        "ftp://example.com/agent",
        "file:///etc/passwd",
        "http://",
        "",
    ],
)
def test_malformed_or_non_http_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match=r"(?i)url|input"):
        validate_target_url(bad)


@pytest.mark.parametrize(
    "blocked",
    [
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://METADATA.GOOGLE.INTERNAL/",
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.0.1:8080/",
    ],
)
def test_metadata_and_link_local_blocked_even_in_dev(blocked: str) -> None:
    # environment defaults to dev — these are NEVER legitimate audit targets.
    with pytest.raises(ValueError, match=r"metadata|link-local"):
        validate_target_url(blocked)


@pytest.mark.parametrize("local", ["http://localhost:8001", "http://127.0.0.1:8001"])
def test_loopback_allowed_in_dev(local: str) -> None:
    assert validate_target_url(local) == local


@pytest.mark.parametrize(
    "local", ["http://localhost:8001", "http://127.0.0.1:8001", "http://[::1]:8001"]
)
def test_loopback_blocked_in_prod(local: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="loopback"):
        validate_target_url(local)


def test_allow_local_targets_overrides_prod_loopback_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("ALLOW_LOCAL_TARGETS", "true")
    get_settings.cache_clear()
    assert validate_target_url("http://localhost:8001") == "http://localhost:8001"


def test_metadata_blocked_even_with_allow_local_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_LOCAL_TARGETS", "true")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="metadata"):
        validate_target_url("http://metadata.google.internal/")


@pytest.mark.parametrize(
    "blocked",
    [
        # RFC1918 private ranges — auditor must never pivot into the VPC.
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://172.16.0.10/",
        # IPv6 ULA + 0.0.0.0 + reserved + multicast.
        "http://[fd00::1]/",
        "http://0.0.0.0/",
        "http://224.0.0.1/",
        "http://[ff00::1]/",
    ],
)
def test_private_and_reserved_addresses_blocked_unconditionally(blocked: str) -> None:
    """Security-review HIGH: the SSRF guard must reject RFC1918 + IPv6 ULA +
    0.0.0.0 + multicast/reserved unconditionally, in any environment, so a
    user-supplied target_url can't be aimed at internal infrastructure."""
    with pytest.raises(ValueError, match=r"private|reserved"):
        validate_target_url(blocked)


def test_userinfo_in_target_url_rejected() -> None:
    """Security-review low: embedded basic-auth credentials would otherwise
    land in Cloud Logging via the validate_endpoint_invoked structured log."""
    with pytest.raises(ValueError, match="credentials"):
        validate_target_url("https://user:pass@target.example/")
