"""Unit tests for MarkdownEmitter — stubs the GCS boundary."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.clustering import FailureClusterSet
from phoenix_audit_agent.patcher.markdown_emitter import (
    EmitResult,
    MarkdownEmitter,
    StorageClient,
    _Blob,
    _Bucket,
)
from phoenix_audit_agent.patcher.recipe import (
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
        # `uploaded` = FIRST upload (the .md artifact); `uploads` = all of
        # them — story-9.17 adds a {recipe_id}.json sidecar second.
        self.uploaded: tuple[bytes, str] | None = None
        self.uploads: list[tuple[bytes, str]] = []
        self.signed_args: dict[str, Any] = {}
        self.if_generation_match: int | None = None

    def upload_from_string(
        self,
        data: bytes,
        content_type: str,
        if_generation_match: int = 0,
    ) -> None:
        if self.uploaded is None:
            self.uploaded = (data, content_type)
            self.if_generation_match = if_generation_match
        self.uploads.append((data, content_type))

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
            "&X-Goog-Credential=fake-sa%40phoenix-audit.iam.gserviceaccount.com"
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
    assert "chaoslab-recipes" in client.bucket_names
    # .md first (the regulator-facing artifact), .json sidecar second
    # (story-9.17 — rehydrates the structured recipe for MR filing).
    assert client.bucket_obj.blob_names == [
        "recipe_abc123def456.md",
        "recipe_abc123def456.json",
    ]


async def test_emit_uploads_with_markdown_content_type() -> None:
    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).emit(_recipe())
    uploaded = client.blob.uploaded
    assert uploaded is not None
    content, content_type = uploaded
    assert content_type == "text/markdown; charset=utf-8"
    assert content.startswith(b"# PhoenixAudit Hardening Recipe")


async def test_emit_uploads_structured_recipe_sidecar() -> None:
    """story-9.17: the JSON sidecar must rehydrate to the SAME recipe."""
    from phoenix_audit_agent.patcher import HardeningRecipe

    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert len(client.blob.uploads) == 2
    data, content_type = client.blob.uploads[1]
    assert content_type == "application/json"
    rehydrated = HardeningRecipe.model_validate_json(data)
    assert rehydrated.recipe_id == "recipe_abc123def456"


async def test_emit_sidecar_failure_contained(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sidecar outage only disables later MR filing — never fails the audit."""
    client = _RecordingClient()
    emitter = MarkdownEmitter(storage_client=client)

    def boom(blob_name: str, content: bytes) -> None:
        raise RuntimeError("gcs hiccup")

    monkeypatch.setattr(emitter, "_upload_sidecar", boom)
    result = await emitter.emit(_recipe())
    assert isinstance(result, EmitResult)


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
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

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
    from phoenix_audit_agent.patcher.markdown_emitter import MarkdownEmitterError

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
    """Bucket-truly-absent case → BucketMissingError (NOT the generic probe base).
    Operator response is 'fix terraform / Secret Manager', distinct from IAM blip."""
    from phoenix_audit_agent.patcher.markdown_emitter import BucketMissingError

    class _MissingBucket:
        def blob(self, name: str) -> Any:  # pragma: no cover
            raise AssertionError("should not be reached")

        def exists(self) -> bool:
            return False

    class _Client:
        def bucket(self, name: str) -> Any:
            return _MissingBucket()

    with pytest.raises(BucketMissingError, match="does not exist"):
        await MarkdownEmitter(storage_client=_Client()).health_check()


async def test_health_check_translates_iam_error_to_typed_error() -> None:
    """IAM/network failure case → BucketUnreachableError (sibling, NOT subclass of
    BucketMissingError). Operator response is IAM-check / retry, distinct from
    config bug — code-reviewer #3 flagged the prior collapse."""
    from phoenix_audit_agent.patcher.markdown_emitter import BucketUnreachableError

    class _ForbiddenBucket:
        def blob(self, name: str) -> Any:  # pragma: no cover
            raise AssertionError("should not be reached")

        def exists(self) -> bool:
            raise RuntimeError("403 Forbidden")

    class _Client:
        def bucket(self, name: str) -> Any:
            return _ForbiddenBucket()

    with pytest.raises(BucketUnreachableError, match="403"):
        await MarkdownEmitter(storage_client=_Client()).health_check()


