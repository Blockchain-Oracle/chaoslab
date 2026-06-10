"""Shared, lazily-cached google-cloud-storage client.

`storage.Client()` performs ADC credential + project discovery (a
metadata-server HTTP round-trip on Cloud Run). Constructing one per signed
URL / per emitter made every report view pay that cost repeatedly — mirror
`firestore_client.py`'s lazy singleton instead.

The SDK is sync-only; callers must keep uploads/signing inside
`asyncio.to_thread` (the client itself is thread-safe).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import timedelta

_CLIENT: Any | None = None


def signed_get_url(blob: Any, *, ttl: timedelta) -> str:
    """v4 signed GET URL that also works on token-only credentials.

    Cloud Run's metadata-server credentials carry NO private key — a bare
    ``generate_signed_url`` raises AttributeError ("you need a private
    key"). When the client's credentials lack ``sign_bytes``, sign via the
    IAM signBlob API instead (service_account_email + access_token; needs
    the ``roles/iam.serviceAccountTokenCreator`` self-grant on the runtime
    SA — audit-notes B8). Signer-carrying credentials (impersonated SA,
    key file) and seam-injected stub blobs take the direct path.
    """
    kwargs: dict[str, Any] = {}
    creds = getattr(getattr(blob, "client", None), "_credentials", None)
    if creds is not None and not hasattr(creds, "sign_bytes"):
        if not getattr(creds, "valid", False):
            from google.auth.transport import requests as ga_requests

            creds.refresh(ga_requests.Request())
        kwargs = {
            "service_account_email": creds.service_account_email,
            "access_token": creds.token,
        }
    return str(blob.generate_signed_url(version="v4", expiration=ttl, method="GET", **kwargs))


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


__all__ = ["get_storage_client", "set_storage_client", "signed_get_url"]
