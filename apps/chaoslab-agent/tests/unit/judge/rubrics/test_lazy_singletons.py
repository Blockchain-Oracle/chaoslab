"""Lazy-singleton tests.

Importing a rubric module must NOT instantiate the Phoenix LLM (which would
run a credential check and break unit-test collection in environments without
GOOGLE_API_KEY set).
"""

from __future__ import annotations


def test_tool_invocation_module_does_not_eagerly_build_evaluator() -> None:
    import chaoslab_agent.judge.rubrics.tool_invocation as f1

    assert f1._EVALUATOR is None


def test_hallucination_module_does_not_eagerly_build_evaluator() -> None:
    import chaoslab_agent.judge.rubrics.hallucination as f3

    assert f3._EVALUATOR is None


def test_prompt_injection_module_does_not_eagerly_build_evaluator() -> None:
    import chaoslab_agent.judge.rubrics.prompt_injection_success as f2

    assert f2._EVALUATOR is None


def test_shared_llm_module_does_not_eagerly_build_judge() -> None:
    import chaoslab_agent.judge.rubrics._llm as llm_mod

    assert llm_mod._JUDGE is None
