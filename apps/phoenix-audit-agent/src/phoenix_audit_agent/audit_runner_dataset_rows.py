"""Dataset-row phase of the audit pipeline.

When the operator picks a dataset in `/new`, this phase runs AFTER the
synthetic battery — sending each dataset row's prompt to the target on its
own adapter lifecycle, recording AttackResults onto the shared
InjectorState, and emitting SSE frames with `origin=f"dataset:{slug}"`
so the chamber UI can label the two phases distinctly.

Containment rules: failures of this phase MUST NOT abort the audit. The
synthetic battery already produced real verdicts, and the signed report
tells the truth either way. Each failure mode is logged as a structured
warning and the phase returns cleanly.

Architectural note: dataset rows are adversarial prompts, not in-process
fault injection — no hook is registered on the target. The judge sees no
`phoenix_audit.fault.*` marker on these probes and naturally classifies
them as pass-by-avoidance per `judge_phase._fault_fired`. That is the
correct semantic for an agent that gave a clean response to an
adversarial prompt.
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
AdapterBuilder = Callable[[str], Any]


def _coerce_fault_class(raw: str) -> FaultClass:
    """Map a dataset row's free-form fault_class string to the typed Literal.

    Rows from public corpora (HarmBench, OWASP, etc.) may use labels outside
    our four-class taxonomy. We normalize to the closest match by prefix or
    fall back to `prompt_injection` (the most common adversarial intent in
    public datasets). Logged at debug so a future drift can be diagnosed.
    """
    if raw in _KNOWN_FAULT_CLASSES:
        return cast(FaultClass, raw)
    _log.debug("dataset_row_unknown_fault_class_coerced", raw=raw, mapped="prompt_injection")
    return "prompt_injection"


async def run_dataset_rows(
    *,
    run_id: str,
    target_url: str,
    dataset_slug: str,
    state: InjectorState,
    emit: EmitFn,
    build_adapter: AdapterBuilder,
) -> None:
    """Drive each dataset row through the target and record AttackResults.

    `build_adapter` is injected so audit_runner.py keeps a single source of
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

    origin = f"dataset:{dataset_slug}"
    base_offset = state.total_attacks
    try:
        for i, row in enumerate(items):
            n = base_offset + i + 1
            fault_class = _coerce_fault_class(row.fault_class)
            await emit(
                "test_started",
                {
                    "n": n,
                    "fault_class": fault_class,
                    "origin": origin,
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
                n=n,
            )
            state.record_attack(attack)
            await emit(
                "test_completed",
                {
                    "n": n,
                    "fault_class": fault_class,
                    "origin": origin,
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
    n: int,
) -> AttackResult:
    """Send one dataset row to the target; map the outcome to AttackResult.

    Three buckets: invoke-raises → error AttackResult with sentinel ids;
    no evidence → error AttackResult (trace_id missing); evidence → ok
    AttackResult with the target's trace_id as span_id (the canonical
    32-hex form the judge fetches by).
    """
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
    )


__all__ = ["run_dataset_rows"]
