"""Judge sub-agent — LLM-as-judge rubrics + failure clustering (Epic 6)."""

from chaoslab_agent.judge.agent import JUDGE_NAME, build_judge_agent

__all__ = ["JUDGE_NAME", "build_judge_agent"]
