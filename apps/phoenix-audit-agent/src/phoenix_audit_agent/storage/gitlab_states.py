"""Single-use PKCE state docs for the GitLab OAuth connect flow (story-9.17).

`consume()` is get-AND-delete: a state token exchanges exactly once. The
code_verifier lives only in these docs — never in a browser round-trip.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import ValidationError

from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import GitLabOAuthState

_COLLECTION = "gitlab_oauth_states"


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
        await (
            self.db.collection(_COLLECTION)
            .document(state)
            .set(
                {
                    "state": state,
                    "uid": uid,
                    "code_verifier": code_verifier,
                    "created_at": created_at,
                }
            )
        )

    async def consume(self, state: str) -> GitLabOAuthState | None:
        ref = self.db.collection(_COLLECTION).document(state)
        doc = await ref.get()
        if not doc.exists:
            return None
        # Delete BEFORE returning — a crash between read and delete must err
        # on the unusable side (single-use beats replayable).
        await ref.delete()
        try:
            return GitLabOAuthState.model_validate(doc.to_dict())
        except ValidationError:
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
