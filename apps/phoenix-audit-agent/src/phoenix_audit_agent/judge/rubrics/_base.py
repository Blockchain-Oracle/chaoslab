"""Shared types + dispatcher for Judge rubrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, assert_never, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

FaultClass = Literal[
    "malformed_tool_output",
    "prompt_injection",
    "context_poisoning",
    "latency_spike",
]


class RubricInputMissingError(ValueError):
    """A required Phoenix span attribute was absent or empty."""

    def __init__(self, span_id: str, fault_class: str, attribute: str) -> None:
        self.span_id = span_id
        self.fault_class = fault_class
        self.attribute = attribute
        super().__init__(
            f"rubric={fault_class} span_id={span_id} required attribute "
            f"{attribute!r} missing or empty — refusing to silently pass"
        )


class PhoenixEvalEmptyError(RuntimeError):
    """Phoenix's async_evaluate returned an empty list (rate-limit/safety/parse)."""

    def __init__(self, span_id: str, fault_class: str) -> None:
        self.span_id = span_id
        self.fault_class = fault_class
        super().__init__(
            f"rubric={fault_class} span_id={span_id} Phoenix returned no Score — "
            "verdict lost; check rate-limit / safety-block / parse failure"
        )


def first_verdict(
    verdicts: list[Any] | tuple[Any, ...],
    *,
    span_id: str,
    fault_class: str,
) -> Any:
    """Unwrap the single Score Phoenix returns, raising loudly on empty."""
    if not verdicts:
        raise PhoenixEvalEmptyError(span_id, fault_class)
    return verdicts[0]


class EvalScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _passed_aligns_with_score(self) -> EvalScore:
        # A pass with score 0 (or a fail with score 1) would silently disagree
        # with downstream consumers that read score alone for clustering.
        if self.passed and self.score == 0.0:
            msg = "passed=True with score=0.0 is contradictory"
            raise ValueError(msg)
        if not self.passed and self.score == 1.0:
            msg = "passed=False with score=1.0 is contradictory"
            raise ValueError(msg)
        return self


@runtime_checkable
class _SpansNamespace(Protocol):
    # Mirrors arize-phoenix-client 2.x AsyncSpans — there is NO get_span;
    # trace reads go through phoenix_tools.span_fetch.fetch_trace_spans.
    async def get_spans(self, **kwargs: Any) -> list[Any]: ...


@runtime_checkable
class PhoenixClient(Protocol):
    """Narrow Protocol of phoenix.client.AsyncClient the judge phase uses."""

    spans: _SpansNamespace


# Re-exported alias so tests can inherit the namespace Protocol nominally.
SpansNamespace = _SpansNamespace


# Hex chars for both 16-char span IDs and 32-char trace IDs — the Injector
# may pass either depending on whether it indexes by tool-call span or root.
SPAN_ID_PATTERN = r"^[0-9a-f]{16}(?:[0-9a-f]{16})?$"
_SPAN_ID_PATTERN = SPAN_ID_PATTERN  # backward-compat alias


class RubricInput(BaseModel):
    """Everything a rubric needs to score one probe.

    Evidence model (evidence-chain repair, 2026-06-10):
    - ``spans`` is the probe's WHOLE target-side trace, prefetched once by
      judge_phase (no per-rubric Phoenix round-trips). Rubrics select the
      span(s) carrying their evidence via the helpers below.
    - Auditor-ORIGINATED data (the attack payload, the original prompt, the
      client-measured duration) rides here directly — round-tripping it
      through span attributes added no evidence value and the writer side
      never existed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    span_id: str = Field(pattern=_SPAN_ID_PATTERN)
    trace_id: str = Field(min_length=1)
    fault_class: FaultClass
    spans: list[Any]
    attack_payload: str | None = None
    original_user_message: str | None = None
    client_duration_ms: float | None = None

    def root_span(self) -> Any:
        root = next((s for s in self.spans if getattr(s, "is_root", False)), None)
        if root is None:
            raise RubricInputMissingError(self.span_id, self.fault_class, "trace root span")
        return root

    def require_attr_from_trace(self, key: str) -> str:
        """Non-empty ``key`` from the FIRST span carrying it (root searched
        first — its values are the response-level evidence) or raise."""
        ordered = sorted(self.spans, key=lambda s: not getattr(s, "is_root", False))
        for span in ordered:
            value = span.attributes.get(key)
            if value is not None and not (isinstance(value, str) and not value):
                return str(value)
        raise RubricInputMissingError(self.span_id, self.fault_class, key)

    def collect_retrieval_documents(self) -> str:
        """The trace's retrieval evidence: ``retrieval.documents`` where the
        backend returns it whole, else the OpenInference flattened form
        (``retrieval.documents.{i}.document.content``); raise when neither
        exists — scoring F3 without the retrieved context would be guesswork."""
        for span in self.spans:
            whole = span.attributes.get("retrieval.documents")
            if whole:
                return str(whole)
        docs: list[str] = []
        for span in self.spans:
            flattened = [
                (k, v)
                for k, v in span.attributes.items()
                if k.startswith("retrieval.documents.") and k.endswith(".document.content") and v
            ]
            docs.extend(str(v) for _, v in sorted(flattened))
        if docs:
            return "\n\n".join(docs)
        raise RubricInputMissingError(self.span_id, self.fault_class, "retrieval.documents")

    def require_payload(self) -> str:
        if not self.attack_payload:
            raise RubricInputMissingError(self.span_id, self.fault_class, "attack_payload")
        return self.attack_payload


def _import_tool_invocation_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from phoenix_audit_agent.judge.rubrics.tool_invocation import tool_invocation_rubric

    return tool_invocation_rubric


def _import_prompt_injection_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from phoenix_audit_agent.judge.rubrics.prompt_injection_success import (
        prompt_injection_rubric,
    )

    return prompt_injection_rubric


def _import_hallucination_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from phoenix_audit_agent.judge.rubrics.hallucination import hallucination_rubric

    return hallucination_rubric


def _import_latency_failure_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from phoenix_audit_agent.judge.rubrics.latency_failure import latency_failure_rubric

    return latency_failure_rubric


async def apply_rubric(inp: RubricInput) -> EvalScore:
    # Lazy-imports per-class modules so the Phoenix LLM credential check
    # defers past test-collection. assert_never on the fallthrough turns
    # "added a new FaultClass" into a compile-time error at this site.
    match inp.fault_class:
        case "malformed_tool_output":
            rubric = _import_tool_invocation_rubric()
        case "prompt_injection":
            rubric = _import_prompt_injection_rubric()
        case "context_poisoning":
            rubric = _import_hallucination_rubric()
        case "latency_spike":
            rubric = _import_latency_failure_rubric()
        case _:  # pragma: no cover — unreachable under FaultClass Literal
            assert_never(inp.fault_class)
    return await rubric(inp)


__all__ = [
    "EvalScore",
    "FaultClass",
    "PhoenixClient",
    "PhoenixEvalEmptyError",
    "RubricInput",
    "RubricInputMissingError",
    "apply_rubric",
    "first_verdict",
]
