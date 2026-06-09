"""Shared fixtures for Judge rubric tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chaoslab_agent.judge.rubrics._base import PhoenixClient, _SpansNamespace

# Canonical 16-hex-char span id; satisfies RubricInput's pattern check.
SPAN_ID = "0123456789abcdef"


@dataclass
class FakeSpan:
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time_ns: int = 0
    end_time_ns: int = 0


class FakeSpansClient(_SpansNamespace):
    def __init__(self, span: FakeSpan) -> None:
        self._span = span

    async def get_span(self, span_id: str) -> FakeSpan:
        return self._span


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
    "SPAN_ID",
    "FakePhoenixClient",
    "FakeSpan",
    "FakeSpansClient",
    "StubVerdict",
    "stub_evaluator",
]
