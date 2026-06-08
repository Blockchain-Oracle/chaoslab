"""Integration tests for the Phoenix `write_span_annotation` FunctionTool wrapper.

Offline path injects `FakeClient` to exercise the production wrapper body without
real HTTP. The `@pytest.mark.online` test hits the real Phoenix Cloud project and
is skipped unless PHOENIX_API_KEY + PHOENIX_TEST_SPAN_ID are both present.
"""

from __future__ import annotations

import inspect
import math
import os
import re
from collections.abc import Iterator

import httpx
import pytest
from pydantic import ValidationError

from chaoslab_agent.config import get_settings
from chaoslab_agent.errors import PhoenixAnnotationError


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Strip inherited env so Settings() is deterministic."""
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
        if key in {"ENVIRONMENT", "SERVICE_VERSION"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_API_KEY", "test-phoenix-key-DO-NOT-LEAK")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://phoenix.example.test/v1/traces")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# Valid OTel-shaped span_id used across tests (16 hex chars).
_SPAN_ID = "abcdef0123456789"


# --- Test fixtures: FakeClient that captures the annotation payload ---------


class _FakeSpans:
    """Test double for AsyncSpans. Records each `log_span_annotations` call."""

    def __init__(self, captured: dict, raises: Exception | None = None) -> None:
        self.captured = captured
        self.raises = raises
        self.captured.setdefault("call_count", 0)
        self.captured.setdefault("calls", [])

    async def log_span_annotations(self, *, span_annotations, sync: bool = False):
        if self.raises is not None:
            raise self.raises
        self.captured["call_count"] += 1
        # SpanAnnotationData is a TypedDict — store the dict-shaped payload.
        payload = [dict(a) for a in span_annotations]
        self.captured["calls"].append(payload)
        # Last-write also exposed under the legacy key for back-compat assertions.
        self.captured["annotations"] = payload
        return [{"id": "ann_001"}]


def _fake_client_factory(captured: dict, raises: Exception | None = None):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["api_key"] = kwargs.get("api_key")
            captured["base_url"] = kwargs.get("base_url")
            self.spans = _FakeSpans(captured, raises=raises)

    return FakeClient


# --- AnnotationResult contract ----------------------------------------------


def test_annotation_result_accepts_valid_payload() -> None:
    from chaoslab_agent.phoenix_tools.write_annotation import AnnotationResult

    result = AnnotationResult(
        status="ok",
        span_id=_SPAN_ID,
        annotation_name="chaoslab_cluster",
        annotation_identifier="chaoslab/0.0.0/default/abcdef0123456789",
        score=0.85,
        wrote_at="2026-06-08T12:00:00.123Z",
    )
    assert result.status == "ok"
    assert result.score == 0.85


@pytest.mark.parametrize("bad_score", [-0.1, 1.5, 2.0, -100])
def test_annotation_result_rejects_out_of_bounds_score(bad_score: float) -> None:
    """Pydantic gates `0.0 <= score <= 1.0` on construction."""
    from chaoslab_agent.phoenix_tools.write_annotation import AnnotationResult

    with pytest.raises(ValidationError, match=r"score"):
        AnnotationResult(
            status="ok",
            span_id=_SPAN_ID,
            annotation_name="chaoslab_cluster",
            annotation_identifier="x",
            score=bad_score,
            wrote_at="2026-06-08T12:00:00.123Z",
        )


def test_annotation_result_rejects_short_span_id() -> None:
    """`span_id` must be at least 8 chars — shape guard against truncated wire data."""
    from chaoslab_agent.phoenix_tools.write_annotation import AnnotationResult

    with pytest.raises(ValidationError, match=r"span_id"):
        AnnotationResult(
            status="ok",
            span_id="short",
            annotation_name="chaoslab_cluster",
            annotation_identifier="x",
            score=0.5,
            wrote_at="2026-06-08T12:00:00.123Z",
        )


def test_annotation_result_rejects_non_iso_wrote_at() -> None:
    """`wrote_at` validator catches non-RFC-3339-UTC strings."""
    from chaoslab_agent.phoenix_tools.write_annotation import AnnotationResult

    with pytest.raises(ValidationError, match=r"wrote_at"):
        AnnotationResult(
            status="ok",
            span_id=_SPAN_ID,
            annotation_name="chaoslab_cluster",
            annotation_identifier="x",
            score=0.5,
            wrote_at="not-an-iso-date",
        )


def test_iso_now_has_millisecond_precision() -> None:
    """Two `_iso_now()` calls in the same second still differ (millisecond precision)."""
    from chaoslab_agent.phoenix_tools.write_annotation import _iso_now

    # Pattern: 'YYYY-MM-DDTHH:MM:SS.mmmZ'
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", _iso_now())


# --- FunctionTool wiring -----------------------------------------------------


def test_phoenix_write_annotation_tool_is_a_function_tool() -> None:
    from google.adk.tools import FunctionTool

    from chaoslab_agent.phoenix_tools.write_annotation import phoenix_write_annotation_tool

    assert isinstance(phoenix_write_annotation_tool, FunctionTool)
    assert getattr(phoenix_write_annotation_tool.func, "__name__", None) == "write_span_annotation"


def test_write_span_annotation_body_is_within_adr_005_loc_budget() -> None:
    """ADR-005: wrapper body MUST be <= 30 significant LOC."""
    from chaoslab_agent.phoenix_tools.write_annotation import write_span_annotation

    src_lines = inspect.getsource(write_span_annotation).splitlines()
    significant = [
        line
        for line in src_lines
        if line.strip()
        and not line.strip().startswith("#")
        and not line.strip().startswith('"""')
        and not line.strip().startswith("'''")
    ]
    assert len(significant) <= 30, (
        f"write_span_annotation body has {len(significant)} significant LOC; "
        f"ADR-005 budget is 30. Extract helpers."
    )


