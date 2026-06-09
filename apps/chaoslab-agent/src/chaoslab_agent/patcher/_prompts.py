"""Patcher LLM prompts. Separated from agent.py to keep per-task LOC low."""
# ruff: noqa: E501  — prompt prose intentionally exceeds line-length limits.

from __future__ import annotations

PER_CLUSTER_PATCHER_PROMPT = """You are ChaosLab's Patcher. Given one cluster of agent failures
with a single root cause, generate (a) one or more PromptPatch entries that fix the root cause
by editing the agent's system prompt, tool descriptions, or few-shot examples, and (b) optionally
one or more ToolValidationDiff entries that add input/output validators, retry policies, or
timeouts to the affected tools.

CLUSTER:
- cluster_id: {cluster_id}
- root_cause: {root_cause}
- failure_count: {failure_count}
- fault_classes: {fault_classes}

FAULT-CLASS -> FIX MAPPING (guidance, not constraint):
- malformed_tool_output -> add_input_validator OR add_output_validator + prompt rule "validate tool outputs"
- prompt_injection -> system_prompt insert with refusal pattern
- context_poisoning -> system_prompt insert with provenance-check rule
- latency_spike -> add_retry_policy AND add_timeout

OUTPUT STRICT JSON ONLY (no markdown fences, no prose):
{{
  "prompt_patches": [
    {{
      "section": "system_prompt" | "tool_description" | "few_shot_example",
      "operation": "insert" | "replace" | "append",
      "before": <string|null>,
      "after": "<the patch text>"
    }}
  ],
  "tool_validation_diffs": [
    {{
      "tool_name": "<tool name from cluster context>",
      "operation": "add_input_validator" | "add_output_validator" | "add_retry_policy" | "add_timeout",
      "code_patch": "<unified diff format>"
    }}
  ]
}}

CONSTRAINTS:
- prompt_patches MUST contain at least 1 entry per cluster.
- tool_validation_diffs SHOULD contain at least 1 entry for malformed_tool_output and latency_spike clusters.
- When operation == "replace", "before" MUST be the exact text being replaced.
- code_patch MUST be valid unified-diff format starting with "--- " and "+++ ".
"""

RETRY_PROMPT = (
    "Your previous output was not valid JSON or did not match the schema. "
    "Re-emit ONLY the JSON object, no prose, no fences. Schema is unchanged."
)


__all__ = ["PER_CLUSTER_PATCHER_PROMPT", "RETRY_PROMPT"]
