"""Unit tests for MarkdownEmitter — stubs the GCS boundary."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.patcher.markdown_emitter import (
    EmitResult,
    MarkdownEmitter,
    StorageClient,
    _Blob,
    _Bucket,
)
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
)


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


def _recipe() -> HardeningRecipe:
    cluster = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="no input validation",
        failure_count=1,
        span_ids=["0123456789abcdef"],
        fault_classes=["malformed_tool_output"],
    )
    return HardeningRecipe(
        recipe_id="recipe_abc123def456",
        target_agent_id="target_customer_support",
        generated_at="2026-06-02T14:30:00Z",
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=1),
        prompt_patches=[],
        tool_validation_diffs=[],
        regression_test_cases=[],
        estimated_resilience_improvement=0.46,
    )


class _RecordingBlob(_Blob):
    def __init__(self) -> None:
        self.uploaded: tuple[bytes, str] | None = None
        self.signed_args: dict[str, Any] = {}
        self.if_generation_match: int | None = None

    def upload_from_string(
        self,
        data: bytes,
        content_type: str,
        if_generation_match: int = 0,
    ) -> None:
        self.uploaded = (data, content_type)
        self.if_generation_match = if_generation_match

    def generate_signed_url(
        self,
        *,
        version: str,
        expiration: timedelta,
        method: str,
    ) -> str:
        self.signed_args = {
            "version": version,
            "expiration": expiration,
            "method": method,
        }
        return (
            "https://storage.googleapis.com/chaoslab-recipes/recipe_abc123def456.md"
            "?X-Goog-Algorithm=GOOG4-RSA-SHA256"
            "&X-Goog-Credential=fake-sa%40chaoslab.iam.gserviceaccount.com"
            "&X-Goog-Date=20260609T000000Z"
            f"&X-Goog-Expires={int(expiration.total_seconds())}"
            "&X-Goog-SignedHeaders=host"
            "&X-Goog-Signature=deadbeef"
        )


class _RecordingBucket(_Bucket):
    def __init__(self, blob: _RecordingBlob, *, exists_result: bool = True) -> None:
        self._blob = blob
        self.blob_names: list[str] = []
        self._exists = exists_result

    def blob(self, name: str) -> _RecordingBlob:
        self.blob_names.append(name)
        return self._blob

    def exists(self) -> bool:
        return self._exists


class _RecordingClient(StorageClient):
    def __init__(self) -> None:
        self.blob = _RecordingBlob()
        self.bucket_obj = _RecordingBucket(self.blob)
        self.bucket_names: list[str] = []

    def bucket(self, name: str) -> _RecordingBucket:
        self.bucket_names.append(name)
        return self.bucket_obj


async def test_emit_uploads_to_gcs_with_correct_uri() -> None:
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert isinstance(result, EmitResult)
    assert result.gcs_uri == "gs://chaoslab-recipes/recipe_abc123def456.md"
    assert client.bucket_names == ["chaoslab-recipes"]
    assert client.bucket_obj.blob_names == ["recipe_abc123def456.md"]


async def test_emit_uploads_with_markdown_content_type() -> None:
    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).emit(_recipe())
    uploaded = client.blob.uploaded
    assert uploaded is not None
    content, content_type = uploaded
    assert content_type == "text/markdown; charset=utf-8"
    assert content.startswith(b"# ChaosLab Hardening Recipe")


async def test_emit_returns_signed_url_with_expected_query_params() -> None:
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert result.signed_url.startswith("https://")
    assert "X-Goog-Signature" in result.signed_url
    assert "X-Goog-Algorithm" in result.signed_url


async def test_emit_ttl_seconds_match_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GCS_SIGNED_URL_TTL_DAYS", "7")
    get_settings.cache_clear()
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert result.ttl_seconds == 7 * 86400
    assert client.blob.signed_args["expiration"] == timedelta(days=7)


async def test_emit_passes_v4_signing_version() -> None:
    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert client.blob.signed_args["version"] == "v4"
    assert client.blob.signed_args["method"] == "GET"


async def test_emit_markdown_bytes_count_matches_content() -> None:
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    uploaded = client.blob.uploaded
    assert uploaded is not None
    assert result.markdown_bytes == len(uploaded[0])


# ---------------------------------------------------------------------------
# Round-2 regression tests (PR #70 review findings)
# ---------------------------------------------------------------------------


async def test_emit_passes_if_generation_match_zero_to_block_clobber() -> None:
    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).emit(_recipe())
    # if_generation_match=0 → GCS rejects with 412 if the blob already exists.
    assert client.blob.if_generation_match == 0


async def test_emit_translates_precondition_failed_to_typed_error() -> None:
    from chaoslab_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class PreconditionFailed(Exception):  # noqa: N818 — name matches GCS SDK class
        pass

    class _RejectingBlob:
        def upload_from_string(
            self, content: bytes, content_type: str, if_generation_match: int = 0
        ) -> None:
            raise PreconditionFailed("412")

        def generate_signed_url(self, **kwargs: Any) -> str:  # pragma: no cover
            return "https://storage.googleapis.com/x.md?X-Goog-Signature=z"

    class _Bucket:
        def blob(self, name: str) -> Any:
            return _RejectingBlob()

        def exists(self) -> bool:
            return True

    class _Client:
        def bucket(self, name: str) -> Any:
            return _Bucket()

    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=_Client()).emit(_recipe())


async def test_emit_translates_generic_upload_failure_to_emitter_error() -> None:
    from chaoslab_agent.patcher.markdown_emitter import MarkdownEmitterError

    class _BoomBlob:
        def upload_from_string(
            self, content: bytes, content_type: str, if_generation_match: int = 0
        ) -> None:
            raise RuntimeError("network unreachable")

        def generate_signed_url(self, **kwargs: Any) -> str:  # pragma: no cover
            return "https://storage.googleapis.com/x.md"

    class _Bucket:
        def blob(self, name: str) -> Any:
            return _BoomBlob()

        def exists(self) -> bool:
            return True

    class _Client:
        def bucket(self, name: str) -> Any:
            return _Bucket()

    with pytest.raises(MarkdownEmitterError, match="network unreachable"):
        await MarkdownEmitter(storage_client=_Client()).emit(_recipe())


async def test_health_check_fails_when_bucket_does_not_exist() -> None:
    from chaoslab_agent.patcher.markdown_emitter import BucketNotConfiguredError

    class _MissingBucket:
        def blob(self, name: str) -> Any:  # pragma: no cover
            raise AssertionError("should not be reached")

        def exists(self) -> bool:
            return False

    class _Client:
        def bucket(self, name: str) -> Any:
            return _MissingBucket()

    with pytest.raises(BucketNotConfiguredError, match="does not exist"):
        await MarkdownEmitter(storage_client=_Client()).health_check()


async def test_health_check_translates_iam_error_to_typed_error() -> None:
    from chaoslab_agent.patcher.markdown_emitter import BucketNotConfiguredError

    class _ForbiddenBucket:
        def blob(self, name: str) -> Any:  # pragma: no cover
            raise AssertionError("should not be reached")

        def exists(self) -> bool:
            raise RuntimeError("403 Forbidden")

    class _Client:
        def bucket(self, name: str) -> Any:
            return _ForbiddenBucket()

    with pytest.raises(BucketNotConfiguredError, match="403"):
        await MarkdownEmitter(storage_client=_Client()).health_check()


async def test_health_check_passes_on_existing_bucket() -> None:
    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).health_check()


# ---------------------------------------------------------------------------
# EmitResult schema invariants (no bypass via direct construction)
# ---------------------------------------------------------------------------


def test_emit_result_rejects_non_https_signed_url_at_field_validator() -> None:
    from pydantic import ValidationError

    # Bypasses the build factory — the field_validator must still enforce.
    with pytest.raises(ValidationError, match="https://"):
        EmitResult(
            recipe_id="recipe_abc123def456",
            gcs_uri="gs://chaoslab-recipes/recipe_abc123def456.md",
            signed_url="http://insecure.example/recipe.md",
            markdown_bytes=10,
            ttl_seconds=604800,
        )


def test_emit_result_rejects_signed_url_not_pointed_at_googleapis() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match=r"storage\.googleapis\.com"):
        EmitResult(
            recipe_id="recipe_abc123def456",
            gcs_uri="gs://chaoslab-recipes/recipe_abc123def456.md",
            signed_url="https://attacker.example/forged.md",
            markdown_bytes=10,
            ttl_seconds=604800,
        )


def test_emit_result_rejects_ttl_above_seven_days() -> None:
    from pydantic import ValidationError

    # v4 SA-keyed signing caps at 7 days = 604800 seconds.
    with pytest.raises(ValidationError):
        EmitResult(
            recipe_id="recipe_abc123def456",
            gcs_uri="gs://chaoslab-recipes/recipe_abc123def456.md",
            signed_url=(
                "https://storage.googleapis.com/chaoslab-recipes/recipe.md?X-Goog-Signature=z"
            ),
            markdown_bytes=10,
            ttl_seconds=604801,
        )


def test_emit_result_rejects_invalid_gcs_uri_shape() -> None:
    from pydantic import ValidationError

    for bad in [
        "s3://chaoslab-recipes/recipe.md",
        "gs://Chaoslab-Recipes/recipe.md",  # uppercase rejected
        "gs://chaoslab-recipes/recipe.txt",  # missing .md
        "gs://chaoslab-recipes/",  # missing object name
    ]:
        with pytest.raises(ValidationError):
            EmitResult(
                recipe_id="recipe_abc123def456",
                gcs_uri=bad,
                signed_url=("https://storage.googleapis.com/x.md?X-Goog-Signature=z"),
                markdown_bytes=10,
                ttl_seconds=604800,
            )


# ---------------------------------------------------------------------------
# Round-3 regression tests (PR #70 post-merge verification findings)
# ---------------------------------------------------------------------------


async def test_health_check_distinguishes_bucket_missing_from_unreachable() -> None:
    """Operators must be able to grep Cloud Logging by error class."""
    from chaoslab_agent.patcher.markdown_emitter import (
        BucketMissingError,
        BucketUnreachableError,
    )

    class _MissingBucket:
        def blob(self, name: str) -> Any:  # pragma: no cover
            raise AssertionError("should not be reached")

        def exists(self) -> bool:
            return False

    class _MissingClient:
        def bucket(self, name: str) -> Any:
            return _MissingBucket()

    class _UnreachableBucket:
        def blob(self, name: str) -> Any:  # pragma: no cover
            raise AssertionError("should not be reached")

        def exists(self) -> bool:
            raise RuntimeError("403 Forbidden")

    class _UnreachableClient:
        def bucket(self, name: str) -> Any:
            return _UnreachableBucket()

    with pytest.raises(BucketMissingError):
        await MarkdownEmitter(storage_client=_MissingClient()).health_check()
    with pytest.raises(BucketUnreachableError):
        await MarkdownEmitter(storage_client=_UnreachableClient()).health_check()


async def test_emit_translates_conflict_alias_to_recipe_already_exists() -> None:
    """The `Conflict` SDK alias must also map to the typed error."""
    from chaoslab_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class Conflict(Exception):  # noqa: N818 — name matches GCS SDK class
        pass

    class _ConflictBlob:
        def upload_from_string(
            self, data: bytes, content_type: str, if_generation_match: int = 0
        ) -> None:
            raise Conflict("conflict")

        def generate_signed_url(self, **kwargs: Any) -> str:  # pragma: no cover
            return "https://storage.googleapis.com/x.md?X-Goog-Signature=z"

    class _Bucket2:
        def blob(self, name: str) -> Any:
            return _ConflictBlob()

        def exists(self) -> bool:
            return True

    class _Client:
        def bucket(self, name: str) -> Any:
            return _Bucket2()

    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=_Client()).emit(_recipe())


async def test_emit_detects_precondition_via_status_code_attribute() -> None:
    """SDK variants put 412 on .status_code rather than .code."""
    from chaoslab_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class _ResponseLike:
        status_code = 412

    class _StatusCodeError(Exception):
        response = _ResponseLike()

    class _Blob3:
        def upload_from_string(
            self, data: bytes, content_type: str, if_generation_match: int = 0
        ) -> None:
            raise _StatusCodeError("412 via response.status_code")

        def generate_signed_url(self, **kwargs: Any) -> str:  # pragma: no cover
            return "https://storage.googleapis.com/x.md?X-Goog-Signature=z"

    class _Bucket3:
        def blob(self, name: str) -> Any:
            return _Blob3()

        def exists(self) -> bool:
            return True

    class _Client3:
        def bucket(self, name: str) -> Any:
            return _Bucket3()

    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=_Client3()).emit(_recipe())


async def test_emit_recipe_already_exists_is_not_wrapped_in_emitter_error() -> None:
    """Bare re-raise of RecipeAlreadyExistsError must not turn into MarkdownEmitterError."""
    from chaoslab_agent.patcher.markdown_emitter import (
        MarkdownEmitterError,
        RecipeAlreadyExistsError,
    )

    class PreconditionFailed(Exception):  # noqa: N818
        pass

    class _Blob4:
        def upload_from_string(
            self, data: bytes, content_type: str, if_generation_match: int = 0
        ) -> None:
            raise PreconditionFailed("412")

        def generate_signed_url(self, **kwargs: Any) -> str:  # pragma: no cover
            return "https://storage.googleapis.com/x.md?X-Goog-Signature=z"

    class _Bucket4:
        def blob(self, name: str) -> Any:
            return _Blob4()

        def exists(self) -> bool:
            return True

    class _Client4:
        def bucket(self, name: str) -> Any:
            return _Bucket4()

    with pytest.raises(RecipeAlreadyExistsError) as exc_info:
        await MarkdownEmitter(storage_client=_Client4()).emit(_recipe())
    # The exception must be exactly RecipeAlreadyExistsError, not a parent
    # class — otherwise a refactor dropping the bare re-raise would
    # silently double-wrap it.
    assert type(exc_info.value) is RecipeAlreadyExistsError
    # MarkdownEmitterError is the parent — issubclass holds — but the
    # `from exc` chain must surface the original PreconditionFailed.
    assert isinstance(exc_info.value, MarkdownEmitterError)
    assert isinstance(exc_info.value.__cause__, PreconditionFailed)


async def test_emit_generic_failure_preserves_cause_chain() -> None:
    from chaoslab_agent.patcher.markdown_emitter import MarkdownEmitterError

    class _NetworkBoom(Exception):  # noqa: N818 - test stub, mimics 5xx-class names
        pass

    class _Blob5:
        def upload_from_string(
            self, data: bytes, content_type: str, if_generation_match: int = 0
        ) -> None:
            raise _NetworkBoom("DNS resolve failed")

        def generate_signed_url(self, **kwargs: Any) -> str:  # pragma: no cover
            return "https://storage.googleapis.com/x.md?X-Goog-Signature=z"

    class _Bucket5:
        def blob(self, name: str) -> Any:
            return _Blob5()

        def exists(self) -> bool:
            return True

    class _Client5:
        def bucket(self, name: str) -> Any:
            return _Bucket5()

    with pytest.raises(MarkdownEmitterError) as exc_info:
        await MarkdownEmitter(storage_client=_Client5()).emit(_recipe())
    assert isinstance(exc_info.value.__cause__, _NetworkBoom)


@pytest.mark.parametrize(
    "bad_uri",
    [
        "s3://chaoslab-recipes/recipe.md",
        "gs://Chaoslab-Recipes/recipe.md",
        "gs://chaoslab-recipes/recipe.txt",
        "gs://chaoslab-recipes/",
    ],
)
def test_emit_result_rejects_invalid_gcs_uri_shape_parametrized(bad_uri: str) -> None:
    """Round-2 used a for-loop; round-3 parametrizes so each bad URI reports independently."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EmitResult(
            recipe_id="recipe_abc123def456",
            gcs_uri=bad_uri,
            signed_url=("https://storage.googleapis.com/x.md?X-Goog-Signature=z"),
            markdown_bytes=10,
            ttl_seconds=604800,
        )
