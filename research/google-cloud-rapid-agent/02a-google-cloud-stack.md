# Google Cloud Agent Stack — Abu's Rosetta Stone

**Hackathon:** Google Cloud Rapid Agent (rapid-agent.devpost.com)
**Deadline:** June 11, 2026
**Audience:** Abu — blockchain-native dev with ZERO Google Cloud / Vertex AI / Gemini experience
**Goal of this file:** Open this in a week and instantly understand every term, tool, and decision point. No re-research needed.

The thing that's confusing about this stack right now: **Google renamed everything at Google Cloud Next 2026 (April 22, 2026).** What you read in tutorials from 2024 / early 2025 uses old names. The console UI uses NEW names. This document is the bridge.

---

## 1. The Rosetta Stone (Naming Map)

Read this table first. Re-read it whenever you get confused about what's what.

| You'll see this (old / docs / blog posts) | Today's name (June 2026) | What it actually is |
|---|---|---|
| **Vertex AI** | **Gemini Enterprise Agent Platform** | The umbrella product. The whole managed offering for building/running/governing agents on Google Cloud. "Vertex AI" still exists as a billing line item and Python SDK package (`google-cloud-aiplatform`), but the *product surface* is now Gemini Enterprise Agent Platform. |
| **Gemini Enterprise** | Gemini Enterprise (separate) | This is the *end-user app* (Google's ChatGPT-for-business, formerly the "Gemini for Workspace" successor). NOT what you build on. Don't confuse with the Agent Platform. |
| **Vertex AI Agent Builder** | **Agent Platform → Studio** (a.k.a. "Agent Studio") | The low-code visual agent builder in the GCP Console. Previously called "Agent Designer" in preview, then "Agent Builder", now "Agent Studio". Same tool, third name. |
| **Vertex AI Search and Conversation** | Now folded into Agent Studio (RAG/Search component) | Old name for the RAG / search engine piece. Lives inside Agent Studio now as the data-store + grounding feature. |
| **Agent Development Kit / ADK** | **ADK (unchanged)** | The code-first open-source framework. `pip install google-adk`. Python is primary; TypeScript / Go / Java / Kotlin also supported. This is the path you almost certainly want for a hackathon. |
| **Vertex AI Reasoning Engine** | **Agent Runtime** | The managed serverless runtime for hosting ADK agents. Sub-second cold starts, multi-day workflows. Replaces / supersedes "Reasoning Engine". Sometimes still called "Agent Engine" in older blog posts. |
| **Cloud Run** | **Cloud Run (unchanged)** | Generic serverless containers. Not agent-specific. Run any Docker container, scales to zero. The cheap general-purpose option. |
| **Gemini API / Google AI Studio** | Gemini API via AI Studio (consumer tier) | Personal API key at `aistudio.google.com`. Cheaper / free tier. Separate billing from Google Cloud. **For this hackathon, you want the Vertex AI / Agent Platform path, not the AI Studio path**, because the $100 credit applies to Cloud, not to AI Studio. |
| **Antigravity** | Antigravity (separate, unrelated build target) | Google's agentic IDE (their answer to Cursor). **It is a developer tool, NOT a deployment target for the hackathon.** Don't accidentally build "an Antigravity agent" — you want a Gemini Enterprise Agent Platform agent. |
| Models: Gemini 2.0, 2.5, 3.0, 3.1 | **Gemini 3.x is current** (Pro, Flash, Flash-Lite, Flash Image, Nano) | Naming convention: bigger = smarter + more expensive. "Pro" = top-tier reasoning. "Flash" = fast + cheap default. "Flash-Lite" = cheapest. Gemini 2.0 Flash was deprecated June 1, 2026. |
| Agent Garden | Agent Garden (new) | Library of pre-built agent templates inside the Agent Platform. Pulls from Google + partners. Worth a browse for inspiration. |
| Agent Memory Bank | Agent Memory Bank (new) | Managed memory/state store for agents. The "stateful" piece. |
| Agent Identity / Registry / Gateway | New governance layer | Identity = who/what an agent is. Registry = catalog of agents in your org. Gateway = secure ingress for agent traffic. You probably do NOT need these for a hackathon demo. |
| Agent Simulation / Evaluation / Observability | New optimization layer | Pre-prod testing + production observability. Arize integrates here (the Arize hackathon track is about observability). |
| A2A (Agent-to-Agent Protocol) | A2A | Google's open protocol for agent ↔ agent communication. Different from MCP (MCP = agent ↔ tools). |
| MCP (Model Context Protocol) | MCP (Anthropic-originated, now broadly adopted) | The protocol agents use to call external tools/services. **At least one Partner MCP server is REQUIRED for the hackathon submission.** |

### What lives where in the GCP Console (June 2026)

When you log in to `console.cloud.google.com`:

- Left nav → **AI** section → **Agent Platform** (this is where everything agent-related lives).
- Inside Agent Platform, you'll see:
  - **Studio** (visual builder — formerly "Agent Builder")
  - **Garden** (templates)
  - **Runtime** (deployments)
  - **Memory Bank**
  - **Registry / Identity / Gateway** (governance)
  - **Evaluation / Observability** (optimization)
- **Vertex AI** is still a side-nav item, but most actions redirect into Agent Platform.
- **Cloud Run** lives under the Compute / Serverless section, not under AI. Same as always.
- **Secret Manager** lives under Security. You'll use this for API keys.

---

## 2. The Two Build Paths

You have to pick one. The hackathon rules allow EITHER but they have very different shape.

### Path A: Visual (Agent Studio in the Console)

- Low-code drag-and-drop in the browser at `console.cloud.google.com → Agent Platform → Studio`.
- Define agent with: name, model, instruction prompt, tools (selected from a catalog), data sources for RAG.
- **Pros:** Fastest demo. Built-in playground. Easy for non-coders. Exports to ADK code when you outgrow it.
- **Cons:** Less control. Custom logic is painful. Custom tools require config gymnastics. **MCP server integration is shakier in the console** than in code. Hard to debug.

### Path B: Code-first (ADK + Agent Runtime OR Cloud Run)

- Write Python (or TS/Go/Java/Kotlin). `pip install google-adk`. Build agent in code. Deploy via `adk deploy` to Agent Runtime, OR package as Docker and ship to Cloud Run.
- **Pros:** Full control. Real software engineering. Trivial MCP integration (`MCPToolset` is a first-class primitive). Source-controlled. Works with the Anti-Slop loop / agentic dev flow you already use. **Required by the Arize track** because Arize's tracing needs a code-owned runtime to instrument.
- **Cons:** More setup. You write more code. Need to think about deployment.

### Decision matrix

| If… | Pick |
|---|---|
| You're targeting the Arize track | **Code-first (ADK)** — REQUIRED |
| You want fastest demo, simple use case | Visual (Studio) |
| You're integrating a Partner MCP server | **Code-first (ADK)** — much smoother |
| You want a custom frontend / API | **Code-first** → deploy backend on Cloud Run |
| You'll demo via the Studio playground UI | Visual |
| You're using fancy multi-agent orchestration | **Code-first (ADK sub-agents)** |

**Recommendation for Abu: Path B (Code-first ADK).** You have agentic dev workflows. You will need MCP. You will want git. You will want to debug. Studio is for product managers.

---

## 3. Agent Development Kit (ADK) — Deep Dive

### What it is

ADK = open-source Python framework from Google for building production AI agents. Repo: `google/adk-python`. Docs: `https://adk.dev` (redirected from `google.github.io/adk-docs/`).

Tagline from Google: *"Build production agents, not prototypes."* It's positioned as the code-first counterpart to LangChain/LlamaIndex, but designed by Google specifically for Gemini + Google Cloud deployment. Currently processes 6 trillion+ tokens/month.

### Languages

Python is the canonical implementation. Also: TypeScript, Go, Java, Kotlin. **Use Python.**

### Install

```bash
pip install google-adk
# Optional extras
pip install "google-adk[extensions]"
```

Requires **Python 3.11+**.

### The anatomy of an ADK agent

An agent has these parts:

- **Model** — the Gemini model ID, e.g. `"gemini-3.5-flash"` or `"gemini-3.1-pro-preview"`.
- **Instruction** — the system prompt. Defines persona and behavior.
- **Tools** — callable functions (or `MCPToolset` instances, or built-in tools like `google_search`) the agent can invoke.
- **Sub-agents** — child agents the root agent can delegate to. This is how you do multi-agent orchestration without LangGraph.
- **Callbacks** — `before_model_callback`, `before_tool_callback`, etc. Hook into the lifecycle for guardrails, logging, arg-rewriting.
- **`generate_content_config`** — temperature, max_output_tokens, safety settings.

### Minimal hello-world

```python
# agent.py
from google.adk import Agent

root_agent = Agent(
    name="greeting_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant. Greet the user warmly.",
)
```

Run it locally with the ADK CLI:

```bash
adk run agent.py
# or for the web playground:
adk web
```

### Agent with a custom function tool

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

def get_capital_city(country: str) -> str:
    """Retrieves the capital city of a given country."""
    capitals = {
        "united states": "Washington, D.C.",
        "france": "Paris",
        "germany": "Berlin",
    }
    return capitals.get(country.lower(), f"Capital not found for {country}")

capital_tool = FunctionTool(func=get_capital_city)

agent = LlmAgent(
    name="geo_agent",
    model="gemini-2.5-flash",
    instruction="You answer questions about world capitals using the get_capital_city tool.",
    tools=[capital_tool],
)
```

Note: the docstring on `get_capital_city` is **load-bearing**. ADK uses it to generate the tool's schema for the LLM. Write good docstrings.

### Agent with sub-agents (multi-agent)

```python
from google.adk import Agent

greeting_agent = Agent(
    name="greeting_agent",
    model="gemini-2.5-flash",
    instruction="You ONLY greet users. Use the say_hello tool.",
    description="Handles greetings and hellos.",
    tools=[say_hello],
)

farewell_agent = Agent(
    name="farewell_agent",
    model="gemini-2.5-flash",
    instruction="You ONLY say goodbye. Use the say_goodbye tool.",
    description="Handles farewells.",
    tools=[say_goodbye],
)

root_agent = Agent(
    name="coordinator",
    model="gemini-2.5-flash",
    instruction=(
        "You coordinate a team. Delegate greetings to greeting_agent, "
        "farewells to farewell_agent. Handle other queries yourself."
    ),
    tools=[get_weather],
    sub_agents=[greeting_agent, farewell_agent],
)
```

The `description` field on sub-agents is what the root agent reads to decide WHEN to delegate. Write it like ad copy.

### Callbacks (guardrails)

```python
from typing import Optional, Dict, Any
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

def block_unsafe_input(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    if tool.name == "get_capital_city" and args.get("country", "").upper() == "BLOCK":
        return {"result": "Tool execution was blocked."}
    return None  # continue normally

agent = LlmAgent(
    name="guarded_agent",
    model="gemini-2.5-flash",
    instruction="...",
    tools=[capital_tool],
    before_tool_callback=block_unsafe_input,
)
```

### Sessions + Runner (for production use)

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name="my_app", session_service=session_service)

async def chat(user_id, session_id, text):
    session = await session_service.create_session(app_name="my_app", user_id=user_id, session_id=session_id)
    msg = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        print(event)
```

### How ADK differs from LangChain / LangGraph

- **Native Gemini-first.** No adapter layer. Calls models directly via the `google-genai` SDK.
- **Sub-agents are first-class.** No need for LangGraph's state graph DSL for simple delegation. Just put agents inside agents.
- **MCP is first-class.** `MCPToolset` is built in. Not a community add-on.
- **Designed for Agent Runtime deployment.** `adk deploy` exists. LangChain doesn't have a managed Google runtime.
- **Smaller surface area.** Fewer abstractions to learn. Closer to "writing real Python".
- **No retrieval orchestration baked in.** You bring your own RAG (or use Vertex AI Search via grounding).

### CRITICAL HACKATHON RULE: no competing orchestrators

Section 7B of the rules bans **LangChain / LangGraph / LlamaIndex as the PRIMARY orchestrator** in the submission. You can call LangChain *components* (e.g., a retriever) from inside an ADK tool, but ADK must be the top-level driver. Don't accidentally write a LangGraph agent that "calls Gemini" — that fails the rule.

---

## 4. Gemini Models — Which One, How Much

Source: https://ai.google.dev/gemini-api/docs/pricing

Prices below are **standard Vertex AI / Gemini API** rates per million tokens (1M tokens ≈ 750k words ≈ a small novel).

| Model | Input ($/M tok) | Output ($/M tok) | Best for |
|---|---|---|---|
| **Gemini 2.5 Pro** | $1.25 (≤200k) / $2.50 (>200k) | $10 / $15 | Hard reasoning, planning, multi-step tasks |
| **Gemini 2.5 Flash** | $0.30 (text/image/video) / $1.00 (audio) | $2.50 | **Hackathon default sweet spot** — fast, cheap, function-calling, MCP-friendly |
| **Gemini 2.5 Flash-Lite** | $0.10 | $0.40 | Cheapest viable. High-volume / simple classification |
| Gemini 2.0 Flash | $0.10 / $0.70 (audio) | $0.40 | **Deprecated June 1, 2026** — do NOT use |
| Gemini 3.1 Pro / Flash | [UNVERIFIED — listed in 3.x announcements but exact pricing not pulled] | [UNVERIFIED] | Newer models from Next 2026 keynote |

### Math against your $100 credit

Using Gemini 2.5 Flash at $0.30 in / $2.50 out:
- 1M input tokens + 100k output tokens = $0.55
- $100 credit ≈ ~180 such conversations. Plenty for build + demo.

Using Gemini 2.5 Pro at $1.25 in / $10 out:
- Same 1M in + 100k out = $2.25
- $100 credit ≈ ~44 such conversations. Still fine for hackathon scale.

### Function calling + MCP

All Gemini 2.5+ models support function calling natively. ADK uses this to wire tools. MCP tools get converted to function-calling schemas under the hood — no extra config required.

### Recommendation

**Default to Gemini 2.5 Flash.** Bump to 2.5 Pro for the root reasoning agent if your task needs multi-step planning. Keep sub-agents on Flash. This is the cost-optimal hackathon pattern.

Model IDs in code:

```python
MODEL_GEMINI_2_5_FLASH = "gemini-2.5-flash"
MODEL_GEMINI_2_5_PRO = "gemini-2.5-pro"
MODEL_GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"  # [UNVERIFIED exact ID]
```

---

## 5. Agent Runtime vs Cloud Run — Which Deployment

Both are allowed by hackathon rules. They are very different.

### Agent Runtime (Vertex AI Agent Engine)

- Managed runtime designed specifically for ADK agents.
- You don't think about Docker, ports, or HTTP servers.
- Built-in: versioning, session persistence, Memory Bank integration, observability tab in GCP Console, playground UI for testing from console.
- Deploy with `adk deploy agent_engine` (or via the SDK).
- **Does NOT expose a public REST API directly** — you call it via the Vertex AI SDK from a backend. For a web demo, you'd typically put a thin Cloud Run frontend in front of it that calls Agent Engine over the SDK.
- Sub-second cold starts. Multi-day workflows supported.

**When to use:** You want the simplest path. Console-driven demo. Don't care about HTTP control.

### Cloud Run

- Generic containerized hosting. Any language, any container.
- For ADK: `adk api_server` exposes your agent as a REST API on `localhost:8000`. Wrap that in a `Dockerfile`, push to Artifact Registry, deploy to Cloud Run.
- **Exposes a real public URL.** Easy to point a frontend at. Easy for judges to curl.
- Scales to zero. Pay per request.
- Standard Docker. Full control. Custom middleware. Custom auth.

**When to use:** You want a public URL judges can hit. You're building a custom frontend. You need any non-Python pieces alongside. You care about cost optimization.

### The hybrid pattern (most common)

- Backend agent runs on **Agent Runtime** (managed, simple).
- Thin **Cloud Run** service hosts your demo frontend (Streamlit / Next.js static / etc.) and proxies calls to Agent Runtime via the SDK.
- This gives you: public URL for the demo + managed agent infra.

### Recommendation

For a hackathon demo where judges need a clickable URL: **Cloud Run with `adk api_server` + a static frontend**, OR **Agent Runtime + a Streamlit-on-Cloud-Run frontend.** Either works. Cloud Run alone is simplest.

Sources:
- https://google.github.io/adk-docs/deploy/agent-engine/
- https://cloud.google.com/blog/topics/developers-practitioners/from-code-to-cloud-three-labs-for-deploying-your-ai-agent

---

## 6. What the $100 Credit Actually Covers

The hackathon distributes Google Cloud credits "while supplies last, first-come-first-served" (per the Devpost resources page). These are Google Cloud PROMOTIONAL credits, redeemable in the Billing section of Cloud Console.

### Confirmed covered (Google Cloud native services)

- **Vertex AI / Gemini Enterprise Agent Platform** — all Gemini API calls go through this billing line. Yes.
- **Gemini model inference** (Pro, Flash, Flash-Lite). Yes.
- **Cloud Run** — yes, including egress within free-tier limits.
- **Agent Builder / Agent Studio** — yes (it's part of Vertex AI).
- **Agent Runtime / Agent Engine** — yes.
- **Secret Manager** — yes.
- **Cloud Storage** — yes (for any artifacts/data).
- **Artifact Registry** — yes (for Docker images).
- **Cloud Build** — yes (for CI).

### Conditionally covered

- **Partner services on Google Cloud Marketplace** (MongoDB Atlas, Elastic Cloud, etc.) — yes, BUT only if you subscribed to them via the Marketplace, so the bill flows through your Cloud account. If you signed up directly on MongoDB.com, it does NOT count against the $100 — that's a separate bill on MongoDB's side.

### Not covered

- AI Studio (`aistudio.google.com`) — separate billing surface. Don't use the AI Studio API key for the hackathon; use the Vertex AI path.
- Anything outside Google Cloud (Vercel, Netlify, Railway, your own VPS, etc.).
- Antigravity (the IDE) — separate product.

### How long does $100 last?

Per the Devpost FAQ (paraphrased — verify against the live FAQ when you redeem): 100 credits typically covers **millions of API tokens** at Flash pricing. You'd have to actively try to burn it on Pro for a week to run out. For a hackathon, you will not hit the limit unless you're doing huge RAG ingestion.

Sources:
- https://rapid-agent.devpost.com/resources
- https://rapid-agent.devpost.com/updates

---

## 7. MCP Integration on the Google Side — The Critical Glue

This is the make-or-break piece. The hackathon REQUIRES at least one Partner MCP server in your submission. Here's exactly how you wire it up.

### What MCP is (short version)

Model Context Protocol = open standard (originated at Anthropic, now broadly adopted) for connecting AI models to external tools. An "MCP server" exposes tools over a standard wire format. An "MCP client" (your agent) calls those tools. Two transport modes:

- **stdio** — spawns the MCP server as a local subprocess; you and it talk via stdin/stdout. Used for tools that run on the same box.
- **SSE** (Server-Sent Events) — talks to a remote MCP server over HTTP. Used for hosted/partner MCP servers.

For the hackathon, **Partner MCP servers will almost certainly be SSE (remote HTTP)**, e.g., MongoDB's hosted MCP, Elastic's, etc.

### ADK's MCP primitive: `MCPToolset`

ADK ships an `MCPToolset` class that wraps an MCP server connection and exposes all its tools as ADK tools. This is the official way.

Import:

```python
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters  # for local
# For SSE remote: from google.adk.tools.mcp_tool import SseServerParams
```

(Exact import paths shift between ADK versions; the canonical examples in `google/adk-python/llms-full.txt` use the above.)

### Pattern 1: Local stdio MCP server (e.g., filesystem)

```python
from contextlib import AsyncExitStack
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters

async def build_agent():
    toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/folder"],
        ),
        tool_filter=["read_file", "list_directory"],  # optional whitelist
    )

    agent = LlmAgent(
        name="filesystem_agent",
        model="gemini-2.5-flash",
        instruction="Help users explore the filesystem.",
        tools=[toolset],  # MCPToolset passed directly
    )
    return agent, toolset
```

### Pattern 2: Remote SSE MCP server (the Partner MCP path)

```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool import SseServerParams

async def build_agent():
    async with MCPToolset(
        connection_params=SseServerParams(
            url="https://mcp.partner.example.com/sse",
            headers={"Authorization": "Bearer <token-from-secret-manager>"},
        )
    ) as toolset:
        tools = await toolset.load_tools()
        agent = LlmAgent(
            name="partner_agent",
            model="gemini-2.5-flash",
            instruction="Use the partner MCP tools to fulfill user requests.",
            tools=tools,
        )
        return agent
```

### Pattern 3: Full app with Runner

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters
from google.genai import types

async def main():
    toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        ),
    )

    agent = LlmAgent(
        model="gemini-2.5-flash",
        name="enterprise_assistant",
        instruction="Help user access their files.",
        tools=[toolset],
    )

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        state={}, app_name="mcp_app", user_id="user_1"
    )

    runner = Runner(
        app_name="mcp_app",
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
    )

    query = "list files in the tests folder"
    content = types.Content(role="user", parts=[types.Part(text=query)])

    async for event in runner.run_async(
        session_id=session.id, user_id=session.user_id, new_message=content
    ):
        print(event)

    await toolset.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Lifecycle gotcha

