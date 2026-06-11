"""Story-9.15 — upload body parser + per-row validator.

Pure (no I/O). Consumed by `POST /datasets` to turn a base64-encoded JSONL or
CSV body into either a `list[FlatDatasetItem]` (happy path, fed straight to
the `PhoenixDatasetClient` wrapper) or an `UploadValidationError` that the
route maps onto a 422 with the BDD-locked shape:

- `parse_error: str | None` — whole-file failure (malformed JSON, CSV missing
  a required column, empty body, > 500 rows, non-base64 envelope).
- `row_errors: list[RowError]` — per-row failures (unknown fault_class,
  duplicate case_id, missing required field, prompt too long).

The two are mutually exclusive — `parse_error` set ⇒ `row_errors == []`,
and vice versa. The route relies on this partition for its 422 body.

The KNOWN_FAULT_CLASSES set is checked in `test_known_fault_classes_match_injector_canon`
against `injector.agent._FAULT_CLASSES`; a drift in either file fails the
test, so this list can never silently diverge from what the audit pipeline
will actually run.
"""

from __future__ import annotations

import base64
import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import ValidationError

from phoenix_audit_agent.injector.agent import _FAULT_CLASSES
from phoenix_audit_agent.phoenix_tools.dataset_client import FlatDatasetItem

# Mirror injector's canonical tuple — same content, set-typed for fast lookups
# in the row validator. The drift guard test pins these to equality.
KNOWN_FAULT_CLASSES: frozenset[str] = frozenset(_FAULT_CLASSES)

_REQUIRED_COLUMNS: tuple[str, ...] = ("case_id", "fault_class", "prompt", "expected", "source")
_MAX_ROWS = 500


@dataclass(frozen=True)
class RowError:
    row: int  # 1-indexed for operator-readable messages
    reason: str


@dataclass(frozen=True)
class UploadValidationError:
    """The 422 body shape. `parse_error` and `row_errors` are mutually exclusive."""

    parse_error: str | None = None
    row_errors: list[RowError] = field(default_factory=list)


def _decode(body_b64: bytes) -> str | None:
    """Strict base64 → text, or None on failure."""
    if not body_b64:
        return None
    try:
        raw = base64.b64decode(body_b64, validate=True)
    except (ValueError, Exception):
        return None
    try:
        return raw.decode("utf-8-sig")  # strips BOM if present
    except UnicodeDecodeError:
        return None


def _validate_row(row_idx: int, row: dict[str, Any]) -> FlatDatasetItem | RowError:
    """One pass per row: shape check, fault_class enum check, pydantic
    bounds. Returns either the validated item or a RowError naming the field."""
    # Normalise empty-string optional fields to None so pydantic optional rules pass.
    for opt in ("severity", "notes"):
        if row.get(opt) == "":
            row[opt] = None
    fc = row.get("fault_class")
    if fc not in KNOWN_FAULT_CLASSES:
        return RowError(row=row_idx, reason=f"unknown fault_class: {fc!r}")
    try:
        return FlatDatasetItem.model_validate(row)
    except ValidationError as ve:
        # Surface the first field error — a row with multiple issues gets fixed
        # one at a time; piling more on doesn't help the operator.
        e0 = ve.errors()[0]
        field_name = ".".join(str(p) for p in e0["loc"])
        return RowError(row=row_idx, reason=f"{field_name}: {e0['msg']}")


def _parse_jsonl(text: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Returns (rows, parse_error). One of them is always None."""
    rows: list[dict[str, Any]] = []
    for line_idx, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            return None, f"line {line_idx}: not valid JSON ({e.msg})"
        if not isinstance(obj, dict):
            return None, f"line {line_idx}: expected JSON object, got {type(obj).__name__}"
        rows.append(obj)
    return rows, None


def _parse_csv(text: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Returns (rows, parse_error). Missing required column → parse_error."""
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    missing = [c for c in _REQUIRED_COLUMNS if c not in header]
    if missing:
        return None, f"missing required columns: {', '.join(missing)}"
    return list(reader), None


def parse_and_validate(
    body_b64: bytes, *, body_format: Literal["jsonl", "csv"]
) -> tuple[list[FlatDatasetItem] | None, UploadValidationError | None]:
    """The entry point. Returns (items, None) on success or (None, err) on
    any validation failure. The two are mutually exclusive."""
    text = _decode(body_b64)
    if text is None:
        return None, UploadValidationError(parse_error="empty or undecodable body")
    if not text.strip():
        return None, UploadValidationError(parse_error="empty body")

    rows, parse_error = (_parse_jsonl if body_format == "jsonl" else _parse_csv)(text)
    if parse_error is not None:
        return None, UploadValidationError(parse_error=parse_error)
    assert rows is not None

    if len(rows) > _MAX_ROWS:
        return None, UploadValidationError(
            parse_error=f"too many rows: {len(rows)} (cap is {_MAX_ROWS})"
        )

    items: list[FlatDatasetItem] = []
    row_errors: list[RowError] = []
    seen_case_ids: dict[str, int] = {}

    for idx, row in enumerate(rows, start=1):
        case_id = row.get("case_id")
        if isinstance(case_id, str) and case_id in seen_case_ids:
            row_errors.append(
                RowError(
                    row=idx,
                    reason=f"duplicate case_id {case_id!r} (also on row {seen_case_ids[case_id]})",
                )
            )
            continue
        result = _validate_row(idx, row)
        if isinstance(result, RowError):
            row_errors.append(result)
        else:
            items.append(result)
            if isinstance(case_id, str):
                seen_case_ids[case_id] = idx

    if row_errors:
        return None, UploadValidationError(row_errors=row_errors)
    return items, None


__all__ = [
    "KNOWN_FAULT_CLASSES",
    "RowError",
    "UploadValidationError",
    "parse_and_validate",
]