# --- Happy path + identifier semantics --------------------------------------


async def test_wrapper_happy_path_returns_annotation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: SDK is called once with the correct payload + AnnotationResult returns."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    result = await mod.write_span_annotation(
        _SPAN_ID, 0.85, "tool returned 404", annotator="chaoslab_judge"
    )
    assert result.status == "ok"
    assert result.span_id == _SPAN_ID
    assert result.annotation_name == "chaoslab_cluster"
    assert result.score == 0.85
    assert captured["call_count"] == 1
    ann = captured["annotations"][0]
    assert ann["name"] == "chaoslab_cluster"
    assert ann["annotator_kind"] == "LLM"
    assert ann["span_id"] == _SPAN_ID
    assert ann["result"]["score"] == 0.85
    assert ann["result"]["explanation"] == "tool returned 404"
    assert captured["api_key"] == "test-phoenix-key-DO-NOT-LEAK"
    assert captured["base_url"] == "https://phoenix.example.test"


async def test_identifier_is_deterministic_and_uses_cluster_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`cluster_id` participates in the dedup identifier so multiple clusters coexist."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    result = await mod.write_span_annotation(_SPAN_ID, 0.5, "r", cluster_id="cluster_42")
    assert result.annotation_identifier == captured["annotations"][0]["identifier"]
    assert "cluster_42" in result.annotation_identifier
    assert result.annotation_identifier != ""


