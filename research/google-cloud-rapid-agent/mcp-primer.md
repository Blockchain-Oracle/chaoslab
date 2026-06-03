# MCP Protocol Primer — Google Cloud Rapid Agent Hackathon

**Audience:** Abu (blockchain-native, needs 15-min grounding before talking to MCP-judges).
**Last verified:** 2026-06-02
**Why this matters:** Every partner track (Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace) ships an MCP server. The rules say you must integrate with it. Calling REST endpoints directly = disqualification risk.

---

## 1. What MCP is, plainly

The **Model Context Protocol** is an open standard, originated by Anthropic in late 2024, for connecting LLM applications to external systems (data + tools + workflow templates).

Think USB-C for AI tools. Before MCP, every LLM client had a bespoke integration with every tool. With MCP, anyone who exposes their service as an "MCP server" is automatically callable from any MCP-aware client (Claude Desktop, ChatGPT, Cursor, VS Code, Google ADK agents, etc.).

Verbatim from the spec ([modelcontextprotocol.io](https://modelcontextprotocol.io/)):

> "MCP (Model Context Protocol) is an open-source standard for connecting AI applications to external systems… Think of MCP like a USB-C port for AI applications."

**Adoption signal as of 2026-06-02:**
- Anthropic (creator) — Claude Desktop, Claude Code
- OpenAI — ChatGPT MCP connectors
- Google — Agent Development Kit (ADK) ships `McpToolset`
- Microsoft — VS Code Copilot supports MCP
- Cursor, Zed, MCPJam, Sentry, Notion, Figma, GitHub, Atlassian, Stripe (all ship official MCP servers)

It is no longer "Anthropic's protocol." It is the cross-vendor agentic-tool standard.

---

## 2. The mental model

Three roles. Don't confuse them. They are NOT synonyms.

```
+--------------------------------------------------------+
|              MCP HOST   (the AI application)           |
|  e.g., Claude Desktop, VS Code, Cursor,                |
|        Google ADK agent, custom Gemini app             |
|                                                        |
|  Spawns one MCP CLIENT per server it connects to:      |
|                                                        |
|   +--------------+   +--------------+   +-----------+  |
|   | MCP Client A |   | MCP Client B |   | Client C  |  |
|   +------+-------+   +------+-------+   +-----+-----+  |
+----------|------------------|----------------|--------+
           |                  |                |
   dedicated conn     dedicated conn   dedicated conn
           |                  |                |
           v                  v                v
   +---------------+  +---------------+  +-----------------+
   | MCP Server A  |  | MCP Server B  |  | MCP Server C    |
   | (local stdio) |  | (local stdio) |  | (remote HTTP)   |
   | e.g. fs       |  | e.g. sqlite   |  | e.g. Sentry,    |
   |               |  |               |  | MongoDB, Arize  |
   +---------------+  +---------------+  +-----------------+
```

- **Host** — the AI app. Manages all clients. Owns the LLM. (Your ADK agent IS the host.)
- **Client** — the connector. One per server. Maintains a dedicated session.
- **Server** — the tool/data provider. Stateless or stateful. Local (stdio) or remote (HTTP).

Source: [Architecture overview](https://modelcontextprotocol.io/docs/learn/architecture).

**Wire protocol:** JSON-RPC 2.0 over the chosen transport. Stateful by default. Lifecycle = initialize → capability negotiation → tool/resource use → terminate.

---

## 3. What MCP servers expose

Three **primitives**. Memorize these — judges will ask.

| Primitive  | What it is                                                  | Example                                                                                          |
| ---------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **Tools**  | Executable functions the LLM can invoke (verbs / actions)   | `query_database(sql)`, `send_slack_message(channel, text)`, `mongodb.find(collection, filter)`   |
| **Resources** | Read-only data sources, addressable by URI (nouns / context) | `file:///etc/config.json`, `mongodb://schema/users`, `arize://trace/abc123`                  |
| **Prompts**  | Reusable templates the server suggests to the host        | "Investigate this trace" template that pre-fills system prompt + few-shot examples               |

Discovery methods: `tools/list`, `resources/list`, `prompts/list`. Execution: `tools/call`, `resources/read`, `prompts/get`.

Servers can also use **client-exposed primitives** going the other direction:
- **Sampling** — server asks host to run an LLM completion (so the server doesn't need its own model)
- **Elicitation** — server asks the user for input mid-flight (confirmation, missing field)
- **Logging** — server streams logs to host

Source: [Architecture overview](https://modelcontextprotocol.io/docs/learn/architecture).

---

## 4. Transports

The spec defines **two standard transports** as of protocol version 2025-11-25. SSE-only is deprecated.

| Transport            | When to use                                                                                                  | Notes                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| **stdio**            | Server runs as a local subprocess on the same machine as the host. Newline-delimited JSON-RPC over stdin/stdout. | Lowest latency. No auth needed (process-level trust). Best for dev / local tools / npm-installed servers. |
| **Streamable HTTP**  | Remote servers. Multi-client. HTTP POST for client→server, optional SSE for server→client streaming.        | Auth via bearer / API key / OAuth. Session ID via `MCP-Session-Id` header. Replaces old HTTP+SSE transport from 2024-11-05. |
| ~~HTTP+SSE (legacy)~~ | Deprecated. Still supported for backward-compat (servers may host both endpoints).                          | Don't build new code on this.                                                                      |

**Rule of thumb:**
- Local CLI MCP server → **stdio** (`StdioServerParameters(command='npx', args=[...])`)
- Cloud-hosted partner MCP server (MongoDB, Arize, etc.) → **Streamable HTTP** with API-key header

**Security gotcha (Streamable HTTP):** servers MUST validate the `Origin` header to prevent DNS rebinding attacks, and SHOULD bind to `127.0.0.1` not `0.0.0.0` when running locally. Don't ship an HTTP MCP server without this.

Source: [Transport specification](https://modelcontextprotocol.io/specification/latest/basic/transports).

---

## 5. MCP in Google Cloud Agent Builder / ADK

The Agent Development Kit (ADK) is Google's open-source agent framework. It is the **expected stack for this hackathon** (Devpost overview says "build with Gemini 3 using Google Cloud Agent Builder and integrate partner MCP servers").

ADK supports MCP in **both directions**:
1. **Consume** — an ADK agent acts as MCP host, talking to partner MCP servers
2. **Expose** — wrap ADK tools so other clients can call them via MCP

### Consuming an MCP server from an ADK agent

```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

# --- Remote HTTP MCP server (the partner-track pattern) ---
mongodb_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mcp.mongodb.com/v1/mcp",   # example URL
        headers={
            "X-Goog-Api-Key": "YOUR_API_KEY",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    ),
    tool_filter=["find", "aggregate"],  # optional — restrict surface area
)

# --- Local stdio MCP server (npm-installed, dev-mode) ---
fs_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        )
    )
)

root_agent = LlmAgent(
    model="gemini-flash-latest",
    name="rapid_agent",
    instruction="You are an investigative agent. Use the MongoDB tools to query data.",
    tools=[mongodb_tools, fs_tools],
)
```

Key class: `McpToolset` — drop it into the `tools=[]` list and ADK handles handshake, capability negotiation, tool discovery, JSON-RPC marshaling.

### Exposing ADK tools as an MCP server

```python
from mcp.server.lowlevel import Server
from mcp import types as mcp_types
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

adk_tool = FunctionTool(your_function)
app = Server("my-server")

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [adk_to_mcp_tool_type(adk_tool)]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    if name == adk_tool.name:
        result = await adk_tool.run_async(args=arguments, tool_context=None)
        return [mcp_types.TextContent(type="text", text=str(result))]
```

Internally ADK uses **FastMCP** for server-side plumbing.

**Production deployment caveat** (from ADK docs): "Agent definitions must be synchronous for production deployments — asynchronous patterns don't work when deploying to Cloud Run, GKE, or Agent Runtime environments." [UNVERIFIED whether this still holds in 2026 ADK release — check before submission].

Sources:
- [ADK MCP overview](https://adk.dev/mcp/)
- [ADK MCP tools detailed](https://adk.dev/tools-custom/mcp-tools/)
- [Codelab: Getting Started with MCP, ADK and A2A](https://codelabs.developers.google.com/codelabs/currency-agent)
- [Codelab: Build a Google Workspace AI Agent with ADK and MCP](https://codelabs.developers.google.com/google-workspace-mcp-adk)

---

## 6. Why MCP matters for this hackathon

Every partner has an MCP server. The rules implicitly say "use it via MCP, not via raw API". Concretely:

| Track     | Partner MCP server (expected)         | What it likely exposes                                       |
| --------- | ------------------------------------- | ------------------------------------------------------------ |
| Arize     | observability MCP                     | tools: get_trace, query_evals; resources: model_versions     |
| Elastic   | search MCP                            | tools: search, kql_query; resources: indices                 |
| Fivetran  | data-pipeline MCP                     | tools: trigger_sync, get_connector_status                    |
| GitLab    | git/issues MCP                        | tools: create_issue, list_merge_requests, run_pipeline        |
| MongoDB   | document-DB MCP                       | tools: find, aggregate, insert; resources: collections, schemas |
| Dynatrace | observability MCP                     | tools: get_problems, query_metrics; resources: entities      |

[UNVERIFIED — confirm exact tool names by reading each partner's MCP server docs once the hackathon resources page is fully populated.]

**Judging implication:** the "Technological Implementation" criterion rewards real MCP integration. A demo where the agent visibly calls `tools/list` against the partner MCP server, then `tools/call` to act, is the strongest signal you can give judges. Reverse: an agent that imports the partner's Python SDK and calls REST directly = checks the wrong box.

---

## 7. Common gotchas

1. **Tool-name collisions.** If you mount MongoDB MCP and Filesystem MCP both, and both have a `search` tool, the LLM may get confused. Use `tool_filter=[...]` on `McpToolset` to scope, or rely on the namespacing the server provides (e.g. `mongodb_search` vs `fs_search`).
2. **Auth on Streamable HTTP.** Bearer tokens go in the `Authorization` header. API keys often go in `X-*-Api-Key` (Google convention) or `X-Api-Key`. The spec recommends OAuth for production. Hackathon: an API key + env var is fine.
3. **Transport mismatch.** Don't try to talk stdio to a remote server. Don't try to spawn a hosted SaaS as a subprocess. Match transport to deployment.
4. **Schema drift.** MCP servers can update their `inputSchema` between versions. ADK caches the schema at startup via `tools/list`. If the server signals `listChanged: true`, you may get a `notifications/tools/list_changed` and need to refresh. Restart your agent if you change server versions mid-build.
5. **Session management (HTTP).** The server returns `MCP-Session-Id` on initialize. You MUST include it on subsequent requests. A 404 means session expired — reinit.
6. **`Origin` header attacks.** If you build your own HTTP MCP server, validate `Origin` and bind to localhost in dev. Otherwise a malicious website can hit your local server via DNS rebinding.
7. **Stdio output discipline.** A server that writes ANY non-JSON-RPC text to stdout corrupts the channel. Logs MUST go to stderr only. Trips up Python servers that have a stray `print()` left in.
8. **Async vs sync in ADK production.** See section 5 caveat. Async agent definitions break Cloud Run / GKE deployment.

---

## 8. Sources

- [modelcontextprotocol.io — landing](https://modelcontextprotocol.io/)
- [Architecture overview](https://modelcontextprotocol.io/docs/learn/architecture)
- [Transport specification](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [MCP GitHub org](https://github.com/modelcontextprotocol) — official SDKs (Python, TypeScript, Kotlin, Swift)
- [Reference MCP servers](https://github.com/modelcontextprotocol/servers) — filesystem, git, sqlite, etc.
- [ADK MCP docs (overview)](https://adk.dev/mcp/)
- [ADK MCP tools (code samples)](https://adk.dev/tools-custom/mcp-tools/)
- [Codelab: ADK + MCP + A2A currency agent](https://codelabs.developers.google.com/codelabs/currency-agent)
- [Codelab: Google Workspace MCP + ADK](https://codelabs.developers.google.com/google-workspace-mcp-adk)
- [Codelab: Google's Agent Stack — ADK, A2A, MCP](https://codelabs.developers.google.com/instavibe-adk-multi-agents/instructions)
- [Arjun Prabhu — ADK MCP deep dive](https://arjunprabhulal.com/adk-mcp-deep-dive/)
- [DeepWiki — ADK MCP Tools](https://deepwiki.com/google/adk-docs/4.4-mcp-tools)
