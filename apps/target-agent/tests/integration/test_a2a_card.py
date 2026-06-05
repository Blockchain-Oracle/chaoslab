"""Integration test: target-agent's A2A server serves a valid agent card +
responds to A2A JSON-RPC method calls over the wire.

Spins up `a2a_app` via uvicorn.Server in a background daemon thread, polls
`/.well-known/agent-card.json` until reachable, asserts JSON structure, then
POSTs an A2A message/send to prove the wire actually carries method calls.

Marked @pytest.mark.integration so unit-only runs skip it. NOT @online —
no Gemini / Phoenix / external service calls; everything is local.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
import warnings
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


class _MemoryLogHandler(logging.Handler):
    """Captures uvicorn's log records so poll-timeout failures can surface root cause."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        # Mirror stdlib StreamHandler.emit: format errors route through
        # handleError() (which respects logging.raiseExceptions) rather than
        # crashing the producing thread.
        try:
            self.records.append(self.format(record))
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class _ServerThread:
    """Runs uvicorn.Server in a daemon thread with a clean shutdown handle.

    uvicorn.Server.should_exit is the documented in-process shutdown signal
    (see https://www.uvicorn.org/server-behavior/#server-shutdown). Setting
    it on the server instance causes the running loop to return cleanly.

    Log capture: attaches a MemoryHandler to the `uvicorn` + `uvicorn.error`
    loggers so a poll-timeout failure can include the last 50 lines of server
    output in its error message instead of just saying "never bound."
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
        self._log_handler = _MemoryLogHandler()
        self._log_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        for name in ("uvicorn", "uvicorn.error"):
            logging.getLogger(name).addHandler(self._log_handler)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def captured_logs(self) -> list[str]:
        return list(self._log_handler.records)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)
        for name in ("uvicorn", "uvicorn.error"):
            logging.getLogger(name).removeHandler(self._log_handler)
        if self.thread.is_alive():
            warnings.warn(
                "_ServerThread.stop(): uvicorn server did not honor should_exit "
                "within 10s; daemon thread leaked. Indicates a shutdown defect in "
                "to_a2a() or the ADK A2A handler.",
                stacklevel=2,
            )


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
        # Capture logs BEFORE stop() so the handler isn't already removed.
        captured = "\n".join(server.captured_logs[-50:]) or "(no uvicorn output captured)"
        server.stop()
        msg = (
            f"A2A server never bound to {base_url} within 30s; "
            f"last httpx error: {last_err}\n"
            f"--- last 50 lines of uvicorn output ---\n{captured}"
        )
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
    assert "skills" in card, f"card missing 'skills' field (A2A spec drift?): {card.keys()}"
    skills = card["skills"] or []
    skill_names = {s.get("name") for s in skills if isinstance(s, dict)}
    # Skill names map 1:1 to the ADK FunctionTool function names. If a future
    # ADK upgrade breaks auto-discovery, declare explicit AgentSkill constructors
    # at the to_a2a() call-site in target_agent/server.py — see
    # research/google-cloud-rapid-agent/architecture/03-multi-agent-patterns.md §2.2.
    expected = {"lookup_order", "refund", "escalate"}
    missing = expected - skill_names
    assert not missing, f"missing skill names: {missing}; got: {skill_names}"


@pytest.mark.integration
def test_a2a_message_send_returns_structured_jsonrpc(a2a_server: str) -> None:
    """POSTs an A2A message/send to prove the wire carries method calls.

    Complements the card tests by exercising the door, not just the storefront.
    A stub agent with matching name+tools would pass the card tests but fail
    this one if the runner is misconfigured.

    We don't assert agent semantics (Gemini ADC isn't required for CI), only
    that the server returns a structurally valid JSON-RPC 2.0 envelope — that
    proves the wire works regardless of whether the LLM call inside succeeds.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": "smoke-1",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "What is order 12345?"}],
                "messageId": "smoke-msg-1",
            }
        },
    }
    try:
        r = httpx.post(f"{a2a_server}/", json=payload, timeout=60.0)
    except httpx.HTTPError as e:
        pytest.fail(f"A2A wire refused the POST: {e}")
    # Accept any structured HTTP outcome — what we care about is the
    # JSON-RPC envelope, not the inner agent result.
    assert r.status_code in (200, 400, 500), f"unexpected HTTP {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body.get("jsonrpc") == "2.0", f"missing/invalid jsonrpc field: {body}"
    assert body.get("id") == "smoke-1", f"id mismatch: {body.get('id')}"
    # Per JSON-RPC 2.0 spec, exactly one of result/error must be present.
    assert ("result" in body) or ("error" in body), f"neither result nor error: {body}"
