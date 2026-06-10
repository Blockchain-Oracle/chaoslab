"""ReportEmitter GCS delivery — create-only uploads.

`if_generation_match=0` makes every report artifact create-only: a re-run
or retry can never silently overwrite a previously delivered (and possibly
already downloaded/signed-off) regulator artifact.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.patcher.markdown_emitter import StorageClient
from phoenix_audit_agent.reporter.emitter import ReportEmitter


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeBlob:
    def __init__(self, name: str, uploads: list[dict[str, Any]]) -> None:
        self._name = name
        self._uploads = uploads

    def upload_from_string(
        self,
        payload: bytes,
        content_type: str,
        if_generation_match: int | None = None,
    ) -> None:
        self._uploads.append(
            {
                "blob": self._name,
                "content_type": content_type,
                "if_generation_match": if_generation_match,
            }
        )

    def generate_signed_url(self, **_: Any) -> str:
        return f"https://signed.example/{self._name}"


class _FakeBucket:
    def __init__(self, uploads: list[dict[str, Any]]) -> None:
        self._uploads = uploads

    def blob(self, name: str) -> _FakeBlob:
        return _FakeBlob(name, self._uploads)


class _FakeClient:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    def bucket(self, name: str) -> _FakeBucket:
        return _FakeBucket(self.uploads)


@pytest.mark.asyncio
async def test_uploads_are_create_only() -> None:
    client = _FakeClient()
    emitter = ReportEmitter(storage_client=cast(StorageClient, client))

    urls = await emitter.emit(
        "run_abcabcabcabc",
        {"report.pdf": b"%PDF", "report.json": b"{}", "signature.json": b"{}"},
    )

    assert set(urls) == {"report.pdf", "report.json", "signature.json"}
    assert len(client.uploads) == 3
    for upload in client.uploads:
        assert upload["if_generation_match"] == 0, upload