@pytest.mark.parametrize(
    "bad_cluster_id",
    ["evil/../other", "with space", "has:colon", "x" * 65, "", "path/traversal"],
)
async def test_wrapper_rejects_malformed_cluster_id_before_http(
    monkeypatch: pytest.MonkeyPatch, bad_cluster_id: str
) -> None:
    """`cluster_id` regex blocks shapes that would collide with other clusters' identifiers."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    with pytest.raises(PhoenixAnnotationError, match=r"cluster_id"):
        await mod.write_span_annotation(_SPAN_ID, 0.5, "reason", cluster_id=bad_cluster_id)
    assert captured.get("call_count", 0) == 0


async def test_two_distinct_cluster_ids_produce_distinct_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BLOCKER fix: two clusters on the same span must NOT silently overwrite each other."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    r1 = await mod.write_span_annotation(_SPAN_ID, 0.1, "r1", cluster_id="c1")
    r2 = await mod.write_span_annotation(_SPAN_ID, 0.9, "r2", cluster_id="c2")
    assert r1.annotation_identifier != r2.annotation_identifier
    assert captured["call_count"] == 2
    sent_identifiers = [c[0]["identifier"] for c in captured["calls"]]
    assert len(set(sent_identifiers)) == 2, sent_identifiers


@pytest.mark.parametrize(
    ("annotator", "expected_kind"),
    [("chaoslab_judge", "LLM"), ("human", "HUMAN"), ("code", "CODE")],
)
async def test_annotator_kind_mapping_per_caller_label(
    monkeypatch: pytest.MonkeyPatch, annotator: str, expected_kind: str
) -> None:
    """Caller-facing `annotator` label maps deterministically to Phoenix's annotator_kind enum."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    await mod.write_span_annotation(
        _SPAN_ID,
        0.5,
        "rat-test",
        annotator=annotator,  # ty: ignore[invalid-argument-type]
    )
    assert captured["annotations"][0]["annotator_kind"] == expected_kind


# --- Validation: input rejection (BEFORE HTTP) -------------------------------


@pytest.mark.parametrize("bad_score", [-0.1, 1.5, -1.0, math.nan, math.inf, -math.inf])
async def test_wrapper_rejects_out_of_bounds_score_before_http(
    monkeypatch: pytest.MonkeyPatch, bad_score: float
) -> None:
    """`score` out of [0,1] (incl. NaN/Inf) raises BEFORE any HTTP call."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    with pytest.raises(PhoenixAnnotationError, match=r"score out of bounds"):
        await mod.write_span_annotation(_SPAN_ID, bad_score, "non-empty reason")
    assert captured.get("call_count", 0) == 0


async def test_wrapper_rejects_empty_reason_before_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty `reason` raises BEFORE any HTTP call (literal "" and whitespace-only)."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    with pytest.raises(PhoenixAnnotationError, match=r"reason must be"):
        await mod.write_span_annotation(_SPAN_ID, 0.5, "")
    with pytest.raises(PhoenixAnnotationError, match=r"reason must be"):
        await mod.write_span_annotation(_SPAN_ID, 0.5, "   ")
    assert captured.get("call_count", 0) == 0


async def test_wrapper_rejects_reason_with_null_byte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reason with control chars (e.g. null byte) raises — Phoenix Postgres would reject."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    with pytest.raises(PhoenixAnnotationError, match=r"control characters"):
        await mod.write_span_annotation(_SPAN_ID, 0.5, "reason\x00with-null")
    assert captured.get("call_count", 0) == 0


async def test_wrapper_rejects_oversized_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reason longer than _MAX_REASON_LEN raises locally instead of failing server-side."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    huge = "a" * (mod._MAX_REASON_LEN + 1)
    with pytest.raises(PhoenixAnnotationError, match=r"reason too long"):
        await mod.write_span_annotation(_SPAN_ID, 0.5, huge)
    assert captured.get("call_count", 0) == 0


async def test_wrapper_rejects_unknown_annotator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown `annotator` raises with the offending value + allowed list."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    with pytest.raises(PhoenixAnnotationError, match=r"unknown annotator"):
        await mod.write_span_annotation(
            _SPAN_ID,
            0.5,
            "reason",
            annotator="alien",  # ty: ignore[invalid-argument-type]
        )
    assert captured.get("call_count", 0) == 0


@pytest.mark.parametrize("bad_span_id", ["short", "not-hex-12345678", "GGGGGGGG", "a" * 33, ""])
async def test_wrapper_rejects_non_hex_or_malformed_span_id(
    monkeypatch: pytest.MonkeyPatch, bad_span_id: str
) -> None:
    """`span_id` must be 8-32 hex chars (OTel SpanID shape)."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    with pytest.raises(PhoenixAnnotationError, match=r"hex chars"):
        await mod.write_span_annotation(bad_span_id, 0.5, "reason")
    assert captured.get("call_count", 0) == 0


# --- SDK / network error paths ----------------------------------------------


