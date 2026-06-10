"""Demo-target seed URL is env-driven (story-9.10 W0.1).

The hardcoded localhost:8001 seed fired REAL failing runs from the deployed
app — one un-confirmed click reached for a URL that only exists on dev
machines. The seed must point at the deployed target-agent in deployed envs.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from phoenix_audit_agent.config import get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("DEMO_TARGET_URL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_seed_defaults_to_localhost_for_dev() -> None:
    from phoenix_audit_agent.storage.agents import demo_target_seed

    assert demo_target_seed().url == "http://localhost:8001"
    assert demo_target_seed().agent_id == "demo-target"


def test_seed_url_honors_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_TARGET_URL", "https://target-agent-x.a.run.app")
    get_settings.cache_clear()
    from phoenix_audit_agent.storage.agents import demo_target_seed

    assert demo_target_seed().url == "https://target-agent-x.a.run.app"


async def test_store_list_serves_env_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seed row a signed-in user actually SEES carries the env URL."""
    from ..storage.fakes import InMemoryAgentStore

    monkeypatch.setenv("DEMO_TARGET_URL", "https://target-agent-x.a.run.app")
    get_settings.cache_clear()
    rows = await InMemoryAgentStore().list_agents()
    demo = next(a for a in rows if a.agent_id == "demo-target")
    assert demo.url == "https://target-agent-x.a.run.app"