MCP connections are stateful. You must close them, OR use the async context manager pattern, OR manage an `AsyncExitStack`. If you forget, you'll leak processes / sockets. The async context manager (Pattern 2) is the cleanest.

### Auth pattern

Partner MCP servers need credentials. The pattern is:

1. Get the partner API key (free tier or hackathon track).
2. Store in **Secret Manager**: `gcloud secrets create partner-api-key --data-file=-`.
3. Load at agent startup; pass into `SseServerParams(headers={...})`.
4. Never check into git.

Sources:
- `google/adk-python` repo (`llms-full.txt`) — canonical MCPToolset examples
- https://adk.dev/

---

## 8. The Agent Starter Pack

Repo: https://github.com/GoogleCloudPlatform/agent-starter-pack

### What it is

CLI scaffolder that generates a complete ADK agent project with backend + frontend + CI/CD config in one command. Maintained by GoogleCloudPlatform org (official).

### Bootstrap

```bash
uvx agent-starter-pack create
# or
pip install agent-starter-pack
agent-starter-pack create
```

Requires Python 3.10+.

### Templates shipped

| Template | What it gives you |
|---|---|
| `adk` | Bare ADK ReAct agent. The minimal start. |
| `adk_a2a` | ADK + Agent2Agent Protocol. For multi-agent systems that talk to other agents. |
| `agentic_rag` | ADK + RAG. Document retrieval baked in. |
| `adk_live` | Real-time multimodal RAG (voice/video streaming). |
| `adk_java` | Same as `adk` but Java instead of Python. |
| `langgraph` | ReAct agent using LangGraph. **AVOID for this hackathon** — banned as primary orchestrator per Section 7B. |

