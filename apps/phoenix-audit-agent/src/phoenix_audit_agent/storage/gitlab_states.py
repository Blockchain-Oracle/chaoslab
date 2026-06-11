"""Single-use PKCE state docs for the GitLab OAuth connect flow (story-9.17).

`consume()` is get-AND-delete: a state token exchanges exactly once. The
code_verifier lives only in these docs — never in a browser round-trip.
"""

from __future__ import annotations

from typing import Any, Protocol

import structlog
from pydantic import ValidationError

from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import GitLabOAuthState

_log = structlog.get_logger(__name__)

_COLLECTION = "gitlab_oauth_states"
# Ops note (story-9.17): abandoned state docs outlive their 10-min TTL —
# the TTL is enforced at consume time; storage cleanup needs a Firestore
# TTL policy on `created_at` (deploy step, see story Notes).


class GitLabStateStore(Protocol):
    async def put(self, state: str, *, uid: str, code_verifier: str, created_at: str) -> None: ...

    async def consume(self, state: str) -> GitLabOAuthState | None:
        """Return the doc and DELETE it — single use. None when unknown."""
        ...


class FirestoreGitLabStateStore:
    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is None:
            self._db = get_firestore()
        return self._db

    async def put(self, state: str, *, uid: str, code_verifier: str, created_at: str) -> None:
        from datetime import UTC, datetime, timedelta

        await (
            self.db.collection(_COLLECTION)
            .document(state)
            .set(
                {
                    "state": state,
                    "uid": uid,
                    "code_verifier": code_verifier,
                    "created_at": created_at,
                    # Real Timestamp for the Firestore TTL policy (TTL ignores
                    # string fields) — abandoned verifiers self-delete. The
                    # consume-time TTL check stays authoritative at 10 min;
                    # this is storage hygiene, not the security boundary.
                    "expire_at": datetime.now(UTC) + timedelta(hours=1),
                }
            )
        )

    async def consume(self, state: str) -> GitLabOAuthState | None:
        from google.cloud import firestore

        ref = self.db.collection(_COLLECTION).document(state)
        transaction = self.db.transaction()

        # Transactional read-and-delete — two concurrent callbacks with the
        # same state must not BOTH consume it (single-use is the invariant
        # the in-memory fake's atomic pop already pins).
        @firestore.async_transactional
        async def _take(tx: Any) -> dict[str, Any] | None:
            snap = await ref.get(transaction=tx)
            if not snap.exists:
                return None
            tx.delete(ref)
            return snap.to_dict()

        data = await _take(transaction)
        if data is None:
            return None
        try:
            return GitLabOAuthState.model_validate(data)
        except ValidationError:
            _log.warning("gitlab_oauth_state_doc_corrupted", state_present=True)
            return None


_STORE: GitLabStateStore | None = None


def set_gitlab_state_store(store: GitLabStateStore | None) -> None:
    """Test/bootstrap seam. None resets to the lazy Firestore default."""
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    _STORE = store


def get_gitlab_state_store() -> GitLabStateStore:
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    if _STORE is None:
        _STORE = FirestoreGitLabStateStore()
    return _STORE


__all__ = [
    "FirestoreGitLabStateStore",
    "GitLabStateStore",
    "get_gitlab_state_store",
    "set_gitlab_state_store",
]
