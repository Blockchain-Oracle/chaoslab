"""Integration test: target-agent's A2A server serves a valid agent card.

Spins up `a2a_app` via uvicorn.Server in a background daemon thread, polls
`/.well-known/agent-card.json` until reachable, asserts JSON structure.

Marked @pytest.mark.integration so unit-only runs skip it. NOT @online —
no Gemini / Phoenix / external service calls; everything is local.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest
import uvicorn

from target_agent.server import a2a_app


def _pick_free_port() -> int:
    """Bind to port 0 and read back the OS-assigned port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class _ServerThread:
    """Runs uvicorn.Server in a daemon thread with a clean shutdown handle.

    uvicorn.Server.should_exit is the documented in-process shutdown signal
    (see https://www.uvicorn.org/server-behavior/#server-shutdown). Setting
    it on the server instance causes the running loop to return cleanly.
    """

    def __init__(self, host: str, port: int) -> None:
        config = uvicorn.Config(
            a2a_app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False,
            lifespan="on",
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


@pytest.fixture
def a2a_server() -> Iterator[str]:
    """Yields the base URL of a started A2A server; tears it down after."""
    host = "127.0.0.1"
    port = _pick_free_port()
    server = _ServerThread(host, port)
    server.start()

    base_url = f"http://{host}:{port}"
    deadline = time.monotonic() + 30.0
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{base_url}/.well-known/agent-card.json", timeout=2.0)
            if r.status_code == 200:
                break
        except httpx.HTTPError as e:
            last_err = e
        time.sleep(0.2)
    else:
        server.stop()
        msg = f"A2A server never bound to {base_url} within 30s; last error: {last_err}"
        raise RuntimeError(msg)

    try:
        yield base_url
    finally:
        server.stop()


@pytest.mark.integration
def test_agent_card_returns_200_with_target_name(a2a_server: str) -> None:
    """The agent card endpoint resolves with the correct agent identity."""
    r = httpx.get(f"{a2a_server}/.well-known/agent-card.json", timeout=5.0)
    assert r.status_code == 200
    card = r.json()
    assert card.get("name") == "target_customer_support", f"unexpected name: {card.get('name')}"


@pytest.mark.integration
def test_agent_card_advertises_all_three_tools(a2a_server: str) -> None:
    """All 3 ADK tools surface as A2A skills with their function names."""
    r = httpx.get(f"{a2a_server}/.well-known/agent-card.json", timeout=5.0)
    card = r.json()
    skills = card.get("skills") or []
    skill_names = {s.get("name") for s in skills if isinstance(s, dict)}
    # Skill names map 1:1 to the ADK FunctionTool function names.
    # If ADK's auto-discovery diverges here, server.py must declare AgentSkill
    # constructors explicitly — see story-2.2 Notes for the override path.
    expected = {"lookup_order", "refund", "escalate"}
    missing = expected - skill_names
    assert not missing, f"missing skill names: {missing}; got: {skill_names}"