### Deployment targets supported

Templates ship pre-configured for **Cloud Run OR Agent Engine**. Pick one at scaffold time.

### CI/CD

Bundles **Cloud Build OR GitHub Actions** workflows. You can wire up auto-deploy on merge.

### Should Abu clone it vs start fresh?

**Clone it.** Specifically `agent-starter-pack create` then pick `adk` template (or `agentic_rag` if your wedge needs RAG). You get:
- Working `Dockerfile`
- Working `pyproject.toml` / `requirements.txt`
- `uvicorn` + `adk api_server` wiring
- Cloud Run deploy script
- Local dev setup
- Test scaffold

That's 2-4 hours of yak-shaving handed to you free. For an 11-day hackathon, this matters.

### Note

The README says "Active development has transitioned to `agents-cli`, though this repository continues receiving critical fixes." [UNVERIFIED whether `agents-cli` is fully GA or just an aspirational successor — the existing starter-pack still works fine, use it.]

---

## 9. Safety & Guardrails

Why a judge cares: hackathons judge on production-readiness. Showing you thought about safety = signal.

### Two layers

**Layer 1: Gemini's built-in safety filters.** Non-configurable filters block CSAM, PII. Configurable filters block 4 harm categories (harassment, hate speech, sexually explicit, dangerous content) at thresholds you set. Configured via `GenerateContentConfig`.

