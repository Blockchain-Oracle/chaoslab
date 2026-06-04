"""Session-scoped OpenTelemetry setup for unit tests.

OpenTelemetry's global tracer provider can only be set ONCE per process,
so we install our in-memory exporter at session start and clear it
between tests via the autouse fixture in `test_tools.py`.

This pattern lets every test capture spans via the same exporter
without fighting `set_tracer_provider`'s "no override" guard.
"""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


@pytest.fixture(scope="session")
def _session_exporter() -> InMemorySpanExporter:
    """Set the global tracer provider ONCE per test session."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


@pytest.fixture
def in_memory_spans(_session_exporter: InMemorySpanExporter) -> InMemorySpanExporter:
    """Return the session-scoped exporter, freshly cleared for THIS test."""
    _session_exporter.clear()
    return _session_exporter
