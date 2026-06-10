"""User-profile store: Firestore `users/{uid}` documents + the test seam.

GET /profile never materializes a document — defaults are computed, so the
collection only ever contains profiles a user actually saved.
"""

from __future__ import annotations

from typing import Any, Protocol

from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import UserProfile

_COLLECTION = "users"


class ProfileStore(Protocol):
    async def get(self, uid: str) -> UserProfile | None: ...

    async def set(self, profile: UserProfile) -> None: ...


class FirestoreProfileStore:
    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is None:
            self._db = get_firestore()
        return self._db

    async def get(self, uid: str) -> UserProfile | None:
        doc = await self.db.collection(_COLLECTION).document(uid).get()
        if not doc.exists:
            return None
        return UserProfile.model_validate(doc.to_dict())

    async def set(self, profile: UserProfile) -> None:
        # Whole-document set: the API layer merges PATCH fields into the
        # stored profile first, so set() semantics can't drop sibling fields.
        await self.db.collection(_COLLECTION).document(profile.uid).set(profile.model_dump())


_STORE: ProfileStore | None = None


def set_profile_store(store: ProfileStore | None) -> None:
    """Test/bootstrap seam. None resets to the lazy Firestore default."""
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    _STORE = store


def get_profile_store() -> ProfileStore:
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    if _STORE is None:
        _STORE = FirestoreProfileStore()
    return _STORE


__all__ = [
    "FirestoreProfileStore",
    "ProfileStore",
    "get_profile_store",
    "set_profile_store",
]
