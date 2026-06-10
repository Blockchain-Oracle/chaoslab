"""phoenix_audit.honored detection (docs/header-convention.md).

The locked report warning claims the attribute was "absent from {N}
probe-response spans" — so {N} may only count response spans that were
actually read from Phoenix and found lacking. Spans that could not be read
are reported separately ("unreadable") and disclosed in the report; they
never inflate {N} and never silently count as compliant.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx
import structlog

from phoenix_audit_agent.phoenix_tools.span_fetch import SpanNotFoundError, fetch_span

_log = structlog.get_logger(__name__)

HonoredStatus = Literal["honored", "missing", "unreadable"]


async def span_honored(
    phoenix: Any,
    *,
    span_id: str,
    trace_id: str,
    project_identifier: str,
    run_id: str,
) -> HonoredStatus:
    """Read phoenix_audit.honored from the TARGET's Phoenix response span.

    "honored"    — span read AND carries the attribute as boolean true.
    "missing"    — span read, attribute absent/not-true (counts toward {N}).
    "unreadable" — Phoenix fetch failed (network/HTTP/not-found); disclosed
                   in the report, excluded from {N}.

    Only fetch-layer failures map to "unreadable" — programmer errors
    (AttributeError, TypeError, ...) propagate; a broad catch here once
    converted a missing client method into "every target is compliant".
    """
    try:
        span = await fetch_span(
            phoenix,
            span_id=span_id,
            trace_id=trace_id,
            project_identifier=project_identifier,
        )
    except (SpanNotFoundError, httpx.HTTPError) as fetch_err:
        _log.warning(
            "honored_span_fetch_failed",
            run_id=run_id,
            span_id=span_id,
            trace_id=trace_id,
            exc_type=type(fetch_err).__name__,
            error=str(fetch_err),
        )
        return "unreadable"
    if span.attributes.get("phoenix_audit.honored") is True:
        return "honored"
    return "missing"