```python
from google.adk.agents import LlmAgent
from google.genai import types

agent = LlmAgent(
    name="safe_agent",
    model="gemini-2.5-flash",
    instruction="...",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
        # safety_settings=[...]  # configure harm category thresholds here
    ),
)
```

**Layer 2: ADK callbacks for app-level guardrails.**

- `before_model_callback` — inspect/block input BEFORE it goes to Gemini.
- `before_tool_callback` — inspect/rewrite/block tool args BEFORE the tool runs.
- `after_model_callback` / `after_tool_callback` — post-process outputs.

You can also run a "guardrail LLM" as a callback — a small Gemini Flash instance whose only job is to classify input as safe/unsafe and return JSON. ADK docs show this pattern explicitly.

```python
# Pseudo-pattern:
def block_unsafe(callback_context, llm_request):
    # call a guardrail LLM
    # if unsafe, return a synthetic LlmResponse that refuses
    # else return None to continue
    ...

agent = LlmAgent(
    ...,
    before_model_callback=block_unsafe,
)
```

### Demo move

In the demo video, show ONE explicit guardrail in action (e.g., "watch what happens when I try to make the agent leak its system prompt"). Judges love this.

---

## 10. Deployment & Demo URL Story

You need a URL the judges can click. Here are the three workable paths, ranked by ease.