@pytest.mark.parametrize("status_code", [429, 500, 503])
async def test_wrapper_wraps_httpx_status_error_with_status_code(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    """`httpx.HTTPStatusError` surfaces with status code in the message (parity with S4.3)."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    response = httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://phoenix.example.test/v1/span_annotations"),
    )
    err = httpx.HTTPStatusError(
        f"status {status_code}", request=response.request, response=response
    )
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory({}, raises=err))

    with pytest.raises(PhoenixAnnotationError) as exc_info:
        await mod.write_span_annotation(_SPAN_ID, 0.5, "reason")
    msg = str(exc_info.value)
    assert _SPAN_ID in msg
    assert str(status_code) in msg
    assert "test-phoenix-key-DO-NOT-LEAK" not in msg


async def test_wrapper_sdk_exception_wraps_with_sanitized_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK exception (non-HTTPStatusError) → PhoenixAnnotationError; message scrubs the API key."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    err = RuntimeError("phoenix HTTP 500: api_key=test-phoenix-key-DO-NOT-LEAK leaked here")
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory({}, raises=err))

    with pytest.raises(PhoenixAnnotationError) as exc_info:
        await mod.write_span_annotation(_SPAN_ID, 0.5, "reason")
    msg = str(exc_info.value)
    assert "test-phoenix-key-DO-NOT-LEAK" not in msg
    assert "<redacted>" in msg
    assert _SPAN_ID in msg


async def test_wrapper_carries_service_version_in_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Annotation metadata carries `chaoslab_version` so server-side queries can filter."""
    from chaoslab_agent.phoenix_tools import write_annotation as mod

    monkeypatch.setenv("SERVICE_VERSION", "1.2.3-test")
    get_settings.cache_clear()
    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _fake_client_factory(captured))

    await mod.write_span_annotation(_SPAN_ID, 0.5, "reason")
    metadata = captured["annotations"][0]["metadata"]
    assert metadata.get("chaoslab_version") == "1.2.3-test"


# --- Second-line defense (helpers cannot be bypassed) -----------------------


def test_build_annotation_rejects_invalid_annotator_kind_directly() -> None:
    """`_build_annotation` second-line defense: callers that bypass _validate_inputs still fail."""
    from chaoslab_agent.config import get_settings as _gs
    from chaoslab_agent.phoenix_tools.write_annotation import _build_annotation

    _gs.cache_clear()
    settings = _gs()
    with pytest.raises(PhoenixAnnotationError, match=r"invalid annotator_kind"):
        _build_annotation(
            _SPAN_ID,
            "BOGUS",  # ty: ignore[invalid-argument-type]
            "auto",
            0.5,
            "reason",
            "ident",
            settings,
        )


def test_build_annotation_rejects_out_of_bounds_score_directly() -> None:
    """`_build_annotation` second-line defense for score bounds too."""
    from chaoslab_agent.config import get_settings as _gs
    from chaoslab_agent.phoenix_tools.write_annotation import _build_annotation

    _gs.cache_clear()
    settings = _gs()
    with pytest.raises(PhoenixAnnotationError, match=r"score out of bounds"):
        _build_annotation(_SPAN_ID, "LLM", "auto", 1.5, "reason", "ident", settings)


# --- Online (real Phoenix) --------------------------------------------------


@pytest.mark.online
async def test_real_phoenix_write_annotation_against_test_span() -> None:
    """Hit real Phoenix; skipped unless PHOENIX_API_KEY + PHOENIX_TEST_SPAN_ID are set."""
    real_key = os.environ.get("PHOENIX_API_KEY", "")
    test_span = os.environ.get("PHOENIX_TEST_SPAN_ID", "")
    if not real_key or real_key.startswith("test-") or not test_span:
        pytest.skip("PHOENIX_API_KEY / PHOENIX_TEST_SPAN_ID not set; online test skipped")

    from chaoslab_agent.phoenix_tools.write_annotation import write_span_annotation

    result = await write_span_annotation(test_span, 0.85, "rat-test")
    assert result.status == "ok"
    assert result.span_id == test_span
    assert re.match(r"^\d{4}-\d{2}-\d{2}T", result.wrote_at)