async def test_bucket_error_subclasses_share_neutral_probe_base() -> None:
    """Taxonomy lock: BucketMissingError + BucketUnreachableError are SIBLINGS
    under BucketProbeError — NOT one descending from the other. Catching the
    neutral base catches both; catching a subclass catches only that operator
    response. Prevents the prior 'flaky IAM masked as config bug' collapse."""
    from phoenix_audit_agent.patcher.markdown_emitter import (
        BucketMissingError,
        BucketProbeError,
        BucketUnreachableError,
    )

    assert issubclass(BucketMissingError, BucketProbeError)
    assert issubclass(BucketUnreachableError, BucketProbeError)
    # Neither subclass is a parent of the other — they're siblings.
    assert not issubclass(BucketMissingError, BucketUnreachableError)
    assert not issubclass(BucketUnreachableError, BucketMissingError)


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
    from phoenix_audit_agent.patcher.markdown_emitter import (
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
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

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
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

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
    from phoenix_audit_agent.patcher.markdown_emitter import (
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
    from phoenix_audit_agent.patcher.markdown_emitter import MarkdownEmitterError

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


# ---------------------------------------------------------------------------
# Round-3 (silent-failure-hunter I-1): _is_already_exists_error must catch
# gRPC FailedPrecondition + string-shaped HTTP codes + grpc.StatusCode enum.
# Each shape gets its own test so a future SDK-version drift fails one not all.
# ---------------------------------------------------------------------------


def _make_emit_client_raising(exc: BaseException) -> Any:
    """Build a minimal storage-client stub that raises `exc` on upload_from_string.
    Used to exercise the upload-path error translation in _is_already_exists_error."""

    class _Blob:
        def upload_from_string(
            self, data: bytes, content_type: str, if_generation_match: int = 0
        ) -> None:
            raise exc

        def generate_signed_url(self, **kwargs: Any) -> str:  # pragma: no cover
            return "https://storage.googleapis.com/x.md?X-Goog-Signature=z"

    class _Bucket:
        def blob(self, name: str) -> Any:
            return _Blob()

        def exists(self) -> bool:
            return True

    class _Client:
        def bucket(self, name: str) -> Any:
            return _Bucket()

    return _Client()


async def test_emit_translates_grpc_failed_precondition_class_name() -> None:
    """gRPC SDK variant uses `FailedPrecondition` class name (not HTTP)."""
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class FailedPrecondition(Exception):  # noqa: N818 — name matches gRPC SDK class
        pass

    client = _make_emit_client_raising(FailedPrecondition("blob exists"))
    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=client).emit(_recipe())


async def test_emit_translates_string_shaped_412_code() -> None:
    """Some SDK versions stringify codes as '412 Precondition Failed' on `.code`."""
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class _StringCodedErr(Exception):  # noqa: N818
        def __init__(self) -> None:
            super().__init__("blob exists")
            self.code = "412 Precondition Failed"

    client = _make_emit_client_raising(_StringCodedErr())
    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=client).emit(_recipe())


async def test_emit_translates_string_shaped_409_conflict_code() -> None:
    """Some SDK versions emit '409 Conflict' on `.code` for if_generation_match."""
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class _StringCoded409(Exception):  # noqa: N818
        def __init__(self) -> None:
            super().__init__("blob exists")
            self.code = "409 Conflict"

    client = _make_emit_client_raising(_StringCoded409())
    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=client).emit(_recipe())


async def test_emit_translates_grpc_status_enum_via_name_attribute() -> None:
    """gRPC StatusCode enum on `.code` exposes `.name == 'FAILED_PRECONDITION'`.
    Locks the `getattr(candidate, 'name', None)` branch in _is_already_exists_error."""
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class _GrpcStatusEnum:
        name = "FAILED_PRECONDITION"

    class _GrpcErr(Exception):  # noqa: N818
        def __init__(self) -> None:
            super().__init__("blob exists")
            self.code = _GrpcStatusEnum()

    client = _make_emit_client_raising(_GrpcErr())
    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=client).emit(_recipe())


