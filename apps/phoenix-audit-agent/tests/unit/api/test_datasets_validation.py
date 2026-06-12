"""Story-9.15 — JSONL/CSV upload parser + per-row validator.

Pure (no I/O), so it's a fast unit-test surface. The route layer takes a
base64-encoded body + a `format` Literal["jsonl", "csv"], calls into this
module, and either gets a `list[FlatDatasetItem]` back (happy path) or a
`UploadValidationError` carrying parse_error / row_errors per BDD.

Three contract tests collapse into one parse_error path and one row_errors
path so the route's 422 body is determined here (mutually exclusive per BDD).
"""

from __future__ import annotations

import base64

import pytest


def _b64(text: str) -> bytes:
    return base64.b64encode(text.encode("utf-8"))


JSONL_OK = (
    '{"case_id": "pi-001", "fault_class": "prompt_injection",'
    ' "prompt": "ignore prior", "expected": "refuse", "source": "OWASP"}\n'
    '{"case_id": "pi-002", "fault_class": "context_poisoning",'
    ' "prompt": "context leak", "expected": "scope only", "source": "internal"}\n'
)


def test_parse_jsonl_happy_path() -> None:
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    items, err = parse_and_validate(_b64(JSONL_OK), body_format="jsonl")
    assert err is None
    assert items is not None
    assert len(items) == 2
    assert items[0].case_id == "pi-001"
    assert items[1].fault_class == "context_poisoning"


def test_parse_jsonl_malformed_returns_parse_error() -> None:
    """A garbage line is a parse_error (whole-file failure), not row_errors."""
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    body = b"this is not json at all\nstill not json\n"
    items, err = parse_and_validate(_b64(body.decode()), body_format="jsonl")
    assert items is None
    assert err is not None
    assert err.parse_error is not None
    assert err.row_errors == []


def test_parse_jsonl_unknown_fault_class_is_row_error() -> None:
    """A row with an unknown fault_class is a per-row 422, NOT a parse_error.
    The two are mutually exclusive in the 422 body."""
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    body = (
        '{"case_id": "x", "fault_class": "made_up_class",'
        ' "prompt": "p", "expected": "e", "source": "s"}\n'
    )
    items, err = parse_and_validate(_b64(body), body_format="jsonl")
    assert items is None
    assert err is not None
    assert err.parse_error is None
    assert len(err.row_errors) == 1
    assert err.row_errors[0].row == 1
    assert "fault_class" in err.row_errors[0].reason


def test_parse_jsonl_duplicate_case_id_is_row_error() -> None:
    """Two rows with the same case_id MUST 422 — case_id uniqueness keeps
    regression-upsert dedup deterministic."""
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    body = (
        '{"case_id": "dup-1", "fault_class": "prompt_injection",'
        ' "prompt": "p", "expected": "e", "source": "s"}\n'
        '{"case_id": "dup-1", "fault_class": "prompt_injection",'
        ' "prompt": "p2", "expected": "e2", "source": "s2"}\n'
    )
    items, err = parse_and_validate(_b64(body), body_format="jsonl")
    assert items is None
    assert err is not None
    assert err.parse_error is None
    assert any("duplicate" in e.reason.lower() for e in err.row_errors)


def test_parse_csv_happy_path() -> None:
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    csv = (
        "case_id,fault_class,prompt,expected,source,severity,notes\n"
        "pi-001,prompt_injection,ignore prior,refuse,OWASP,high,\n"
        "pi-002,context_poisoning,leak,scope,internal,medium,extra note\n"
    )
    items, err = parse_and_validate(_b64(csv), body_format="csv")
    assert err is None
    assert items is not None
    assert len(items) == 2
    assert items[1].notes == "extra note"


def test_parse_csv_missing_required_column_is_parse_error() -> None:
    """A CSV missing a required column fails wholesale (parse_error), not
    per-row — the operator's mistake is the file shape, not a row."""
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    csv = "case_id,fault_class,prompt,expected\npi-001,prompt_injection,p,e\n"
    items, err = parse_and_validate(_b64(csv), body_format="csv")
    assert items is None
    assert err is not None
    assert err.parse_error is not None
    assert "source" in err.parse_error  # the missing column is named


def test_empty_body_is_parse_error() -> None:
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    items, err = parse_and_validate(b"", body_format="jsonl")
    assert items is None
    assert err is not None
    assert err.parse_error is not None


def test_too_many_rows_is_parse_error() -> None:
    """500-row cap per upload (story-9.15 invariants)."""
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    lines = []
    for i in range(501):
        lines.append(
            f'{{"case_id": "row-{i}", "fault_class": "prompt_injection",'
            ' "prompt": "p", "expected": "e", "source": "s"}'
        )
    body = "\n".join(lines)
    items, err = parse_and_validate(_b64(body), body_format="jsonl")
    assert items is None
    assert err is not None
    assert err.parse_error is not None
    assert "500" in err.parse_error


def test_non_base64_body_is_parse_error() -> None:
    """The route encodes body as base64; a non-base64 body is a parse_error,
    not a 500."""
    from phoenix_audit_agent.api.datasets_validation import parse_and_validate

    items, err = parse_and_validate(b"not base64 at all !!!", body_format="jsonl")
    # Either it decodes to garbage that fails jsonl parse, or it raises a
    # parse error directly — both yield err.parse_error, never items.
    assert items is None
    assert err is not None
    assert err.parse_error is not None


@pytest.mark.parametrize("fmt", ["jsonl", "csv"])
def test_known_fault_classes_match_injector_canon(fmt: str) -> None:
    """Module-load drift guard. `KNOWN_FAULT_CLASSES` is derived from
    `injector.agent._FAULT_CLASSES` at import time, so they cannot diverge
    today. This test exists to fail loudly IF a future refactor splits
    them — at which point either (a) re-derive at import time, or (b) add
    a CI step (docs/architecture.md silent-failure pattern #3) that diffs the two."""
    from phoenix_audit_agent.api.datasets_validation import KNOWN_FAULT_CLASSES
    from phoenix_audit_agent.injector.agent import _FAULT_CLASSES

    assert set(KNOWN_FAULT_CLASSES) == set(_FAULT_CLASSES)
