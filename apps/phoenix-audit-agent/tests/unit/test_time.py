"""Canonical UTC timestamp helpers (`phoenix_audit_agent._time`).

One format for every record the registry stores, orders, and compares —
the per-story `_iso_now()` copies produced three incompatible shapes
(`Z` / `+00:00` / microseconds) that broke lexicographic ordering.
"""

from __future__ import annotations

from datetime import UTC, datetime

from phoenix_audit_agent._time import parse_iso, utc_now_iso


def test_utc_now_iso_is_offset_form_second_precision() -> None:
    ts = utc_now_iso()
    assert ts.endswith("+00:00"), ts
    assert "." not in ts, f"microseconds leaked into canonical timestamp: {ts}"
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_parse_iso_accepts_both_legacy_forms() -> None:
    z = parse_iso("2026-06-10T00:00:00Z")
    offset = parse_iso("2026-06-10T00:00:00+00:00")
    assert z == offset == datetime(2026, 6, 10, tzinfo=UTC)


def test_parse_iso_round_trips_canonical_form() -> None:
    ts = utc_now_iso()
    assert parse_iso(ts).isoformat(timespec="seconds") == ts