async def test_emit_translates_grpc_already_exists_status_name() -> None:
    """ALREADY_EXISTS is the gRPC-native semantic match (Code 6)."""
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    class _GrpcAlreadyExists:
        name = "ALREADY_EXISTS"

    class _Err(Exception):  # noqa: N818
        def __init__(self) -> None:
            super().__init__("blob exists")
            self.grpc_status_code = _GrpcAlreadyExists()

    client = _make_emit_client_raising(_Err())
    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=client).emit(_recipe())


async def test_emit_leaves_unrelated_400_as_emitter_error() -> None:
    """A garden-variety 400 must NOT be translated to RecipeAlreadyExistsError —
    locks the False branch of _is_already_exists_error so a generic upload error
    doesn't masquerade as a clobber-refused signal."""
    from phoenix_audit_agent.patcher.markdown_emitter import (
        MarkdownEmitterError,
        RecipeAlreadyExistsError,
    )

    class _BadRequest(Exception):  # noqa: N818
        def __init__(self) -> None:
            super().__init__("bad request")
            self.code = 400

    client = _make_emit_client_raising(_BadRequest())
    with pytest.raises(MarkdownEmitterError) as exc_info:
        await MarkdownEmitter(storage_client=client).emit(_recipe())
    # Specifically NOT the precondition subclass.
    assert not isinstance(exc_info.value, RecipeAlreadyExistsError)


# Skipif-guarded test that exercises the REAL google-api-core PreconditionFailed
# class — if the SDK is installed in this venv, raise an actual instance to
# prove `isinstance`-vs-name match parity. Otherwise the test is skipped, and
# the stand-in tests above provide name-match coverage only.
try:
    from google.api_core.exceptions import (
        PreconditionFailed as _RealPreconditionFailed,
    )

    _has_google_api_core = True
except ImportError:  # pragma: no cover — depends on venv install state
    _has_google_api_core = False


@pytest.mark.skipif(not _has_google_api_core, reason="google-api-core not installed")
async def test_emit_translates_real_google_api_core_precondition_failed() -> None:
    """Locks the prod path: a REAL `google.api_core.exceptions.PreconditionFailed`
    instance maps to RecipeAlreadyExistsError. Test-quality-reviewer #3 — proves
    the class-name match isn't just hitting our local stand-ins."""
    from phoenix_audit_agent.patcher.markdown_emitter import RecipeAlreadyExistsError

    client = _make_emit_client_raising(_RealPreconditionFailed("blob exists"))
    with pytest.raises(RecipeAlreadyExistsError):
        await MarkdownEmitter(storage_client=client).emit(_recipe())


# ---------------------------------------------------------------------------
# Regression — run_d9bcbf208b2c (2026-06-12 production audit)
# E1: Cloud Run's compute-engine credentials lack `sign_bytes`. The naive
# `blob.generate_signed_url(...)` raises `AttributeError("you need a private
# key to sign credentials")`. The shared `signed_get_url` helper routes
# around this via IAM signBlob — markdown_emitter must use that helper.
# ---------------------------------------------------------------------------


