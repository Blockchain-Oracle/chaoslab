"""Shared fixtures for Judge rubric tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.rubrics._base import PhoenixClient, _SpansNamespace

# Canonical 16-hex-char span id; satisfies RubricInput's pattern check.
SPAN_ID = "0123456789abcdef"
TRACE_ID = SPAN_ID * 2
PROJECT_ID = "target-agent"


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Wire the Vertex AI path so Settings() construction succeeds without
    # any real credential. F4 only reads LATENCY_SLA_MS; the judge LLM is
    # stubbed out in every other rubric test.
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


@dataclass
class FakeSpan:
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time_ns: int = 0
    end_time_ns: int = 0


def _iso(ns: int) -> str:
    return "" if not ns else datetime.fromtimestamp(ns / 1e9, tz=UTC).isoformat()


class FakeSpansClient(_SpansNamespace):
    """Mirrors the REAL arize-phoenix-client 2.x AsyncSpans: only get_spans,
    returning dict-shaped v1.Span objects scoped to a trace."""

    def __init__(self, span: FakeSpan, *, span_id: str = SPAN_ID) -> None:
        self._span = span
        self._span_id = span_id

    async def get_spans(self, **kwargs: Any) -> list[dict[str, Any]]:
        return [
            {
                "name": "fake-span",
                "context": {"trace_id": TRACE_ID, "span_id": self._span_id},
                "span_kind": "AGENT",
                "start_time": _iso(self._span.start_time_ns),
                "end_time": _iso(self._span.end_time_ns),
                "status_code": "OK",
                "parent_id": "aaaabbbbccccdddd",
                "attributes": dict(self._span.attributes),
            }
        ]


class FakePhoenixClient(PhoenixClient):
    # Explicit Protocol inheritance so ty accepts the fake at every
    # RubricInput construction site.
    spans: _SpansNamespace

    def __init__(self, span: FakeSpan) -> None:
        self.spans = FakeSpansClient(span)


@dataclass
class StubVerdict:
    label: str
    explanation: str | None = None


def stub_evaluator(verdict: StubVerdict, *, captured: list[dict[str, Any]] | None = None) -> Any:
    """Build a stand-in Phoenix evaluator that returns one Score per call.

    If `captured` is supplied, each payload passed to `async_evaluate` is
    appended so tests can assert exactly which keys the rubric forwarded.
    """

    class StubEvaluator:
        async def async_evaluate(self, payload: dict[str, Any]) -> list[StubVerdict]:
            if captured is not None:
                captured.append(payload)
            return [verdict]

    return StubEvaluator()


__all__ = [
    "PROJECT_ID",
    "SPAN_ID",
    "TRACE_ID",
    "FakePhoenixClient",
    "FakeSpan",
    "FakeSpansClient",
    "StubVerdict",
    "stub_evaluator",
]
