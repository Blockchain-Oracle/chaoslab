"""User-profile store: Firestore `users/{uid}` documents + the test seam.

GET /profile never materializes a document — defaults are computed, so the
collection only ever contains profiles a user actually saved. Writes are
field-level merges: unknown stored fields (the Wave-C gitlab blob, wizard
fields) must survive a settings save untouched.
"""

from __future__ import annotations

from typing import Any, Protocol

import structlog
from pydantic import ValidationError

from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import UserProfile

_log = structlog.get_logger(__name__)

_COLLECTION = "users"


class ProfileStore(Protocol):
    async def get(self, uid: str) -> UserProfile | None: ...

    async def merge(self, uid: str, fields: dict[str, Any]) -> None:
        """Upsert ONLY the given fields — never a whole-document overwrite."""
        ...


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
        try:
            return UserProfile.model_validate(doc.to_dict())
        except ValidationError:
            # Do NOT swallow into None — a follow-up PATCH would then overwrite
            # the corrupted doc with defaults (data destruction). Log so the
            # 500 is debuggable, then let it surface.
            _log.error("profile_doc_corrupted", uid=uid, exc_info=True)
            raise

    async def merge(self, uid: str, fields: dict[str, Any]) -> None:
        await self.db.collection(_COLLECTION).document(uid).set(fields, merge=True)


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