async def test_emit_routes_through_signed_get_url_helper_for_iam_signing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the blob's client carries token-only credentials (no sign_bytes,
    like Cloud Run's compute-engine creds), the helper must call IAM signBlob
    — NOT the raw generate_signed_url that crashes with AttributeError.

    This test simulates Cloud Run by giving the recording client a fake
    `_credentials` object with no `sign_bytes`, then asserts the helper's
    IAM-signing branch fires (kwargs contain `service_account_email` +
    `access_token`).
    """

    # Patch the IAM-signing-credential factory to return a deterministic stub
    # so we don't reach the metadata server in unit tests.
    class _StubIamCreds:
        valid = True
        token = "stub-access-token-xyz"
        service_account_email = "chaoslab-runtime@phoenix-audit.iam.gserviceaccount.com"

    import phoenix_audit_agent.storage.gcs as gcs_module

    def _stub_iam_signing_credentials() -> _StubIamCreds:
        return _StubIamCreds()

    monkeypatch.setattr(gcs_module, "_iam_signing_credentials", _stub_iam_signing_credentials)

    captured_kwargs: dict[str, Any] = {}

    class _TokenOnlyCreds:
        """Mimics Cloud Run's compute_engine.Credentials — token only, no signer."""

        service_account_email = "chaoslab-runtime@phoenix-audit.iam.gserviceaccount.com"

    class _TokenOnlyClient:
        _credentials = _TokenOnlyCreds()

    class _CloudRunBlob(_Blob):
        client = _TokenOnlyClient()

        def upload_from_string(
            self,
            data: bytes,
            content_type: str,
            if_generation_match: int = 0,
        ) -> None:
            pass

        def generate_signed_url(self, **kwargs: Any) -> str:
            captured_kwargs.update(kwargs)
            return "https://storage.googleapis.com/chaoslab-recipes/x.md?X-Goog-Signature=z"

    class _CloudRunBucket(_Bucket):
        def blob(self, name: str) -> _CloudRunBlob:
            return _CloudRunBlob()

        def exists(self) -> bool:
            return True

    class _CloudRunStorage(StorageClient):
        def bucket(self, name: str) -> _CloudRunBucket:
            return _CloudRunBucket()

    result = await MarkdownEmitter(storage_client=_CloudRunStorage()).emit(_recipe())
    assert isinstance(result, EmitResult)
    # The contract: when creds lack sign_bytes, the helper MUST forward
    # IAM-signing parameters to generate_signed_url so signing happens via
    # the IAM signBlob API instead of crashing on the private-key check.
    assert captured_kwargs.get("service_account_email") == (
        "chaoslab-runtime@phoenix-audit.iam.gserviceaccount.com"
    )
    assert captured_kwargs.get("access_token") == "stub-access-token-xyz"
    assert captured_kwargs.get("version") == "v4"
    assert captured_kwargs.get("method") == "GET"


async def test_emit_skips_iam_signing_when_credentials_have_sign_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative-branch lock: when the blob's client carries credentials that
    DO expose `sign_bytes` (key-file / impersonated SA / local dev), the
    helper takes the direct path — IAM kwargs MUST NOT be forwarded and
    `_iam_signing_credentials` MUST NOT be invoked. A refactor that always
    forwards IAM kwargs would pass the positive test but break local dev.
    """
    iam_calls = 0

    def _stub_iam_signing_credentials() -> Any:
        nonlocal iam_calls
        iam_calls += 1
        return None  # should never be reached on this branch

    import phoenix_audit_agent.storage.gcs as gcs_module

    monkeypatch.setattr(gcs_module, "_iam_signing_credentials", _stub_iam_signing_credentials)

    captured_kwargs: dict[str, Any] = {}

    class _KeyfileCreds:
        """Mimics SA-keyfile / impersonated creds — has a signer."""

        service_account_email = "fake-sa@phoenix-audit.iam.gserviceaccount.com"

        def sign_bytes(self, _data: bytes) -> bytes:
            return b"stub-signature"

    class _KeyfileClient:
        _credentials = _KeyfileCreds()

    class _KeyfileBlob(_Blob):
        client = _KeyfileClient()

        def upload_from_string(
            self,
            data: bytes,
            content_type: str,
            if_generation_match: int = 0,
        ) -> None:
            pass

        def generate_signed_url(self, **kwargs: Any) -> str:
            captured_kwargs.update(kwargs)
            return "https://storage.googleapis.com/chaoslab-recipes/x.md?X-Goog-Signature=z"

    class _KeyfileBucket(_Bucket):
        def blob(self, name: str) -> _KeyfileBlob:
            return _KeyfileBlob()

        def exists(self) -> bool:
            return True

    class _KeyfileStorage(StorageClient):
        def bucket(self, name: str) -> _KeyfileBucket:
            return _KeyfileBucket()

    result = await MarkdownEmitter(storage_client=_KeyfileStorage()).emit(_recipe())
    assert isinstance(result, EmitResult)
    assert "service_account_email" not in captured_kwargs
    assert "access_token" not in captured_kwargs
    assert iam_calls == 0
    assert captured_kwargs.get("version") == "v4"
    assert captured_kwargs.get("method") == "GET"
