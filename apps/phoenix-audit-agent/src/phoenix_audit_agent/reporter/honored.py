"""phoenix_audit.honored detection (docs/header-convention.md).

The locked report warning claims the attribute was "absent from {N}
probe-response spans" — so {N} may only count response spans that were
actually read from Phoenix and found lacking. Transport failures (no
response span exists) and unreadable spans are excluded by the caller /
this module respectively.
"""

from __future__ import annotations

from typing import Any

import structlog

_log = structlog.get_logger(__name__)


async def span_honored(phoenix: Any, span_id: str, *, run_id: str) -> bool:
    """Read phoenix_audit.honored from the TARGET's Phoenix response span.

    Returns True only when the span was readable AND carries the attribute
    as boolean true. An unreadable span ALSO returns True (i.e. NOT counted
    as missing) — a Phoenix read failure must not inflate {N} in a signed
    artifact; it is logged instead.
    """
    try:
        span = await phoenix.spans.get_span(span_id)
    except Exception as fetch_err:
        _log.warning(
            "honored_span_fetch_failed",
            run_id=run_id,
            span_id=span_id,
            exc_type=type(fetch_err).__name__,
            error=str(fetch_err),
        )
        return True
    attributes = getattr(span, "attributes", None) or {}
    if isinstance(span, dict):  # phoenix client may return dict-shaped spans
        attributes = span.get("attributes") or attributes
    return bool(attributes.get("phoenix_audit.honored") is True)
