"""Dataset-row phase of the audit pipeline.

Runs after the synthetic battery: invokes the target with each dataset
row's prompt on a dedicated adapter lifecycle, records AttackResults
tagged source=f"dataset:{slug}", emits SSE frames with origin=same.
Failures contain to a structured warning + return cleanly; the synthetic
battery's verdicts are never voided.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any, cast

import structlog

from phoenix_audit_agent.injector.agent import AttackResult, FaultClass, InjectorState
from phoenix_audit_agent.injector.target_adapters.base import AdapterInvocation

_log = structlog.get_logger(__name__)

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_KNOWN_FAULT_CLASSES: frozenset[str] = frozenset(
    {"malformed_tool_output", "prompt_injection", "context_poisoning", "latency_spike"}
)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def run_dataset_rows(
    *,
    run_id: str,
    target_url: str,
    dataset_slug: str,
    state: InjectorState,
    emit: EmitFn,
    build_adapter: Callable[[str], Any],
) -> None:
    """Drive each dataset row through the target and record AttackResults.

    `build_adapter` is injected so audit_runner.py stays the single source of
    truth for adapter selection AND tests can monkeypatch one symbol.
    """
    from phoenix_audit_agent.api.datasets import get_phoenix_client
    from phoenix_audit_agent.storage.datasets import get_dataset_index_store

    try:
        idx = await get_dataset_index_store().get_by_slug(dataset_slug)
    except Exception as e:
        _log.warning(
            "dataset_phase_index_lookup_failed",
            run_id=run_id,
            dataset_slug=dataset_slug,
            error_type=type(e).__name__,
            error=str(e),
        )
        return
    if idx is None:
        _log.warning("dataset_phase_index_missing", run_id=run_id, dataset_slug=dataset_slug)
        return
    try:
        items = await get_phoenix_client().get_examples(idx.phoenix_dataset_id)
    except Exception as e:
        _log.warning(
            "dataset_phase_rows_fetch_failed",
            run_id=run_id,
            dataset_slug=dataset_slug,
            phoenix_dataset_id=idx.phoenix_dataset_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        return
    if not items:
        return

    adapter = build_adapter(target_url)
    try:
        await adapter.connect()
    except Exception as e:
        _log.warning(
            "dataset_phase_adapter_connect_failed",
            run_id=run_id,
            dataset_slug=dataset_slug,
            error_type=type(e).__name__,
            error=str(e),
        )
        return

    source = f"dataset:{dataset_slug}"
    base_offset = state.total_attacks
    n = base_offset
    try:
        for row in items:
            # Skip rows with fault_class outside the four-class taxonomy. The
            # signed report's cluster + fault-class breakdown stays honest;
            # silently coercing unknown classes to prompt_injection (PR #129
            # code-review #2) misrepresents both verdict and category.
            if row.fault_class not in _KNOWN_FAULT_CLASSES:
                _log.warning(
                    "dataset_row_unknown_fault_class_skipped",
                    run_id=run_id,
                    dataset_slug=dataset_slug,
                    case_id=row.case_id,
                    fault_class=row.fault_class,
                )
                await emit(
                    "test_skipped",
                    {
                        "fault_class": row.fault_class,
                        "origin": source,
                        "case_id": row.case_id,
                        "reason": "unknown fault_class outside the audit taxonomy",
                        "run_id": run_id,
                    },
                )
                continue
            n += 1
            # Membership in _KNOWN_FAULT_CLASSES (checked above) proves row.fault_class
            # is one of the four — cast lets ty narrow from str to the Literal.
            fault_class: FaultClass = cast(FaultClass, row.fault_class)
            await emit(
                "test_started",
                {
                    "n": n,
                    "fault_class": fault_class,
                    "origin": source,
                    "case_id": row.case_id,
                    "source": row.source,
                    "run_id": run_id,
                },
            )
            attack = await _invoke_one_row(
                adapter=adapter,
                row=row,
                run_id=run_id,
                dataset_slug=dataset_slug,
                fault_class=fault_class,
                source_tag=source,
                n=n,
            )
            state.record_attack(attack)
            await emit(
                "test_completed",
                {
                    "n": n,
                    "fault_class": fault_class,
                    "origin": source,
                    "case_id": row.case_id,
                    "status": attack.status,
                    "span_id": attack.span_id,
                    "duration_ms": attack.duration_ms,
                    "run_id": run_id,
                },
            )
    finally:
        try:
            await adapter.disconnect()
        except Exception as e:
            _log.warning(
                "dataset_phase_adapter_disconnect_failed",
                run_id=run_id,
                exc_type=type(e).__name__,
                error=str(e),
            )


async def _invoke_one_row(
    *,
    adapter: Any,
    row: Any,
    run_id: str,
    dataset_slug: str,
    fault_class: FaultClass,
    source_tag: str,
    n: int,
) -> AttackResult:
    """Send one dataset row to the target; map outcome to AttackResult."""
    common_attrs: dict[str, Any] = {
        "phoenix_audit.fault.type": fault_class,
        "phoenix_audit.dataset.case_id": row.case_id,
        "phoenix_audit.dataset.source": row.source,
        "phoenix_audit.dataset.expected": row.expected,
    }
    try:
        result = await adapter.invoke(AdapterInvocation(prompt=row.prompt, fault_config=None))
    except Exception as exc:
        _log.warning(
            "dataset_row_invoke_failed",
            run_id=run_id,
            dataset_slug=dataset_slug,
            case_id=row.case_id,
            exc_type=type(exc).__name__,
            exc_info=True,
        )
        return AttackResult(
            run_idx=n - 1,
            fault_class=fault_class,
            span_id=f"error:{type(exc).__name__}",
            trace_id="error:no-trace",
            status="error",
            duration_ms=0.0,
            attack_payload=row.prompt,
            span_attributes={**common_attrs, "phoenix_audit.attack.exception": type(exc).__name__},
            source=source_tag,
            expected=row.expected,
        )

    adapter_span_id = result.span_ids[0] if result.span_ids else ""
    raw_trace = result.metadata.get("trace_id", "") if result.metadata else ""
    trace_id = raw_trace if _HEX32.fullmatch(str(raw_trace) or "") else ""
    if not adapter_span_id or not trace_id:
        return AttackResult(
            run_idx=n - 1,
            fault_class=fault_class,
            span_id=trace_id or "missing:no-trace-emitted",
            trace_id=trace_id or "missing:no-trace-emitted",
            status="error",
            duration_ms=result.duration_ms,
            attack_payload=row.prompt,
            span_attributes={**common_attrs, "phoenix_audit.attack.span_missing": True},
            source=source_tag,
            expected=row.expected,
        )
    return AttackResult(
        run_idx=n - 1,
        fault_class=fault_class,
        span_id=trace_id,
        trace_id=trace_id,
        status="ok",
        duration_ms=result.duration_ms,
        attack_payload=row.prompt,
        span_attributes=common_attrs,
        source=source_tag,
        expected=row.expected,
    )


__all__ = ["run_dataset_rows"]
