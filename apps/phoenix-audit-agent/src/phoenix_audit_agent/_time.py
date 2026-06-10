"""Canonical UTC timestamp helpers — ONE format for every stored record.

Three per-story `_iso_now()` copies produced three incompatible shapes
(`...Z`, `...+00:00`, `...+00:00` with microseconds). Firestore ordering and
the schedule due-comparison are string-based, so format drift is an ordering
bug. Every writer goes through `utc_now_iso()`; every reader that must
compare goes through `parse_iso()` (tolerates both legacy suffixes).

Exception: `phoenix_tools.write_annotation` keeps its own millisecond-`Z`
stamp — that shape is the Phoenix annotation wire contract, enforced by a
field validator there, not a registry timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """RFC-3339 UTC, second precision, `+00:00` offset."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def parse_iso(ts: str) -> datetime:
    """Parse either legacy form (`Z` or `+00:00` suffix) to an aware datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


__all__ = ["parse_iso", "utc_now_iso"]
