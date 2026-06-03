# Google's Canonical Agent Platform Link Directory

**Source:** https://github.com/Google-Cloud-AI/agent-platform/blob/main/README.md
**Fetched:** 2026-06-02

This is Google's own master link directory for the Gemini Enterprise Agent Platform — the most authoritative single source of "where does X live?" for the entire platform.

---

## Onboarding & video

- **Onboarding Guide:** https://goo.gle/agent-platform-onboard (Google's quick-start)
- **Intro video:** https://goo.gle/agent-platform-video → resolves to the Holt Skinner video at https://youtu.be/j8qW5poBkEU (full transcript at `refs/holt-skinner-gemini-enterprise-agent-platform-transcript.md`)

## Foundation Models

- **Gemini API:** https://deepmind.google/models/gemini/
- **Veo (video):** https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate
- **Lyria (music):** https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/lyria/lyria-3
- **Nano Banana (image):** https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-flash-image
- **Model Garden:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-garden/explore-models (150+ partner and open-weight models, including Claude)

## Build phase

- **Agent Development Kit (ADK):** https://adk.dev — open-source, model-agnostic agent framework
- **Agents CLI:** https://google.github.io/agents-cli/ — scaffold, test, deploy
- **Agent Studio:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/agent-studio — low-code visual interface
- **Agent Garden:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/agent-garden — pre-built agent templates
- **Grounding:** https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/grounding/intro-grounding-gemini.ipynb
- **RAG Engine:** https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/rag-engine/intro_rag_engine.ipynb
- **Agent Search** (formerly Vertex AI Search / Generative AI App Builder): https://docs.cloud.google.com/generative-ai-app-builder/docs/try-enterprise-search
- **Vector Search 2.0:** https://github.com/GoogleCloudPlatform/generative-ai/blob/main/embeddings/vector-search-2-intro.ipynb

## Protocols & interoperability (FIVE total — not just MCP/A2A)

- **MCP (Model Context Protocol):** https://modelcontextprotocol.io/ — agent ↔ tools
- **A2A (Agent-to-Agent):** https://a2a-protocol.org — agent ↔ agent
- **A2UI (Agent-to-UI):** https://a2ui.org — agent generates dynamic UIs
- **AP2 (Agent Payments Protocol):** https://ap2-protocol.org — secure automated financial transactions
- **UCP (Universal Commerce Protocol):** https://ucp.dev/ — unified e-commerce/retail operations

## Scale phase

- **Agent Runtime** (formerly Agent Engine, Reasoning Engine): https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/agent-engine/intro_agent_engine.ipynb
- **Agent Sessions:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/sessions
- **Agent Memory Bank:** https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/memory_bank/get_started_with_memory_bank.ipynb
- **Agent Sandbox** (= Code Execution): https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/tutorial_get_started_with_code_execution.ipynb

## Govern phase (some private preview)

- **Agent Gateway:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/gateways/agent-gateway-overview *(Private Preview — Abu won't have access for the hackathon)*
- **Agent Identity:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/agent-identity-overview
- **Agent Policies:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/policies/overview *(Private Preview)*
- **Agent Registry:** https://docs.cloud.google.com/agent-registry/overview
- **Model Armor:** https://docs.cloud.google.com/model-armor/overview

## Optimize phase

- **Agent Evaluation:** https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/create_agent_and_run_evaluation.ipynb
- **Agent Simulation:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/optimize/evaluation/evaluate-simulated
- **Agent Observability:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/optimize/observability/overview
- **Agent Optimizer:** https://docs.cloud.google.com/gemini-enterprise-agent-platform/optimize/evaluation/optimize-agent

## Notebook tutorials (the bulk of practical learning material)

All notebooks live in the `GoogleCloudPlatform/generative-ai` repo, not the `Google-Cloud-AI/agent-platform` repo (which is just a directory README). Key starter notebooks:

### Core Gemini
- [Intro to Gemini 3.5 Flash](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_3_5_flash.ipynb) ⭐ **current default model**
- [Intro to Gemini 3.1 Flash-Lite](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_3_1_flash_lite.ipynb)
- [Intro to Gemini 3.1 Pro](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_3_1_pro.ipynb)
- [Intro to Batch Prediction](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/batch-prediction/intro_batch_prediction.ipynb)
- [Intro to Code Execution](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/code-execution/intro_code_execution.ipynb)
- [Intro to Computer Use](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/computer-use/intro_computer_use.ipynb)
- [Intro to Agentic Vision](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/code-execution/intro_agentic_vision.ipynb)
- [Intro to Context Caching](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/context-caching/intro_context_caching.ipynb)
- [Intro to Live API](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/multimodal-live-api/live_api_quickstart.ipynb)

### Specialized use cases
- [Intro to Evaluation](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/quick_start_gen_ai_eval.ipynb)
- [Document Processing](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/document-processing/document_processing.ipynb)
- [Spatial Understanding](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/spatial-understanding/spatial_understanding.ipynb)
- [YouTube Video Analysis](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/video-analysis/youtube_video_analysis.ipynb)
- [Prompt Attacks and Mitigation](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/responsible-ai/gemini_prompt_attacks_mitigation_examples.ipynb)
- [Intro to LangGraph](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/orchestration/intro_langgraph_gemini.ipynb) (reference only — banned as primary orchestrator for this hackathon)

### Embeddings & Vector Search
- [Text Embeddings + Vector Search](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/embeddings/intro-textemb-vectorsearch.ipynb)
- [Multimodal Embeddings](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/embeddings/intro_multimodal_embeddings.ipynb)
- [Vector Search 2.0](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/embeddings/vector-search-2-intro.ipynb)
- [Hybrid Search](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/embeddings/hybrid-search.ipynb)

---

**Note from the repo:** "This is not an officially supported Google product." — i.e., samples-only, not a SLA-backed service. The notebooks are reference patterns.
