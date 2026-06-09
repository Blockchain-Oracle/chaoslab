"""Unit tests for the `_fingerprint.behavioral_fingerprint` v0 stub.

Per S3.6 + the `@advanced` escape hatch: v0 returns an empty-ish dict with
the requested opts echoed back so the caller (adapter / S5.7 Injector) can
verify wiring is correct. v1 (story-3.6b) will replace this with the real
probes.
"""

from __future__ import annotations

import httpx

from chaoslab_agent.injector.target_adapters._fingerprint import behavioral_fingerprint


async def test_v0_stub_returns_dict_with_v0_marker() -> None:
    """The version marker `"v0-stub"` is the call site's hint that the real
    probes haven't landed yet — Injector uses it to skip fingerprint-derived
    fault selection until v1."""
    async with httpx.AsyncClient() as http:
        result = await behavioral_fingerprint(http, "http://x", opts={})
    assert result["version"] == "v0-stub"
    assert result["requested"] == {}


async def test_v0_stub_echoes_requested_opts() -> None:
    """Whatever the caller asked for is round-tripped so v1 wiring can be
    verified by inspection of `requested` in real runs."""
    async with httpx.AsyncClient() as http:
        result = await behavioral_fingerprint(
            http,
            "http://x",
            opts={"system_prompt": True, "style": True, "streaming": False},
        )
    assert result["requested"]["system_prompt"] is True
    assert result["requested"]["style"] is True
    assert result["requested"]["streaming"] is False


async def test_v0_stub_handles_none_opts() -> None:
    """Default-None opts must not crash — the call site may pass None when
    only the discovery-derived signals are needed."""
    async with httpx.AsyncClient() as http:
        result = await behavioral_fingerprint(http, "http://x", opts=None)
    assert result["requested"] == {}


async def test_v0_stub_carries_deferral_note() -> None:
    """The notes field documents that fingerprinting is deferred — Epic 6's
    pattern-finder can show this in audit reports so a regulator-facing
    reader sees explicitly that behavioral signals are a stub."""
    async with httpx.AsyncClient() as http:
        result = await behavioral_fingerprint(http, "http://x")
    assert "story-3.6b" in result["notes"]
