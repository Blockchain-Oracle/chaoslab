"""Shared lazy `Phoenix.evals.LLM` singleton for all rubrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from chaoslab_agent.config import get_settings

if TYPE_CHECKING:
    from phoenix.evals import LLM

_JUDGE: Any = None


def get_judge_llm() -> LLM:
    # Lazy: instantiating `LLM(provider="google_genai", ...)` at module load
    # triggers a credential check that breaks unit-test imports without
    # GOOGLE_API_KEY set.
    global _JUDGE  # noqa: PLW0603
    if _JUDGE is None:
        from phoenix.evals import LLM

        _JUDGE = LLM(provider="google_genai", model=get_settings().JUDGE_LLM)
    return _JUDGE


__all__ = ["get_judge_llm"]
