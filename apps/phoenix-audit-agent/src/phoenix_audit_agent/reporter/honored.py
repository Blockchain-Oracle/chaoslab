"""phoenix_audit.honored detection (docs/header-convention.md).

The locked report warning claims the attribute was "absent from {N}
probe-response spans" — so {N} may only count response spans that were
actually read from Phoenix and found lacking. Traces that could not be read
at all are reported separately ("unreadable") and disclosed in the report;
they never inflate {N} and never silently count as compliant.

Since the single-fetch judge refactor, the trace's spans arrive PREFETCHED
(judge_phase fetches once and shares them with the rubric); fetch-layer
failures are mapped to "unreadable" by the caller. This function only decides
honored/missing/unreadable from the spans it was handed.
"""

from __future__ import annotations

from typing import Any, Literal

import structlog

_log = structlog.get_logger(__name__)

HonoredStatus = Literal["honored", "missing", "unreadable"]


def span_honored(
    spans: list[Any],
    *,
    trace_id: str,
    run_id: str,
) -> HonoredStatus:
    """Read phoenix_audit.honored from the TARGET's root response span.

    "honored"    — root span present AND carries the attribute as boolean true.
    "missing"    — root span read, attribute absent/not-true (counts toward {N}).
    "unreadable" — the trace carried no root span; the response span cannot
                   be read, so it must not count as compliant OR as missing.
    """
    root = next((s for s in spans if getattr(s, "is_root", False)), None)
    if root is None:
        _log.warning(
            "honored_root_span_missing",
            run_id=run_id,
            trace_id=trace_id,
            span_count=len(spans),
        )
        return "unreadable"
    if root.attributes.get("phoenix_audit.honored") is True:
        return "honored"
    return "missing"


__all__ = ["HonoredStatus", "span_honored"]
