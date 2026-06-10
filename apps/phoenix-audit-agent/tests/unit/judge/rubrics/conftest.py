"""Shared fixtures for Judge rubric tests.

Evidence-chain repair (2026-06-10): rubrics no longer fetch from Phoenix —
judge_phase prefetches the probe's whole trace once and hands the spans in
via ``RubricInput.spans``. These helpers build that prefetched shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.rubrics._base import RubricInput
from phoenix_audit_agent.phoenix_tools.span_fetch import FetchedSpan

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
    """Attribute holder for one span of the prefetched trace."""

    attributes: dict[str, Any] = field(default_factory=dict)
    start_time_ns: int = 0
    end_time_ns: int = 0
    parent_id: str = ""  # "" => root


def to_fetched(span: FakeSpan, *, span_id: str = SPAN_ID) -> FetchedSpan:
    return FetchedSpan(
        span_id=span_id,
        trace_id=TRACE_ID,
        parent_id=span.parent_id,
        attributes=dict(span.attributes),
        start_time_ns=span.start_time_ns,
        end_time_ns=span.end_time_ns,
    )


def make_input(
    fault_class: str,
    *spans: FakeSpan,
    attack_payload: str | None = None,
    original_user_message: str | None = None,
    client_duration_ms: float | None = None,
) -> RubricInput:
    """RubricInput over a prefetched trace (first span is the root)."""
    fetched = [
        to_fetched(s, span_id=SPAN_ID if i == 0 else f"{i:016x}") for i, s in enumerate(spans)
    ]
    return RubricInput(
        span_id=SPAN_ID,
        trace_id=TRACE_ID,
        fault_class=fault_class,  # ty: ignore[invalid-argument-type]
        spans=fetched,
        attack_payload=attack_payload,
        original_user_message=original_user_message,
        client_duration_ms=client_duration_ms,
    )


def child(attributes: dict[str, Any], **kw: Any) -> FakeSpan:
    return FakeSpan(attributes=attributes, parent_id=SPAN_ID, **kw)


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
    "FakeSpan",
    "StubVerdict",
    "child",
    "make_input",
    "stub_evaluator",
    "to_fetched",
]
