"""Unit tests for POST /validate — preflight A2A card validation endpoint.

The wizard at `/new` calls this when the user pastes a target URL so they
get a verdict ("✓ AIScan — A2A v0.3.0 · 6 skills · no auth" / "⚠ pre-v1 /
basic audit" / "✗ reason") in milliseconds — instead of finding out after
a 90s full audit fails.

Auth follows the same `require_user` pattern every other /api/agent/*
route uses; SSRF protection reuses the existing `_url_guard`.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import respx


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset env vars so `get_settings()` picks up a deterministic config."""
    from phoenix_audit_agent.config import get_settings

    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "FIREBASE_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as: Any) -> None:
    """This module's subject is /validate, not auth — requests arrive
    pre-authenticated. Auth wiring is covered by test_auth_scoping."""


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _v1_card_payload(name: str = "test-agent", url: str = "https://x.example") -> dict[str, Any]:
    """Minimal A2A v1.0-conformant card shape."""
    return {
        "name": name,
        "description": "A test agent.",
        "url": url,
        "version": "1.0.0",
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {"id": "echo", "name": "echo", "description": "Echo input.", "tags": ["test"]},
        ],
    }


@respx.mock
async def test_validate_returns_valid_v1_for_aiscan_shape(
    client: httpx.AsyncClient,
) -> None:
    """Happy path — strict v1.0 card → JSON shape the wizard can render."""
    respx.get("https://target.example/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_v1_card_payload(name="AIScan"))
    )
    resp = await client.post("/validate", json={"target_url": "https://target.example"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is True
    assert body["mode"] == "v1"
    assert body["name"] == "AIScan"
    assert body["protocol_version"] == "0.3.0"
    assert body["skills_count"] == 1
    assert body["auth"] == "none"
    assert body["discovery_path"] == "/.well-known/agent-card.json"
    assert body["warnings"] == []


@respx.mock
async def test_validate_returns_permissive_with_warning_for_pre_v1(
    client: httpx.AsyncClient,
) -> None:
    """Pre-v1 / Codelabs `methods`-shape card → mode=permissive + warning so
    the wizard shows an amber state ("basic audit only")."""
    pre_v1 = {
        "name": "Global Weather Agent",
        "description": "Real-time weather information.",
        "url": "https://target.example",
        "version": "1.0.0",
        "capabilities": {"streaming": True},
        "methods": [{"name": "message/send"}],
    }
    respx.get("https://target.example/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=pre_v1)
    )
    resp = await client.post("/validate", json={"target_url": "https://target.example"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is True
    assert body["mode"] == "permissive"
    assert body["name"] == "Global Weather Agent"
    assert body["skills_count"] == 0
    assert body["warnings"]
    assert "pre-v1" in body["warnings"][0].lower()


@respx.mock
async def test_validate_returns_invalid_with_reason_on_404(
    client: httpx.AsyncClient,
) -> None:
    """Both well-known paths 404 → valid=false with both probed paths named
    in the reason so the user can copy/paste into a support ticket."""
    respx.get("https://target.example/.well-known/agent-card.json").mock(
        return_value=httpx.Response(404)
    )
    respx.get("https://target.example/.well-known/agent.json").mock(
        return_value=httpx.Response(404)
    )
    resp = await client.post("/validate", json={"target_url": "https://target.example"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is False
    assert "agent-card.json" in body["reason"]
    assert "agent.json" in body["reason"]


@respx.mock
async def test_validate_returns_invalid_on_5xx(client: httpx.AsyncClient) -> None:
    """A 5xx on the v1.0 path → invalid + reason. Don't silently retry the
    legacy path; an outage is an outage, not "agent uses legacy convention"."""
    respx.get("https://target.example/.well-known/agent-card.json").mock(
        return_value=httpx.Response(500)
    )
    resp = await client.post("/validate", json={"target_url": "https://target.example"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is False
    # The card resolver wraps 5xx as CardTransportError; message includes 500.
    assert "500" in body["reason"] or "transport" in body["reason"].lower()


async def test_validate_rejects_ssrf_targets(client: httpx.AsyncClient) -> None:
    """Reuses the existing _url_guard so /validate can't be used to fetch
    GCP metadata / loopback / link-local. Security parity with /run is
    non-negotiable per the security-reviewer convention.

    NB: `localhost`/`127.0.0.1` are intentionally allowed in dev mode (the
    demo target runs on localhost:8001 — see _url_guard.py for the
    documented ALLOW_LOCAL_TARGETS / environment=dev carve-out), so they
    are not in this matrix. Metadata server + link-local are unconditional.
    """
    for ssrf in (
        "http://169.254.169.254/computeMetadata/v1/",
        "http://metadata.google.internal/",
        "http://metadata/",
        "ftp://target.example/",  # non-http(s) scheme
    ):
        resp = await client.post("/validate", json={"target_url": ssrf})
        assert resp.status_code in (400, 422), (
            f"SSRF target {ssrf!r} should be rejected; got {resp.status_code}"
        )
