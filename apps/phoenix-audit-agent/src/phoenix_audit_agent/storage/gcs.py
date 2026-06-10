"""Shared, lazily-cached google-cloud-storage client.

`storage.Client()` performs ADC credential + project discovery (a
metadata-server HTTP round-trip on Cloud Run). Constructing one per signed
URL / per emitter made every report view pay that cost repeatedly — mirror
`firestore_client.py`'s lazy singleton instead.

The SDK is sync-only; callers must keep uploads/signing inside
`asyncio.to_thread` (the client itself is thread-safe).
"""

from __future__ import annotations

from typing import Any

_CLIENT: Any | None = None


def get_storage_client() -> Any:
    global _CLIENT  # noqa: PLW0603 — module singleton is the documented seam
    if _CLIENT is None:
        # Deferred import so test stubs avoid google-cloud-storage's auth
        # probe entirely; the import only runs when a real client is needed.
        from google.cloud import storage

        _CLIENT = storage.Client()
    return _CLIENT


def set_storage_client(client: Any | None) -> None:
    """Test/bootstrap seam. None resets to the lazy default."""
    global _CLIENT  # noqa: PLW0603 — module singleton is the documented seam
    _CLIENT = client


__all__ = ["get_storage_client", "set_storage_client"]