### Path A (recommended): Cloud Run + `adk api_server` + tiny static frontend

1. Build agent locally with ADK.
2. `Dockerfile` runs `adk api_server` on `$PORT`.
3. `gcloud run deploy` — get a public URL (e.g. `https://my-agent-xxxx-uc.a.run.app`).
4. Build a small static frontend (Next.js / SvelteKit / vanilla HTML) that calls the Cloud Run REST API. Deploy that to Cloud Run too (or to a static host).
5. Submit the frontend URL.

Pros: Single platform. One billing surface. Public URL for free.
Cons: You write a little frontend.

### Path B: Streamlit on Cloud Run

1. Build agent in a Streamlit `app.py`.
2. Streamlit calls the ADK agent in-process.
3. Container the whole thing, deploy to Cloud Run.

Pros: ZERO frontend code. Streamlit gives you a chat UI out of the box.
Cons: Looks generic. Judges have seen 100 Streamlit demos. Loses on visual polish.

### Path C: Agent Runtime (Agent Engine) + Cloud Run frontend

1. Deploy agent to Agent Engine via `adk deploy agent_engine`.
2. Build a frontend (Next.js or similar) on Cloud Run that uses the Vertex AI Python/JS SDK to call your Agent Engine.
3. Frontend URL is what you submit.

