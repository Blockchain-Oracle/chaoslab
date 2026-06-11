"""Dataset-index store (story-9.15) — Firestore `datasets/{slug}` documents
plus the test seam, mirroring `storage/profiles.py`.

The store owns ONLY the thin index row (slug + phoenix_dataset_id + kind +
owner_uid + agent_id + content_hash). Example rows live in Phoenix; the
`PhoenixDatasetClient` wrapper handles them.
"""

from __future__ import annotations

from typing import Any, Protocol

import structlog
from pydantic import ValidationError

from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import DatasetIndex

_log = structlog.get_logger(__name__)

_COLLECTION = "datasets"


class DatasetIndexStore(Protocol):
    async def upsert(self, index: DatasetIndex) -> None: ...

    async def get_by_slug(self, slug: str) -> DatasetIndex | None: ...

    async def list_visible(self, uid: str | None) -> list[DatasetIndex]:
        """Visible rows for the given user: every battery row, every
        uploaded/regression row whose `owner_uid == uid`. `uid=None`
        returns battery-only."""
        ...

    async def delete_by_slug(self, slug: str) -> None:
        """Idempotent: deleting a non-existent slug is a no-op."""
        ...


class FirestoreDatasetIndexStore:
    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is None:
            self._db = get_firestore()
        return self._db

    async def upsert(self, index: DatasetIndex) -> None:
        # Whole-doc write keyed by the slug. The index is small + immutable
        # in shape, so we don't need field-merge semantics here.
        await self.db.collection(_COLLECTION).document(index.dataset_id).set(index.model_dump())

    async def get_by_slug(self, slug: str) -> DatasetIndex | None:
        doc = await self.db.collection(_COLLECTION).document(slug).get()
        if not doc.exists:
            return None
        try:
            return DatasetIndex.model_validate(doc.to_dict())
        except ValidationError:
            # Same discipline as profiles.py: don't swallow into None — a
            # downstream write would overwrite a corrupted doc with defaults.
            _log.error("dataset_index_doc_corrupted", slug=slug, exc_info=True)
            raise

    async def list_visible(self, uid: str | None) -> list[DatasetIndex]:
        # Firestore filter: battery (owner_uid IS NULL) UNION owner_uid == uid.
        # We do two queries and merge — Firestore doesn't support OR across
        # disjoint values directly in v1 client; two reads stay simple + cheap.
        battery_docs = self.db.collection(_COLLECTION).where("owner_uid", "==", None).stream()
        rows: list[DatasetIndex] = []
        async for doc in battery_docs:
            try:
                rows.append(DatasetIndex.model_validate(doc.to_dict()))
            except ValidationError:
                _log.error("dataset_index_doc_corrupted", slug=doc.id, exc_info=True)
        if uid is not None:
            owned = self.db.collection(_COLLECTION).where("owner_uid", "==", uid).stream()
            async for doc in owned:
                try:
                    rows.append(DatasetIndex.model_validate(doc.to_dict()))
                except ValidationError:
                    _log.error("dataset_index_doc_corrupted", slug=doc.id, exc_info=True)
        return rows

    async def delete_by_slug(self, slug: str) -> None:
        # Firestore delete on missing doc is a no-op — matches our contract.
        await self.db.collection(_COLLECTION).document(slug).delete()


_STORE: DatasetIndexStore | None = None


def set_dataset_index_store(store: DatasetIndexStore | None) -> None:
    """Test/bootstrap seam. `None` resets to the lazy Firestore default."""
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    _STORE = store


def get_dataset_index_store() -> DatasetIndexStore:
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    if _STORE is None:
        _STORE = FirestoreDatasetIndexStore()
    return _STORE


__all__ = [
    "DatasetIndexStore",
    "FirestoreDatasetIndexStore",
    "get_dataset_index_store",
    "set_dataset_index_store",
]
