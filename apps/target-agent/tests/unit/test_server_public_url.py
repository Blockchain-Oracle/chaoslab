"""Unit tests for server.py's PUBLIC_URL handling (issue #22 fix).

The agent card serves an `url` field that downstream `RemoteA2aAgent` clients
use to dispatch JSON-RPC. Without PUBLIC_URL, the URL is hardcoded to
`http://localhost:8001` regardless of where the container binds — unreachable
when deployed on Cloud Run.

These tests verify `_build_a2a_app()` correctly parses PUBLIC_URL and forwards
the right kwargs to `to_a2a()`. We mock `to_a2a` to capture its kwargs so the
assertions verify actual behavior (not just "the function returned something").

Why imports stay inside test functions: `_build_a2a_app()` reads `os.environ`
at call time, not at import time, so each test needs to monkeypatch the env
BEFORE the function is invoked. Module-top imports + module-level
`a2a_app = _build_a2a_app()` would freeze whatever env happened to be set at
collection time. Per-test imports + monkeypatch keep the isolation clean.
DO NOT "optimize" these imports to the module top.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with PUBLIC_URL unset so the default path is deterministic."""
    monkeypatch.delenv("PUBLIC_URL", raising=False)


def _patch_to_a2a(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Replace target_agent.server.to_a2a with a kwargs-capturing stub.

    Returns a dict that will be populated with the (kwargs) of the call.
    §14 carve-out: test-side stub of the ADK to_a2a constructor — we want to
    assert what kwargs the production code passes, not what to_a2a does.
    """
    captured: dict[str, object] = {}
    sentinel = object()

    def _stub(agent: object, **kw: object) -> object:
        captured["agent"] = agent
        captured["kwargs"] = kw
        captured["called"] = True
        return sentinel

    # §14 carve-out: test-side stub of target_agent.server.to_a2a
    import target_agent.server as _s

    monkeypatch.setattr(_s, "to_a2a", _stub)
    return captured


def test_build_a2a_app_without_public_url_calls_to_a2a_with_default_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default path (no PUBLIC_URL) → to_a2a(root_agent, port=8001) only.

    No host or protocol kwargs (let ADK defaults handle them).
    """
    captured = _patch_to_a2a(monkeypatch)
    from target_agent.server import _build_a2a_app

    _build_a2a_app()
    assert captured["called"] is True
    assert captured["kwargs"] == {"port": 8001}


def test_build_a2a_app_with_https_public_url_forwards_correct_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTPS PUBLIC_URL → host + protocol="https" + port=443 (scheme default)."""
    monkeypatch.setenv("PUBLIC_URL", "https://target-abc.run.app")
    captured = _patch_to_a2a(monkeypatch)
    from target_agent.server import _build_a2a_app

    _build_a2a_app()
    assert captured["kwargs"] == {
        "host": "target-abc.run.app",
        "port": 443,
        "protocol": "https",
    }


def test_build_a2a_app_with_explicit_port_uses_url_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PUBLIC_URL with explicit port → that port wins over scheme defaults."""
    monkeypatch.setenv("PUBLIC_URL", "https://target.example.com:9443")
    captured = _patch_to_a2a(monkeypatch)
    from target_agent.server import _build_a2a_app

    _build_a2a_app()
    assert captured["kwargs"] == {
        "host": "target.example.com",
        "port": 9443,
        "protocol": "https",
    }


def test_build_a2a_app_with_http_scheme_uses_port_80(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP PUBLIC_URL → port=80 + protocol="http". Counterpart to the https case."""
    monkeypatch.setenv("PUBLIC_URL", "http://internal.example.com")
    captured = _patch_to_a2a(monkeypatch)
    from target_agent.server import _build_a2a_app

    _build_a2a_app()
    assert captured["kwargs"] == {
        "host": "internal.example.com",
        "port": 80,
        "protocol": "http",
    }


def test_build_a2a_app_strips_trailing_path_from_public_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PUBLIC_URL with a path → host/port/protocol extracted; path component ignored.

    A future operator might accidentally include the trailing /.well-known/
    or similar; the parser should still work as long as host is present.
    """
    monkeypatch.setenv("PUBLIC_URL", "https://target.example.com/some/path")
    captured = _patch_to_a2a(monkeypatch)
    from target_agent.server import _build_a2a_app

    _build_a2a_app()
    assert captured["kwargs"]["host"] == "target.example.com"
    assert captured["kwargs"]["port"] == 443
    assert captured["kwargs"]["protocol"] == "https"


def test_build_a2a_app_with_empty_public_url_uses_default_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PUBLIC_URL="" (empty string) is falsy → default path, not malformed-URL error.

    Common case: deploy script does `--set-env-vars=PUBLIC_URL=` (literally empty)
    or `os.environ["PUBLIC_URL"] = ""`. Should fall through to the default,
    not raise.
    """
    monkeypatch.setenv("PUBLIC_URL", "")
    captured = _patch_to_a2a(monkeypatch)
    from target_agent.server import _build_a2a_app

    _build_a2a_app()
    assert captured["kwargs"] == {"port": 8001}


def test_build_a2a_app_rejects_url_without_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """A garbage PUBLIC_URL with no host should fail loud, not silently default."""
    monkeypatch.setenv("PUBLIC_URL", "not-a-url-at-all")
    from target_agent.server import _build_a2a_app

    with pytest.raises(SystemExit, match="scheme must be 'http' or 'https'"):
        _build_a2a_app()


def test_build_a2a_app_rejects_unsupported_scheme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fix for silent-failure H-1: schemes other than http/https must fail loud.

    Previously, `ftp://target.run.app` was silently accepted: scheme was
    truthy, hostname was parseable, port defaulted to 80 (because the code
    only checked == "https"), protocol was kept as "ftp", and the card
    advertised `ftp://target.run.app:80` — downstream RemoteA2aAgent
    dispatch then failed cryptically with no log line. Now: fail loud at
    boot with the bad input echoed.
    """
    monkeypatch.setenv("PUBLIC_URL", "ftp://target.run.app")
    from target_agent.server import _build_a2a_app

    with pytest.raises(SystemExit, match="scheme must be 'http' or 'https'"):
        _build_a2a_app()


def test_build_a2a_app_rejects_scheme_relative_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scheme-relative URLs (`//host`) are ambiguous — fail loud.

    Previously the empty scheme silently coerced to "http". An operator who
    meant HTTPS but typed `//target.run.app` would have traffic broken at
    the wire with no diagnostic. Now: same fail-loud as the ftp case.
    """
    monkeypatch.setenv("PUBLIC_URL", "//target.run.app")
    from target_agent.server import _build_a2a_app

    with pytest.raises(SystemExit, match="scheme must be 'http' or 'https'"):
        _build_a2a_app()


def test_main_rejects_non_integer_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() raises SystemExit when PORT env var isn't parseable as int.

    This was added in PR #18 (F2 from the silent-failure-hunter findings)
    but never had a direct test. test-analyzer Gap §5.2 caught the omission.
    """
    monkeypatch.setenv("PORT", "not-a-number")

    # Replace uvicorn.run with a sentinel — we don't want to actually start a
    # server in a unit test. If PORT parsing succeeds (regression), the test
    # would otherwise hang trying to bind a port.
    import target_agent.server as _s

    def _explode_if_called(*_a: object, **_kw: object) -> None:
        msg = "uvicorn.run reached — PORT validation skipped past the SystemExit"
        raise AssertionError(msg)

    monkeypatch.setattr(_s.uvicorn, "run", _explode_if_called)

    with pytest.raises(SystemExit, match="PORT env var must be an integer"):
        _s.main()


def _read_main_for_test() -> str:
    """Re-read server.py source so source-shape assertions reflect current state."""
    import pathlib

    src = pathlib.Path(__file__).parent.parent.parent / "src" / "target_agent" / "server.py"
    return src.read_text()


def test_server_source_references_public_url() -> None:
    """Source-shape regression guard: server.py must reference PUBLIC_URL + urlparse.

    Catches the case where a future refactor accidentally deletes the
    PUBLIC_URL handling, even if behavioral tests above somehow still pass.
    Kept as belt-and-suspenders alongside the behavioral mock-based tests
    above (which are the real workhorses).
    """
    contents = _read_main_for_test()
    assert "PUBLIC_URL" in contents, (
        "server.py must reference PUBLIC_URL — see issue #22 + audit-notes D4-8"
    )
    assert "urlparse" in contents, "server.py must use urlparse to parse PUBLIC_URL safely"
    # The whitelist check that closes silent-failure H-1.
    assert "_SUPPORTED_PUBLIC_URL_SCHEMES" in contents, (
        "server.py must whitelist supported PUBLIC_URL schemes — see H-1 in PR #27 review"
    )
