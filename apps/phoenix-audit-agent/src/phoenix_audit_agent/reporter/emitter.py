"""GCS delivery for the signed report artifact set.

Uploads report.pdf + report.json + signature.json under
reports/<run_id>/ in the recipes bucket and returns v4 signed URLs.
Reuses the MarkdownEmitter's storage protocol + upload conventions
(thread offload — google-cloud-storage is sync-only).
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import cast

import structlog

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.patcher.markdown_emitter import StorageClient
from phoenix_audit_agent.storage.gcs import get_storage_client

_log = structlog.get_logger(__name__)

_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".json": "application/json",
}


class ReportEmitter:
    def __init__(self, storage_client: StorageClient | None = None) -> None:
        settings = get_settings()
        self._bucket_name = settings.GCS_RECIPES_BUCKET
        self._ttl = timedelta(days=settings.GCS_SIGNED_URL_TTL_DAYS)
        self._client: StorageClient = storage_client or cast(StorageClient, get_storage_client())

    def _upload_one(self, blob_name: str, payload: bytes, content_type: str) -> str:
        from phoenix_audit_agent.storage.gcs import signed_get_url

        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(blob_name)
        # if_generation_match=0 → create-only: a retry/re-run can never
        # silently overwrite an already-delivered regulator artifact.
        blob.upload_from_string(payload, content_type=content_type, if_generation_match=0)
        return signed_get_url(blob, ttl=self._ttl)

    async def emit(self, run_id: str, artifacts: dict[str, bytes]) -> dict[str, str]:
        """Upload the signature sidecar FIRST, then the rest concurrently.

        Sidecar-first keeps the invariant that a partial failure can never
        leave an unverifiable report orphaned in the bucket; the remaining
        documents upload in parallel (the PDF can be MBs — serial uploads
        added seconds to the tail of every audit). On failure the
        already-uploaded set is logged by name so a partial delivery is
        never an untracked orphan.
        """
        urls: dict[str, str] = {}

        async def _upload(name: str, payload: bytes) -> None:
            suffix = name[name.rfind(".") :]
            content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")
            blob_name = f"reports/{run_id}/{name}"
            urls[name] = await asyncio.to_thread(self._upload_one, blob_name, payload, content_type)
            _log.info("report_artifact_uploaded", blob=blob_name, bytes=len(payload))

        try:
            remaining = dict(artifacts)
            sidecar = remaining.pop("signature.json", None)
            if sidecar is not None:
                await _upload("signature.json", sidecar)
            results = await asyncio.gather(
                *(_upload(name, payload) for name, payload in remaining.items()),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, BaseException):
                    raise result
        except Exception:
            _log.error(
                "report_upload_partial_failure",
                run_id=run_id,
                uploaded=sorted(urls),
                missing=sorted(set(artifacts) - set(urls)),
                exc_info=True,
            )
            raise
        return urls