Pros: Cleanest agent infra, gets you observability + Memory Bank for free.
Cons: Two deploy targets. More moving parts. The Vertex AI SDK call from a Node frontend can be fiddly with auth.

### Recommendation

**Path A** for default. **Path B** if you're behind on time and need a working demo above all. **Path C** if you're specifically going after the Arize observability track or want a "production polish" angle.

### Auth for the demo URL

If you require auth on Cloud Run, judges can't easily test. Either:
- Leave Cloud Run unauthenticated (set IAM `allUsers` → `roles/run.invoker`). For a hackathon demo this is fine; just don't put secrets in URLs.
- Or, require a simple shared password in your README that judges paste.

---

## 11. Gotchas List

Quick bullets on traps that will burn time if you don't know about them.

### Billing / account setup

- **RBI debit card mandate burns Indian Google Cloud signups.** If your card is Indian, billing setup may fail. Workarounds: (a) virtual card from Niyo / Fi / Jupiter, (b) ask in the hackathon Discord whether they have a credit-redemption path that doesn't require card-on-file.
- **Free trial credit ($300, 90 days)** and **promotional credit ($100 hackathon)** are DIFFERENT instruments with different redemption flows. The promo credit redeems at `console.cloud.google.com/billing/redeem` with a code. The trial activates when you sign up. They DO stack — but read the small print on each.
- Some hackathon promo credits require your billing account to be a *Cloud Billing* account (not "AI Studio billing"). Make sure you set up Cloud billing first, then redeem.

