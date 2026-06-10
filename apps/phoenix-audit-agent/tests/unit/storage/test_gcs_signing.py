"""signed_get_url — v4 signing must work on Cloud Run's token-only creds.

The metadata-server credentials carry NO private key: a bare
``generate_signed_url`` raises AttributeError ("you need a private key"),
which is why every deployed run had dead downloads (IF-16 follow-on). The
helper must detect signer-less credentials and route through the IAM
signBlob API (service_account_email + access_token kwargs).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from phoenix_audit_agent.storage.gcs import signed_get_url

_TTL = timedelta(days=2)


class _StubBlob:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client
        self.kwargs: dict[str, Any] | None = None

    def generate_signed_url(self, **kwargs: Any) -> str:
        self.kwargs = kwargs
        return "https://signed.example/blob"


class _StubClient:
    def __init__(self, credentials: Any) -> None:
        self._credentials = credentials


class _SignerCreds:
    """Credentials WITH a private key (impersonated SA / key file)."""

    def sign_bytes(self, payload: bytes) -> bytes:  # pragma: no cover - marker
        return b"sig"


class _TokenOnlyCreds:
    """Cloud Run metadata-server credentials — no sign_bytes attribute."""

    def __init__(self) -> None:
        self.service_account_email = "runtime@example.iam.gserviceaccount.com"
        self.token: str | None = None
        self.valid = False
        self.refreshed = 0

    def refresh(self, request: Any) -> None:
        self.refreshed += 1
        self.token = "ya29.token"
        self.valid = True


def test_signer_credentials_sign_directly() -> None:
    blob = _StubBlob(client=_StubClient(_SignerCreds()))
    url = signed_get_url(blob, ttl=_TTL)
    assert url == "https://signed.example/blob"
    assert blob.kwargs is not None
    assert "service_account_email" not in blob.kwargs
    assert blob.kwargs["version"] == "v4"
    assert blob.kwargs["method"] == "GET"
    assert blob.kwargs["expiration"] == _TTL


def test_token_only_credentials_route_through_iam_signing() -> None:
    creds = _TokenOnlyCreds()
    blob = _StubBlob(client=_StubClient(creds))
    url = signed_get_url(blob, ttl=_TTL)
    assert url == "https://signed.example/blob"
    assert creds.refreshed == 1
    assert blob.kwargs is not None
    assert blob.kwargs["service_account_email"] == creds.service_account_email
    assert blob.kwargs["access_token"] == "ya29.token"


def test_valid_token_is_not_refreshed_again() -> None:
    creds = _TokenOnlyCreds()
    creds.token = "ya29.cached"
    creds.valid = True
    blob = _StubBlob(client=_StubClient(creds))
    signed_get_url(blob, ttl=_TTL)
    assert creds.refreshed == 0
    assert blob.kwargs is not None
    assert blob.kwargs["access_token"] == "ya29.cached"


def test_blob_without_client_signs_directly() -> None:
    # Test seams hand in bare stub blobs — no credential introspection possible.
    blob = _StubBlob(client=None)
    signed_get_url(blob, ttl=_TTL)
    assert blob.kwargs is not None
    assert "service_account_email" not in blob.kwargs
