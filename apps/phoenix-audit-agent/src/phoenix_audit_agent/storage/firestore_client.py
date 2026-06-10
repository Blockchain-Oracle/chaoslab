"""Lazy Firestore AsyncClient singleton.

Construction is deferred past import so unit tests (which inject in-memory
stores via the seams in runs.py/agents.py) never touch credentials. The
client honors FIRESTORE_EMULATOR_HOST automatically.
"""

from __future__ import annotations

from typing import Any

_client: Any = None


def get_firestore() -> Any:
    global _client  # noqa: PLW0603 — lazy client singleton
    if _client is None:
        from google.cloud import firestore

        _client = firestore.AsyncClient()
    return _client


def reset_firestore() -> None:
    """Symmetry with set_run_store(None) — lets tests swap emulator/clients."""
    global _client  # noqa: PLW0603 — lazy client singleton
    _client = None


__all__ = ["get_firestore", "reset_firestore"]
