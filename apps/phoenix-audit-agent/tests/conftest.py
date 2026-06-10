"""Shared test bootstrap for phoenix-audit-agent.

macOS + Homebrew: WeasyPrint loads Pango via cffi `dlopen`, which does not
search /opt/homebrew/lib by default on Apple Silicon. Setting the fallback
path here (before any deferred `import weasyprint`) makes the PDF renderer
tests run on dev machines with `brew install pango`; Linux CI and the
Docker image get the libraries via apt and ignore this.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from typing import Any

import pytest

if sys.platform == "darwin":
    _brew_lib = "/opt/homebrew/lib"
    if os.path.isdir(_brew_lib):
        existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if _brew_lib not in existing.split(":"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                f"{existing}:{_brew_lib}" if existing else _brew_lib
            )


# --- Firebase auth seams (story-9.4) -----------------------------------------
# Two seams, two purposes:
# - `auth_as` — FastAPI dependency override. The default for endpoint tests
#   whose subject is NOT auth: requests arrive pre-authenticated as a chosen
#   uid without minting headers. Modules opt in via a tiny autouse wrapper.
# - `as_user` — the real header path (`X-Firebase-Id-Token`) with the Google
#   verifier monkeypatched. For tests whose subject IS the auth wiring.
# NOTE: lives here (not tests/unit/conftest.py) — a tests/unit/conftest.py
# module name collides with target-agent's in the combined two-app run.


@pytest.fixture
def auth_as() -> Iterator[Callable[..., None]]:
    """Override `require_user` so requests run as a chosen fake user."""
    from phoenix_audit_agent.api.auth import AuthedUser, require_user
    from phoenix_audit_agent.main import app

    def set_user(uid: str = "user-test", email: str | None = None) -> None:
        app.dependency_overrides[require_user] = lambda: AuthedUser(uid=uid, email=email)

    set_user()
    yield set_user
    app.dependency_overrides.pop(require_user, None)


@pytest.fixture
def as_user(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., dict[str, str]]]:
    """Mint `X-Firebase-Id-Token` headers for a fake verified user.

    The Google verifier is monkeypatched — the real one fetches certs over
    HTTPS, so an unmocked call would fail offline for the wrong reason.
    Token format `uid:<uid>` maps to claims `{"sub": uid, "email": ...}`.
    """
    from phoenix_audit_agent.api import auth as auth_api
    from phoenix_audit_agent.config import get_settings

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()

    def verify(token: str, request: object, audience: object) -> dict[str, Any]:
        if not token.startswith("uid:"):
            msg = "unknown test token"
            raise ValueError(msg)
        uid = token.removeprefix("uid:")
        return {"sub": uid, "email": f"{uid}@test.example"}

    monkeypatch.setattr(auth_api.id_token, "verify_firebase_token", verify)

    def headers(uid: str = "user-a") -> dict[str, str]:
        return {"x-firebase-id-token": f"uid:{uid}"}

    yield headers
    get_settings.cache_clear()