### Console UI naming

- **The UI says "Studio" not "Agent Builder".** If you Google "Agent Builder console" you'll land on outdated screenshots. The current path is: Console → Agent Platform → Studio.
- **"Agent Engine" is still in the URL paths and docs** even though the official name is "Agent Runtime". Both refer to the same thing.
- **"Vertex AI" still appears in many sidebar items** because the underlying APIs (`aiplatform.googleapis.com`) didn't rename. The PRODUCT renamed; the API namespace didn't.

### Antigravity confusion

- **Antigravity is an IDE (Google's competitor to Cursor / Claude Code).** It is a developer tool you use to write code. It is NOT a deployment target for the hackathon. Don't accidentally try to "ship an Antigravity agent" — that's not a thing.

### Banned competing AI tools in dev workflow

- **Section 7B of the rules bans Claude / Cursor / Copilot from the SUBMISSION CODE.** Read carefully: the ban is on the submission, not on your dev workflow. You can use Claude Code locally to write the code, but the agent that's SUBMITTED must run on Gemini, not Claude. The submitted repo's runtime calls Gemini APIs only.
- **Section 7B also bans LangChain / LangGraph / LlamaIndex as primary orchestrator.** Components used inside ADK tools are fine. The TOP-LEVEL agent loop must be ADK (or Agent Builder visual). If the judges grep your repo and see `langgraph.StateGraph` driving the main loop, you're DQ'd.

### MCP gotchas

- MCP connections leak processes if you don't close them. Use `async with` patterns.
- `tool_filter` on `MCPToolset` is your friend. Partner MCP servers often expose 50+ tools; filtering to the 3 you actually need keeps the Gemini context clean and reduces tool-selection errors.
- For SSE remote MCP servers, **auth is via HTTP headers** (Bearer token). Not a query param.

### Model gotchas

- **Gemini 2.0 Flash is deprecated as of June 1, 2026.** If you copy code from an older tutorial that uses `gemini-2.0-flash`, swap to `gemini-2.5-flash`.
- Pro is 8-10x more expensive than Flash. Don't accidentally leave Pro on for sub-agents.
- Long context (>200k tokens) doubles input pricing on Pro. Be aware.

### ADK version churn

- ADK is still pre-2.0 → 2.0 transition. APIs shift. Pin your version: `pip install google-adk==1.16.0` (or whatever the current stable is when you start).
- The `MCPToolset` import path moved between versions. If `from google.adk.tools.mcp_tool import MCPToolset` fails, try `from google.adk.tools import MCPToolset` or check the current version's docs.

### Demo gotchas

- **`gcloud run deploy` with unauthenticated access requires explicit flag**: `--allow-unauthenticated`. Without it, judges hit 403.
- **Streamlit on Cloud Run needs `--server.port=$PORT` and `--server.address=0.0.0.0`** or Cloud Run health checks fail.

### Partner integration gotchas

- Partner MCP servers via Google Cloud Marketplace bill against your $100 credit. Direct signups don't. If you have a choice, go through Marketplace.
- Some partners (MongoDB Atlas, Elastic Cloud) have generous free tiers. Use those for the hackathon; don't burn credit on infra.

---

## 12. Open Questions / [UNVERIFIED]

Things I couldn't pin down with confidence — verify before you commit.

- **[UNVERIFIED] Exact Gemini 3.1 Pro / Flash pricing.** The 3.1 family was announced at Next 2026 but the live pricing page I pulled still shows 2.5 as primary. May be that 3.x is still preview / private GA. Check `ai.google.dev/gemini-api/docs/pricing` closer to submission.
- **[UNVERIFIED] Whether the hackathon allows Gemini 3.x or restricts to 2.5.** Probably allows both, but the safe bet is 2.5 Flash/Pro which are definitively stable.
- **[UNVERIFIED] `agents-cli` vs `agent-starter-pack` status.** The starter-pack README hints at a successor. Stick with `agent-starter-pack` for now since it's the one with full template coverage.
- **[UNVERIFIED] Exact MCP import paths in latest ADK.** The pattern `from google.adk.tools.mcp_tool import MCPToolset` is from ADK 1.x docs. Verify against `pip show google-adk` and the current docs.
- **[UNVERIFIED] Whether Agent Runtime / Agent Engine charges separately from model inference.** I expect yes (runtime hours + token costs), but didn't find a clean pricing breakdown. Budget assumption: model tokens dominate, runtime is small fraction.
- **[UNVERIFIED] Devpost FAQ specifics on $100 credit.** I read the Resources page; the Updates page may have additional info on the exact credit terms.
- **[UNVERIFIED] List of officially blessed "Partner MCP servers" for the hackathon.** The Devpost resources page lists six integration partners (Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace) but doesn't explicitly say which expose MCP servers. Probably all of them, but confirm in the partner-specific track docs.

---

## Sources (for the future agent reading this)

- https://cloud.google.com/products/gemini-enterprise-agent-platform
- https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-enterprise-agent-platform
- https://en.wikipedia.org/wiki/Gemini_Enterprise_Agent_Platform
- https://adk.dev/ (canonical ADK docs, redirected from google.github.io/adk-docs)
- https://github.com/google/adk-python
- https://github.com/GoogleCloudPlatform/agent-starter-pack
- https://ai.google.dev/gemini-api/docs/pricing
- https://google.github.io/adk-docs/deploy/agent-engine/
- https://cloud.google.com/blog/topics/developers-practitioners/from-code-to-cloud-three-labs-for-deploying-your-ai-agent
- https://rapid-agent.devpost.com/resources
- https://rapid-agent.devpost.com/updates
- https://uibakery.io/blog/vertex-ai-agent-builder (third-party 2026 guide — good supplementary)
- https://gcpstudyhub.com/blog/vertex-ai-replaced-by-gemini-enterprise-agent-platform (rename context)
- https://thenewstack.io/google-gemini-agent-platform/ (Next 2026 announcement coverage)
- https://medium.com/google-cloud/end-to-end-ai-agent-on-gcp-adk-bigquery-mcp-agent-engine-and-cloud-run-4843fec27c13 (end-to-end pattern walkthrough)
- Context7 corpus: `/google/adk-python` (1225 snippets) and `/arjunprabhulal/adk-python-mcp-client` (MCP client examples)

---

## TL;DR for future-Abu

1. Stack you're using: **ADK (Python) + Gemini 2.5 Flash + at least one Partner MCP server (via `MCPToolset` over SSE) + Cloud Run for hosting**.
2. Scaffold with: `uvx agent-starter-pack create` → pick `adk` template.
3. Default model: `gemini-2.5-flash`. Bump to `gemini-2.5-pro` only on the root reasoning agent if needed.
4. Demo URL: Cloud Run (`--allow-unauthenticated`).
5. The console UI calls Agent Builder "Studio" now. Vertex AI is now Gemini Enterprise Agent Platform. Don't get confused by outdated tutorials.
6. Don't put LangChain / LangGraph / LlamaIndex as primary orchestrator. Don't ship code that runs Claude / Cursor / Copilot. Both = DQ.
7. $100 credit is plenty if you default to Flash. Burn-rate alarm only matters if you do RAG ingestion at scale.
