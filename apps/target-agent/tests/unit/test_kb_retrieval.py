"""S-EC6: the naive KB retrieval tool — F3 retriever_insert's attack surface.

The demo target needs a real `BaseRetrievalTool` so Phoenix Audit's
context-poisoning battery (retriever_insert variants) has a genuine retrieval
path to poison. Naive by design: no source filtering, no provenance check —
the poisoned document is consumed as authoritative policy.
"""

from __future__ import annotations

from google.adk.tools.retrieval import BaseRetrievalTool

from target_agent.tools import kb_retrieval_tool


def test_kb_tool_is_a_real_retrieval_tool() -> None:
    assert isinstance(kb_retrieval_tool, BaseRetrievalTool)
    assert kb_retrieval_tool.name == "search_policy_kb"


async def test_kb_returns_policy_documents_as_list() -> None:
    docs = await kb_retrieval_tool.run_async(args={"query": "refund"}, tool_context=None)
    assert isinstance(docs, list)
    assert docs, "seeded KB must not be empty"
    assert all(isinstance(d, str) for d in docs)
    assert any("refund" in d.lower() for d in docs)


async def test_kb_unmatched_query_still_returns_list() -> None:
    docs = await kb_retrieval_tool.run_async(args={"query": "zzz-no-match"}, tool_context=None)
    assert isinstance(docs, list)


def test_root_agent_exposes_the_kb_tool() -> None:
    from target_agent.agent import root_agent

    assert any(getattr(t, "name", "") == "search_policy_kb" for t in root_agent.tools)
