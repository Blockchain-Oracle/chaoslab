# 06 — Open Standards & Protocols for Agent Observability and Chaos Testing

> Spec-level reference. Pure technical documentation, no opinions. Pulled from official spec sites in May–June 2026. Items marked `[UNVERIFIED]` could not be confirmed from a single primary source and rely on secondary write-ups (URLs cited inline).

This file goes deeper than `brainstorm/04-protocol-wedges.md`, `mcp-primer.md`, and `02b-gemini-enterprise-agent-platform.md`. Where those earlier passes summarized, this file captures spec text, JSON schemas, attribute lists, method names, and error code ranges that a downstream agent designing fault injection / observability tooling would need to consume the wire.

---

## Table of Contents

1. Model Context Protocol (MCP) — spec 2025-11-25
2. A2A (Agent-to-Agent) Protocol v1.0
3. OpenInference span conventions
4. OpenTelemetry GenAI semantic conventions
5. Agent Payments Protocol (AP2)
6. Universal Commerce Protocol (UCP)
7. Agent-to-UI Protocol (A2UI)
8. OWASP Top 10 for LLM Applications (2025)
9. OWASP Top 10 for Agentic Applications (2026 / ASI)
10. MITRE ATLAS
11. NIST AI RMF & GenAI Profile (AI 600-1)
12. ARC-AGI and agent benchmarks
13. Academic eval frameworks (HELM, BIG-bench, LMSYS, METR)
14. Red-team-specific datasets & attack technique families
15. Interop: OpenInference + A2A + MCP unified trace story
16. Consolidated source list

---

## 1. Model Context Protocol (MCP) — Deep Technical Reference

### 1.1 Current Spec Version

**Spec date: `2025-11-25`** (the dated string is the literal protocol version exchanged on the wire). Source of truth is the TypeScript schema at `github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.ts`. Source: <https://modelcontextprotocol.io/specification/>.

Earlier dated versions seen in the wild:

- `2024-11-05` — original HTTP+SSE transport (deprecated)
- `2025-03-26` — added Streamable HTTP transport, assumed by servers that receive no `MCP-Protocol-Version` header
- `2025-06-18` — intermediate
- `2025-11-25` — current; added `tasks` capability for async/agentic patterns, refined OAuth (Client ID Metadata Documents)

### 1.2 Architecture

Three roles, JSON-RPC 2.0 messaging:

- **Host** — LLM application that initiates connections (the user-facing app, e.g. Claude Desktop, Cursor)
- **Client** — connector inside the host, one per server connection
- **Server** — service exposing context (resources), templated workflows (prompts), and callable functions (tools)

MCP is explicitly modeled after the Language Server Protocol (LSP). Connections are stateful; capabilities are negotiated.

### 1.3 Wire Format — JSON-RPC 2.0

**Request:**

```ts
{
  jsonrpc: "2.0";
  id: string | number;   // MUST NOT be null; MUST NOT be reused in session
  method: string;
  params?: { [key: string]: unknown };
}
```

**Result response:**

```ts
{
  jsonrpc: "2.0";
  id: string | number;
  result: { [key: string]: unknown };
}
```

**Error response:**

```ts
{
  jsonrpc: "2.0";
  id?: string | number;
  error: { code: number; message: string; data?: unknown };
}
```

**Notification** (no response expected):

```ts
{
  jsonrpc: "2.0";
  method: string;
  params?: { [key: string]: unknown };
}
```

All messages MUST be UTF-8.

Standard JSON-RPC error code ranges apply: `-32700` parse error, `-32600` invalid request, `-32601` method not found, `-32602` invalid params, `-32603` internal error, server errors `-32000` to `-32099`.

### 1.4 Lifecycle

**Three phases:** Initialization → Operation → Shutdown.

**Initialization sequence (REQUIRED first interaction):**

1. Client → Server: `initialize` request
2. Server → Client: `initialize` response
3. Client → Server: `notifications/initialized`

Before the server has responded to `initialize`, the client SHOULD NOT send anything but pings. Before the server has received `notifications/initialized`, the server SHOULD NOT send anything but pings and `logging` messages.

**`initialize` request example (2025-11-25):**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {},
      "elicitation": { "form": {}, "url": {} },
      "tasks": {
        "requests": {
          "elicitation": { "create": {} },
          "sampling": { "createMessage": {} }
        }
      }
    },
    "clientInfo": {
      "name": "ExampleClient",
      "title": "Example Client Display Name",
      "version": "1.0.0",
      "description": "An example MCP client application",
      "icons": [
        {
          "src": "https://example.com/icon.png",
          "mimeType": "image/png",
          "sizes": ["48x48"]
        }
      ],
      "websiteUrl": "https://example.com"
    }
  }
}
```

**`initialize` response example:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "logging": {},
      "prompts": { "listChanged": true },
      "resources": { "subscribe": true, "listChanged": true },
      "tools": { "listChanged": true },
      "tasks": {
        "list": {},
        "cancel": {},
        "requests": { "tools": { "call": {} } }
      }
    },
    "serverInfo": { "name": "ExampleServer", "version": "1.0.0" },
    "instructions": "Optional instructions for the client"
  }
}
```

**Then:** `{"jsonrpc": "2.0", "method": "notifications/initialized"}`.

**Version negotiation:** Client sends latest version it supports. If server supports that version, server echoes it. Otherwise server returns latest version _it_ supports. Client disconnects if it can't speak the server's version. Mismatch error example:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Unsupported protocol version",
    "data": { "supported": ["2024-11-05"], "requested": "1.0.0" }
  }
}
```

**Shutdown:**

- stdio: client closes stdin → waits → SIGTERM → SIGKILL escalation
- HTTP: close associated HTTP connection(s)

**Timeouts:** Per-request, configurable. SHOULD support reset-on-progress-notification but MUST enforce a hard ceiling.

### 1.5 Capabilities Negotiation

Each side declares what it offers in the `capabilities` object:

| Side   | Capability     | Description                                 |
| ------ | -------------- | ------------------------------------------- |
| Client | `roots`        | Filesystem roots exposure                   |
| Client | `sampling`     | Server can ask client LLM to generate       |
| Client | `elicitation`  | Server can ask user for input (form or URL) |
| Client | `tasks`        | Task-augmented (async) client requests      |
| Client | `experimental` | Non-standard custom features                |
| Server | `prompts`      | Templated prompts                           |
| Server | `resources`    | Readable data sources                       |
| Server | `tools`        | Callable functions                          |
| Server | `logging`      | Structured log message emission             |
| Server | `completions`  | Argument autocompletion                     |
| Server | `tasks`        | Task-augmented server requests              |
| Server | `experimental` | Custom features                             |

Sub-capabilities:

- `listChanged: true` — emits notifications when list of prompts/resources/tools changes
- `subscribe: true` — supports subscriptions to individual resource changes (resources only)

### 1.6 Transports

Two officially defined; custom permitted.

**stdio transport:**

- Client spawns server as subprocess
- Messages = newline-delimited JSON-RPC (no embedded newlines)
- Server `stderr` is free-form logs; client MAY ignore
- Server MUST NOT write non-MCP data to stdout

**Streamable HTTP transport** (replaced HTTP+SSE from 2024-11-05):

Single endpoint (e.g. `https://example.com/mcp`) handles both POST and GET.

POST contract (client→server):

- Body: single JSON-RPC request, notification, or response
- Headers: `Accept: application/json, text/event-stream`
- If body is a notification or response: server returns `202 Accepted` with no body
- If body is a request: server EITHER returns `Content-Type: application/json` (single JSON response) OR `Content-Type: text/event-stream` (opens SSE stream that eventually delivers the JSON-RPC response)
- During an SSE stream, server MAY send unrelated requests/notifications interleaved
- After response is sent, server SHOULD terminate the stream

GET contract (client opens long-lived stream from server):

- Headers: `Accept: text/event-stream`
- Server returns either SSE stream OR `405 Method Not Allowed`
- Server MUST NOT send JSON-RPC responses on this stream unless resuming a prior request

Required headers:

- `MCP-Protocol-Version: 2025-11-25` — on every subsequent client request after init. If missing, server defaults to `2025-03-26`. Invalid version → `400 Bad Request`.
- `MCP-Session-Id` — optional; server MAY return one in init response, client MUST echo it on all subsequent requests. Server MAY 404 on stale session IDs; client MUST then reinitialize. Client MAY DELETE the endpoint to terminate.

Resumability via SSE `Last-Event-Id` header. Servers MAY attach an `id` to SSE events; clients reconnecting send `Last-Event-Id: <id>` to replay missed messages from that specific stream.

Security:

- MUST validate `Origin` header (DNS rebinding defense) → 403 on bad origin
- SHOULD bind to `127.0.0.1` when running locally
- SHOULD use auth on remote deployments

**Deprecated HTTP+SSE** (protocol 2024-11-05):

- Two endpoints: `/sse` (GET, long-lived stream) and a separate POST endpoint announced via an `endpoint` SSE event
- Servers can dual-host both transports for backwards compatibility

### 1.7 Authorization

MCP authorization is OPTIONAL but specified for HTTP. STDIO clients SHOULD use environment variables, not OAuth.

Standards stack:

- OAuth 2.1 (draft-ietf-oauth-v2-1-13)
- RFC 8414 — OAuth 2.0 Authorization Server Metadata
- RFC 7591 — Dynamic Client Registration
- RFC 9728 — OAuth 2.0 Protected Resource Metadata (PRM)
- RFC 8707 — Resource Indicators
- draft-ietf-oauth-client-id-metadata-document-00 — CIMD

Mandatory client behaviors:

- MUST implement PKCE with `S256` challenge method
- MUST send `resource` parameter (RFC 8707) on every authorization + token request
- MUST verify PKCE support via `code_challenge_methods_supported` in AS metadata
- MUST parse `WWW-Authenticate` headers on 401 responses
- MUST follow PRM discovery to find AS location
- MUST NOT include access tokens in URI query strings
- MUST NOT forward tokens upstream (token passthrough is explicitly forbidden)
- MUST send `Authorization: Bearer <token>` on every HTTP request, not just first

Server behaviors:

- MUST implement RFC 9728 PRM
- MUST validate that incoming tokens were specifically issued for this resource (audience binding)
- MUST return 401 with `WWW-Authenticate: Bearer resource_metadata="<url>", scope="..."`
- MUST return 403 with `error="insufficient_scope"` for scope upgrades
- MUST validate exact redirect URIs against registered set

Client registration order of preference:

1. Pre-registered static credentials
2. Client ID Metadata Documents (CIMD) — client hosts a JSON metadata doc at an HTTPS URL, which IS the client_id
3. Dynamic Client Registration (RFC 7591)
4. Prompt user

CIMD advertised via `client_id_metadata_document_supported: true` in AS metadata.

Step-up authorization: client receives `403 insufficient_scope` → reauthorizes with widened scope set → retries.

### 1.8 Server Features

Three primitives by control hierarchy:

| Primitive | Controller  | Description                        | Example                    |
| --------- | ----------- | ---------------------------------- | -------------------------- |
| Prompts   | User        | Templates invoked by user choice   | Slash commands             |
| Resources | Application | Contextual data attached by client | File contents, git history |
| Tools     | Model       | Functions for the LLM to call      | API calls, file writes     |

#### 1.8.1 Tools

Methods:

- `tools/list` — request with optional `cursor` for pagination; returns `{ tools: Tool[], nextCursor?: string }`
- `tools/call` — request with `{ name, arguments }`; returns `CallToolResult`
- `notifications/tools/list_changed` — server→client when tool catalog mutates

**Tool schema:**

```json
{
  "name": "string (1-128 chars, [A-Za-z0-9_.-])",
  "title": "optional human-readable name",
  "description": "string",
  "icons": "optional Icon[]",
  "inputSchema": "JSON Schema (defaults to 2020-12)",
  "outputSchema": "optional JSON Schema",
  "annotations": "ToolAnnotations",
  "execution": { "taskSupport": "forbidden|optional|required" }
}
```

**Tool annotations** (untrusted unless server is trusted):

- `readOnlyHint: boolean` — tool does not modify state
- `destructiveHint: boolean` — may delete or otherwise destroy
- `idempotentHint: boolean` — repeated calls produce the same result
- `openWorldHint: boolean` — touches systems beyond the local environment

**CallToolResult:**

```ts
{
  content: ContentItem[];   // array of text|image|audio|resource_link|resource
  isError?: boolean;
  structuredContent?: object;   // JSON object matching outputSchema
}
```

Content item types:

- `text` — `{ type: "text", text: string }`
- `image` — `{ type: "image", data: base64, mimeType }`
- `audio` — `{ type: "audio", data: base64, mimeType }`
- `resource_link` — `{ type: "resource_link", uri, name, description?, mimeType? }`
- `resource` (embedded) — `{ type: "resource", resource: { uri, mimeType, text|blob, annotations? } }`

All content items support `annotations: { audience, priority, lastModified }`.

**Error handling — two layers:**

- _Protocol errors_ — JSON-RPC errors (unknown tool, malformed request) — `-32602`, etc.
- _Tool execution errors_ — `result.isError: true` with error text in content; the LLM can self-correct. Clients SHOULD pass these back to the LLM.

#### 1.8.2 Resources

Methods:

- `resources/list` — paginated; returns `Resource[]`
- `resources/templates/list` — returns `ResourceTemplate[]` (URI templates)
- `resources/read` — `{ uri }` → `{ contents: ResourceContent[] }`
- `resources/subscribe` — `{ uri }`; server emits `notifications/resources/updated` when changed
- `resources/unsubscribe`
- `notifications/resources/list_changed`
- `notifications/resources/updated`

URI schemes: `file://`, `https://`, custom schemes, `screen://`, etc.

#### 1.8.3 Prompts

Methods:

- `prompts/list` — paginated
- `prompts/get` — `{ name, arguments }` → `{ description?, messages: PromptMessage[] }`
- `notifications/prompts/list_changed`

Prompt schema: `{ name, description, arguments: PromptArgument[], icons? }`.

#### 1.8.4 Completion / Logging / Pagination

- `completion/complete` — argument autocompletion (`ref` = `{type: "ref/prompt"|"ref/resource", ...}`, `argument: { name, value }`)
- `logging/setLevel` — client sets server log threshold (`debug|info|notice|warning|error|critical|alert|emergency`)
- `notifications/message` — server emits structured log

Pagination: opaque `cursor` strings; server returns `nextCursor` when more data exists.

### 1.9 Client Features

#### 1.9.1 Sampling — Server-Initiated LLM Generation

Method `sampling/createMessage`. The server asks the host's LLM to generate. The client/user gates this; the host's UI is expected to gate every sampling request.

Request shape (abbreviated):

```ts
{
  messages: SamplingMessage[],
  modelPreferences?: { hints?, costPriority?, speedPriority?, intelligencePriority? },
  systemPrompt?: string,
  includeContext?: "none" | "thisServer" | "allServers",
  temperature?, maxTokens, stopSequences?, metadata?
}
```

Response: `{ role, content, model, stopReason }`.

#### 1.9.2 Roots — Filesystem Boundaries

Method `roots/list` (server→client). Returns `{ roots: [{ uri: "file://...", name?: string }] }`.

`notifications/roots/list_changed` when client's roots change.

#### 1.9.3 Elicitation — Server Asks User

Method `elicitation/create`. Two subforms:

- `form` — structured form fields the client renders
- `url` — server returns a URL the client opens in a browser

User-approved → response carries collected data. User-rejected → declined error.

### 1.10 Utilities

- **Cancellation** — `notifications/cancelled` with target request ID. Either side may cancel.
- **Progress** — `notifications/progress` with `{ progressToken, progress, total? }`. Requestor opts in by including `progressToken` in `_meta` of the original request.
- **Ping** — `ping` request returns empty result.
- **Tasks** (new in 2025-11-25) — augments tool calls with async lifecycle. Server returns a task ID; client polls or subscribes. Capability: `tasks: { list, cancel, requests: { ... } }`.
- **`_meta`** — reserved key on params, params items, results for protocol-level annotations. Prefix `io.modelcontextprotocol/`, `dev.mcp/`, etc. are reserved.

### 1.11 Trust & Safety (Spec Section)

Implementors SHOULD:

- Require explicit user consent before exposing data or invoking tools
- Treat tool annotations as untrusted
- Require approval per sampling request
- Provide clear UI for what's exposed to the LLM
- Implement timeouts, rate limits, audit logging

The protocol does not enforce any of this — it's the host's responsibility.

---

## 2. A2A (Agent-to-Agent) Protocol v1.0

Originally announced by Google. Donated to the Linux Foundation. Spec at `a2a-protocol.org/latest/specification/`. Source: <https://a2a-protocol.org>.

### 2.1 Version & Release Status

- **v1.0.0** — stable (current). Previous releases: 0.3.0, 0.2.6, 0.1.0.
- Version negotiated via `A2A-Version` HTTP header in `Major.Minor` format.

### 2.2 Transports

Three protocol bindings, defined verbatim:

1. **JSON-RPC 2.0** — method-based RPC over HTTPS (the default / reference binding)
2. **gRPC** — service-based with Protobuf serialization
3. **HTTP+JSON / REST** — RESTful endpoints with JSON

### 2.3 Agent Card

Discovery document; typically served at `/.well-known/agent-card.json`.

Schema fields:

- `name`, `description`, `url`, `version`
- `provider` — `{ organization, url, ... }`
- `capabilities` — `{ streaming: bool, pushNotifications: bool, extendedAgentCard: bool }`
- `defaultInputModes`, `defaultOutputModes` — supported MIME types
- `skills[]` — array of `Skill` objects
- `securitySchemes` — auth method definitions (mirrors OpenAPI Security Schemes)
- `security` — required scheme refs
- `interfaces[]` — protocol binding URLs with optional tenant routing

Extended agent card (auth-gated, fuller capability list) requested via `agent/getAuthenticatedExtendedCard` per implementations.

### 2.4 Skill Schema

Each `Skill` declares:

- `id` (unique within agent), `name`, `description`
- `tags[]` for taxonomy
- `examples[]` — sample inputs
- `inputModes[]`, `outputModes[]` — overrides defaults

### 2.5 Task Object

```ts
{
  id: string,           // server-generated unique
  contextId: string,    // groups related tasks/messages
  status: { state: TaskState, message?: Message, timestamp: string },
  artifacts: Artifact[],
  history: Message[],
  metadata: { [k: string]: any }
}
```

**TaskState enum** (verbatim from the proto/JSON-RPC binding):

- `TASK_STATE_SUBMITTED`
- `TASK_STATE_WORKING`
- `TASK_STATE_INPUT_REQUIRED` — agent needs user input to continue
- `TASK_STATE_COMPLETED`
- `TASK_STATE_FAILED`
- `TASK_STATE_CANCELED`
- `TASK_STATE_REJECTED`
- `TASK_STATE_AUTH_REQUIRED`

### 2.6 Message Format

```ts
{
  messageId: string,            // creator-generated, unique
  contextId?: string,
  taskId?: string,
  role: "ROLE_USER" | "ROLE_AGENT",
  parts: Part[],
  referenceTaskIds?: string[],
  metadata?: object,
  extensions?: object[]
}
```

**Part type (oneof):**

- `text` — string content
- `raw` — binary (base64 in JSON)
- `url` — external file reference
- `data` — structured JSON

Optional on every part: `mediaType`, `filename`.

### 2.7 Core Methods (JSON-RPC binding)

| Method                                          | Purpose                                |
| ----------------------------------------------- | -------------------------------------- |
| `message/send`                                  | Send a message; may auto-create a task |
| `message/stream` (a.k.a. `tasks/sendSubscribe`) | Send + open SSE stream of updates      |
| `tasks/get`                                     | Poll a task by ID                      |
| `tasks/list`                                    | Paginated task listing with filters    |
| `tasks/cancel`                                  | Request cancellation                   |
| `tasks/resubscribe`                             | Reattach SSE stream to existing task   |
| `tasks/pushNotificationConfig/set`              | Register webhook for push updates      |
| `tasks/pushNotificationConfig/get`              | Read webhook config                    |
| `tasks/pushNotificationConfig/list`             |                                        |
| `tasks/pushNotificationConfig/delete`           |                                        |
| `agent/getAuthenticatedExtendedCard`            | Authenticated card                     |

Note: depending on transport binding, method names differ (gRPC uses `SendMessage`, `SubscribeToTask`, etc.).

### 2.8 Streaming (SSE)

`message/stream` returns SSE. Each event's `data:` is a JSON `StreamResponse` wrapping one of:

- `task` — full Task object (e.g., on creation)
- `message` — agent message
- `statusUpdate` — `TaskStatusUpdateEvent { taskId, status, final: bool }`
- `artifactUpdate` — `TaskArtifactUpdateEvent { taskId, artifact, append?, lastChunk? }`

### 2.9 Push Notifications (Webhooks)

When `capabilities.pushNotifications: true`, the client can register webhook URLs with optional auth:

```json
{
  "url": "https://client.example.com/a2a/webhook",
  "token": "client-defined-bearer",
  "authentication": { "schemes": ["Bearer"], "credentials": "..." }
}
```

Server POSTs `StreamResponse`-shaped payloads to the webhook on task state changes.

### 2.10 Authentication Schemes

Mirrors OpenAPI security types:

- API Key (header / query / cookie)
- HTTP Basic / Bearer
- OAuth 2.0 — flows: `AuthorizationCode`, `ClientCredentials`, `DeviceCode`, `Implicit` (discouraged)
- OpenID Connect
- Mutual TLS (mTLS)

### 2.11 Errors

**Standard A2A error codes** (protocol-agnostic names):

- `TaskNotFoundError`
- `TaskNotCancelableError`
- `PushNotificationNotSupportedError`
- `UnsupportedOperationError`
- `ContentTypeNotSupportedError`
- `VersionNotSupportedError`

**Binding-specific:**

- JSON-RPC: custom range `-32001` to `-32099` for A2A-specific
- gRPC: gRPC status codes (`UNAUTHENTICATED`, `PERMISSION_DENIED`, `INVALID_ARGUMENT`, `NOT_FOUND`, `FAILED_PRECONDITION`, etc.)
- REST: HTTP status codes (400/401/403/404/409/500)

All error bodies include: `code`, human-readable `message`, optional structured `details[]` with `@type` discriminator.

### 2.12 Key Design Choices

- **Async-first** — long-running tasks are first class
- **Opaque execution** — agents don't expose internal state; only declared capabilities
- **Context inheritance** — new tasks under the same `contextId` see prior conversation
- **Capability validation** — agents reject unsupported ops with `UnsupportedOperationError`
- **Three delivery mechanisms** for updates: polling, SSE streaming, webhooks

---

## 3. OpenInference Span Conventions

Spec maintained by Arize at `github.com/Arize-ai/openinference`. Sits as a complement to OpenTelemetry — designed to be emitted as OTel spans with OI-specific attributes layered on top.

### 3.1 Span Kinds

Required attribute on every OI span: `openinference.span.kind`. Valid values:

| Span Kind   | Definition                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------------- |
| `LLM`       | Call to a language model for completion / generation                                               |
| `EMBEDDING` | Call to embedding model                                                                            |
| `CHAIN`     | Starting point or link between application steps                                                   |
| `RETRIEVER` | Data retrieval, e.g. vector store query                                                            |
| `RERANKER`  | Document ranking pass                                                                              |
| `TOOL`      | External tool / function call invoked by LLM or agent                                              |
| `AGENT`     | Reasoning block encompassing LLM + tool interactions                                               |
| `GUARDRAIL` | Component that filters/modifies prompts or outputs to protect against jailbreak or harmful content |
| `EVALUATOR` | Quality scoring of model output (relevance, correctness, helpfulness)                              |
| `PROMPT`    | Rendering of a prompt template (newer addition)                                                    |

### 3.2 Universal Attributes

Attributes that apply to every span kind:

- `openinference.span.kind` (string, required)
- `input.value` (string) — serialized input
- `input.mime_type` (string) — `text/plain`, `application/json`, etc.
- `output.value` (string)
- `output.mime_type` (string)
- `session.id` (string) — for grouping multi-turn sessions
- `user.id` (string)
- `metadata` (JSON string)
- `tag.tags` (string[])

### 3.3 LLM Span Attributes

```
llm.model_name              str
llm.system                  str  (e.g. "openai", "anthropic", "vertexai")
llm.provider                str  (hosting, e.g. "azure", "aws", "google")
llm.input_messages          List[object] (flattened indexed)
llm.output_messages         List[object]
llm.prompts                 List[object]
llm.choices                 List[object]
llm.function_call           JSON string
llm.invocation_parameters   JSON string
llm.finish_reason           str
llm.prompt_template.template            str
llm.prompt_template.variables           JSON string
llm.prompt_template.version             str
llm.token_count.prompt                  int
llm.token_count.completion              int
llm.token_count.total                   int
llm.token_count.prompt_details.cache_read    int
llm.token_count.prompt_details.cache_write   int
llm.token_count.prompt_details.audio         int
llm.token_count.completion_details.reasoning int
llm.token_count.completion_details.audio     int
llm.cost.prompt             float (USD)
llm.cost.completion         float
llm.cost.total              float
llm.cost.prompt_details.*   float
llm.cost.completion_details.* float
llm.tools                   List[object]   (tool definitions surfaced to the model)
```

**Indexed message flattening convention:**

```
llm.input_messages.0.message.role     = "user"
llm.input_messages.0.message.content  = "what is the weather?"
llm.input_messages.1.message.role     = "assistant"
llm.input_messages.1.message.tool_calls.0.tool_call.id = "call_abc"
llm.input_messages.1.message.tool_calls.0.tool_call.function.name = "get_weather"
llm.input_messages.1.message.tool_calls.0.tool_call.function.arguments = "{...}"
```

`llm.system` well-known values: `anthropic`, `openai`, `vertexai`, `cohere`, `mistralai`, `xai`, `deepseek`, `amazon`, `meta`, `ai21`.

`llm.provider` well-known values: `anthropic`, `openai`, `cohere`, `mistralai`, `azure`, `google`, `aws`, `xai`, `deepseek`, `groq`, `fireworks`, `moonshot`, `cerebras`, `perplexity`, `together`.

### 3.4 Tool Span Attributes

```
tool.name                       str
tool.description                str
tool.json_schema                JSON string
tool.parameters                 JSON string
tool.id                         str
tool_call.id                    str
tool_call.function.name         str
tool_call.function.arguments    JSON string
tool_call.reasoning_signature   str   (for reasoning-model thoughts)
```

A TOOL span emerges when an agent framework actually executes a tool. The argument value the LLM proposed lives on the parent LLM span's `llm.output_messages[*].tool_calls`; the execution result lives on the TOOL span's `output.value`. The `tool_call.id` correlates the two.

### 3.5 Retriever / Document Attributes

```
retrieval.documents             List[Document]
document.id                     str | int
document.content                str
document.score                  float
document.metadata               JSON string
```

### 3.6 Embedding Attributes

```
embedding.model_name            str
embedding.text                  str
embedding.vector                List[float]
embedding.embeddings            List[object]   (when batched)
embedding.invocation_parameters JSON string
```

### 3.7 Reranker Attributes

```
reranker.model_name             str
reranker.query                  str
reranker.top_k                  int
reranker.input_documents        List[Document]
reranker.output_documents       List[Document]
```

### 3.8 Message Content (Multimodal)

```
message.role                              str
message.content                           str
message.contents                          List[object]   (multimodal parts)
message.name                              str
message.tool_call_id                      str
message.function_call_name                str
message.function_call_arguments_json      JSON string
message.tool_calls                        List[object]

message_content.type           str  ("text"|"image"|"audio"|"reasoning"|"tool_use")
message_content.text           str
message_content.image          object
message_content.id             str
message_content.signature      str
message_content.data           str
message_content.encrypted_content str
```

### 3.9 Misc Attributes

```
exception.message       str
exception.type          str
exception.stacktrace    str
exception.escaped       bool

image.url               str
audio.url               str
audio.mime_type         str
audio.transcript        str

prompt.vendor           str
prompt.id               str
prompt.url              str

agent.name              str

graph.node.id           str
graph.node.name         str
graph.node.parent_id    str   (for graph/workflow visualization)
```

### 3.10 How Spans Emerge

| Operation                        | Resulting span tree                                                                                                       |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Single LLM completion            | one `LLM` span                                                                                                            |
| LLM with tool calls (agent loop) | parent `AGENT` span → child `LLM` (model call) → sibling `TOOL` (each executed tool) → child `LLM` (follow-up call), etc. |
| RAG query                        | `CHAIN` parent → `EMBEDDING` (query) → `RETRIEVER` → optionally `RERANKER` → `LLM`                                        |
| Guarded LLM call                 | `CHAIN` → `GUARDRAIL` (input check) → `LLM` → `GUARDRAIL` (output check)                                                  |
| Multi-agent system               | `CHAIN` (orchestrator) → multiple `AGENT` children, each with their own LLM/TOOL children                                 |

Manual spans at routing decisions, guardrail checks, and handoffs make test datasets and continuous-eval pipelines tractable.

### 3.11 OTel Compatibility

OpenInference is "transport and file-format agnostic" — it does NOT define a wire protocol; it defines attribute keys on top of OpenTelemetry's span model. Any OTel-compatible backend (OTel Collector, Tempo, Jaeger, Phoenix, Arize) can ingest OI spans.

Source: <https://github.com/Arize-ai/openinference>, <https://arize-ai.github.io/openinference/spec/>.

---

## 4. OpenTelemetry GenAI Semantic Conventions

Status as of mid-2026: **Development** (not yet Stable). Source: <https://opentelemetry.io/docs/specs/semconv/gen-ai/>.

Opt-in migration controlled by `OTEL_SEMCONV_STABILITY_OPT_IN` environment variable.

### 4.1 Span Coverage

- **Model spans** — chat completions, embeddings, text completion
- **Agent spans** — `create_agent`, `invoke_agent`, `invoke_workflow`
- **Tool execution spans** — `execute_tool`

### 4.2 Technology-Specific Conventions

Dedicated sub-specs for: Anthropic, Azure AI Inference, AWS Bedrock, OpenAI, Model Context Protocol (MCP). Each adds vendor-specific attributes on top of the generic `gen_ai.*` namespace.

### 4.3 Span Names

| Operation             | Span name                                               |
| --------------------- | ------------------------------------------------------- |
| Create agent          | `create_agent {gen_ai.agent.name}`                      |
| Invoke agent (remote) | `invoke_agent {gen_ai.agent.name}` — span kind CLIENT   |
| Invoke agent (local)  | `invoke_agent {gen_ai.agent.name}` — span kind INTERNAL |
| Invoke workflow       | `invoke_workflow {gen_ai.workflow.name}` — INTERNAL     |
| Chat completion       | `chat {gen_ai.request.model}`                           |
| Embeddings            | `embeddings {gen_ai.request.model}`                     |
| Execute tool          | `execute_tool {gen_ai.tool.name}`                       |

### 4.4 Required Attributes (per span)

- `gen_ai.operation.name` — enum: `chat`, `embeddings`, `generate_content`, `text_completion`, `execute_tool`, `create_agent`, `invoke_agent`, `invoke_workflow`, `retrieval`
- `gen_ai.provider.name` — `openai`, `anthropic`, `aws.bedrock`, `gcp.vertex_ai`, `azure.ai.openai`, etc.

### 4.5 Request Attributes (`gen_ai.request.*`)

```
gen_ai.request.model               str
gen_ai.request.max_tokens          int
gen_ai.request.temperature         double
gen_ai.request.top_p               double
gen_ai.request.top_k               double
gen_ai.request.frequency_penalty   double
gen_ai.request.presence_penalty    double
gen_ai.request.stop_sequences      string[]
gen_ai.request.stream              bool
gen_ai.request.choice_count        int
gen_ai.request.seed                int
gen_ai.request.encoding_formats    string[]   (for embeddings)
```

### 4.6 Response Attributes (`gen_ai.response.*`)

```
gen_ai.response.model               str
gen_ai.response.id                  str
gen_ai.response.finish_reasons      string[]   ("stop"|"length"|"tool_calls"|...)
gen_ai.response.time_to_first_chunk double     (streaming TTFT)
```

### 4.7 Usage Metrics (`gen_ai.usage.*`)

```
gen_ai.usage.input_tokens                    int
gen_ai.usage.output_tokens                   int
gen_ai.usage.cache_creation.input_tokens     int
gen_ai.usage.cache_read.input_tokens         int
gen_ai.usage.reasoning.output_tokens         int
```

### 4.8 Agent Attributes

```
gen_ai.agent.id          str   (unique identifier)
gen_ai.agent.name        str   (human-readable)
gen_ai.agent.description str
gen_ai.agent.version     str
gen_ai.workflow.name     str   (multi-step workflow id)
```

### 4.9 Tool Attributes

```
gen_ai.tool.name            str
gen_ai.tool.type            str  ("function"|"extension"|"datastore")
gen_ai.tool.description     str
gen_ai.tool.definitions     object[]
gen_ai.tool.call.id         str
gen_ai.tool.call.arguments  object | str
gen_ai.tool.call.result     object | str
```

### 4.10 Content (Opt-In)

```
gen_ai.input.messages       object[]   (chat history)
gen_ai.output.messages      object[]   (model responses)
gen_ai.output.type          str        ("text"|"json"|"image"|"speech")
gen_ai.system_instructions  string
```

### 4.11 RAG / Retrieval

```
gen_ai.retrieval.query.text     str
gen_ai.retrieval.documents      object[]
gen_ai.data_source.id           str
```

### 4.12 Evaluation Attributes

```
gen_ai.evaluation.name           str
gen_ai.evaluation.score.value    double
gen_ai.evaluation.score.label    str
gen_ai.evaluation.explanation    str
```

### 4.13 Misc

```
gen_ai.conversation.id         str   (session / thread)
gen_ai.prompt.name             str
gen_ai.embeddings.dimension.count int
server.address                 str
server.port                    int
```

### 4.14 Deprecated → Replacement Mapping

| Deprecated                                            | Replacement                                                              |
| ----------------------------------------------------- | ------------------------------------------------------------------------ |
| `gen_ai.system`                                       | `gen_ai.provider.name`                                                   |
| `gen_ai.usage.prompt_tokens`                          | `gen_ai.usage.input_tokens`                                              |
| `gen_ai.usage.completion_tokens`                      | `gen_ai.usage.output_tokens`                                             |
| `gen_ai.prompt` / `gen_ai.completion` (as attributes) | OTel Event API (`gen_ai.user.message`, `gen_ai.assistant.message`, etc.) |

### 4.15 OpenInference vs OTel GenAI

| Concern           | OpenInference                                                                                                                 | OTel GenAI                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Maintainer        | Arize (vendor-neutral spec, single-vendor steward)                                                                            | CNCF / OpenTelemetry Specification SIG              |
| Status            | Stable & widely-adopted                                                                                                       | Development                                         |
| Span kinds        | Explicit dimension (`openinference.span.kind`) — LLM/TOOL/RETRIEVER/EMBEDDING/RERANKER/CHAIN/AGENT/GUARDRAIL/EVALUATOR/PROMPT | Implied by `gen_ai.operation.name`                  |
| Token namespace   | `llm.token_count.*`                                                                                                           | `gen_ai.usage.*`                                    |
| Content namespace | `llm.input_messages.N.message.*` (indexed flatten)                                                                            | `gen_ai.input.messages` (single attribute) + events |
| Provider          | `llm.system` (model family) + `llm.provider` (host)                                                                           | `gen_ai.provider.name` (host)                       |
| Cost              | First-class (`llm.cost.*`)                                                                                                    | Not standard                                        |
| Adoption          | Native in LangChain, LlamaIndex, OpenAI SDK, Anthropic SDK, Vertex SDK auto-instrumentations                                  | Growing; some vendors emit both                     |

In practice many instrumentations dual-emit, mapping the same data to both namespaces. `[UNVERIFIED]` — the convergence story is documented in <https://niteagent.com/blog/2026-05-25-openinference-vs-otel-agent-tracing/>.

---

## 5. Agent Payments Protocol (AP2)

Source: <https://ap2-protocol.org/>. Reference SDK + spec: <https://github.com/google-agentic-commerce/AP2>.

### 5.1 Status & Version

- **AP2 v0.2** — announced 2025-09-16 by Google with 60+ launch partners (Mastercard, PayPal, Coinbase, American Express, Salesforce, etc.)
- Donated trajectory: positioned as open standard; intended to interoperate with A2A, MCP, UCP
- `[UNVERIFIED]` — exact v0.3+ deltas not consistently surfaced in mid-2026 docs

### 5.2 Settlement Rails

- **Currently in spec:** card networks (Visa/MC/Amex), x402 micropayments
- **On roadmap:** e-wallets, real-time bank push (UPI, PIX, FedNow), stablecoins, digital currencies, ACH

### 5.3 Three-Mandate Model

Every agent purchase represents three signed mandates:

#### Intent Mandate

- Signed by the _user_ inside their AP2-compatible client
- Captures scope and constraints: "buy running shoes, size 10, white or grey, under $150, deliver to saved address"
- Created at initial user request
- Used in **human-not-present (HNP)** mode as the standing authorization

Field set (canonical fields per the spec):

- `intentId`, `userId`, `agentId`
- `description`, `category` / `merchantType`
- `constraints`: `{ maxPrice, currency, deliverBy, allowedMerchants, deniedMerchants, attributes }`
- `expiresAt`
- `signature` (W3C VC proof block)

#### Cart Mandate (a.k.a. Checkout Mandate)

- Produced by the merchant or merchant-side agent
- Binds specific SKU(s), price, tax, shipping, total to the Intent
- Two stages: **Open** (constraints, pre-finalization) and **Closed** (final cart authorized by the user)
- Provides non-repudiable proof of approval

Field set:

- `cartId`, `merchantId`, `intentMandateRef`
- `lineItems[]`: `{ sku, name, qty, unitPrice, taxAmount }`
- `subtotal`, `taxTotal`, `shippingTotal`, `total`, `currency`
- `shippingTo`, `paymentMethodHints`
- `expiresAt`
- `signature`

#### Payment Mandate

- Minimal credential derived from the Cart Mandate
- Appended to the payment authorization; signals to the payment network and issuer that an agent was involved
- Specifies transaction modality: `human_present` vs `human_not_present`
- Does **not** expose sensitive cart or PII to every party in the chain

Field set:

- `paymentMandateId`, `cartMandateRef`
- `amount`, `currency`
- `modality`: `"human_present"` | `"human_not_present"`
- `agentId`, `userId`
- `issuer`, `network`, `merchantId`
- `signature`

### 5.4 VC / Signing Format

- Each Mandate is a **W3C Verifiable Credential** (JSON-LD)
- Signed by the user's wallet OR the agent's key
- Crypto: **ECDSA over P-256 (or stronger), SHA-256** integrity hashing
- Each mandate is tamper-evident; signatures are chainable for audit

### 5.5 Agent Identity

- Agents have cryptographic identity (key pairs); their public key is the basis for verification
- Identity may be backed by DIDs (Decentralized Identifiers) — `[UNVERIFIED]` for v0.2; the spec leaves this somewhat open

### 5.6 Dispute / Audit Model

AP2 provides "a non-repudiable cryptographic audit trail for every transaction." When a dispute arises:

1. The chain of signed mandates (Intent → Cart → Payment) is presented to the issuer/network
2. Each signature is verifiable independently
3. The modality (`human_present` vs `human_not_present`) drives the liability allocation per the merchant agreement
4. Networks adapt existing chargeback flows around this evidence chain

### 5.7 Cards vs x402 vs Other Rails

| Rail                       | Notes                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Cards                      | Existing rails reuse the Payment Mandate as a signal in the authorization stream; issuers gain `agent_involved` flag  |
| x402                       | HTTP 402 micropayment standard — agent retries request after attaching payment; AP2 mandates supply the consent layer |
| Bank push (UPI/PIX/FedNow) | Roadmap; would replace the card auth path                                                                             |
| Stablecoins                | Roadmap; mandate chain replaces conventional consent recording                                                        |

---

## 6. Universal Commerce Protocol (UCP)

Source: <https://ucp.dev/> (root), <https://github.com/Universal-Commerce-Protocol/ucp>, <https://github.com/Universal-Commerce-Protocol/ucp-schema>. Google-led, endorsed by Shopify, Etsy, Wayfair, Target, Walmart, 20+ partners.

### 6.1 Version

Specs are dated (e.g., `2026-04-08`). Schemas live at well-known URLs:

- `https://ucp.dev/schemas/shopping/checkout.json`
- `https://ucp.dev/schemas/shopping/order.json`

### 6.2 Transports

REST and JSON-RPC. Integrates with MCP (tool surface), A2A (agent-to-merchant agent), and AP2 (payments).

### 6.3 Capability Areas

| Capability                | Purpose                                                         |
| ------------------------- | --------------------------------------------------------------- |
| Catalog Search and Lookup | Product discovery + detail retrieval                            |
| Cart Building             | Adding/modifying items, applying discounts                      |
| Identity Linking          | OAuth 2.0 binding between agent and merchant account            |
| Checkout                  | Cart finalization, tax, shipping resolution                     |
| Order Management          | From purchase confirmation through delivery; real-time webhooks |

### 6.4 Merchant Profile

The merchant profile document (typically at `/.well-known/ucp-profile.json` or similar) declares:

- `version` (date-formatted, e.g. `"2026-04-08"`)
- `services[]` — endpoints for each capability
- `capabilities[]` — which UCP primitives the merchant supports
- `schemaEndpoints` — URLs of the JSON schemas being used
- `specifications` — supported UCP profile (shopping vs lodging vs food)

### 6.5 Verticals

- **Shopping** — primary (current)
- **Lodging** — detailed spec in progress (hotel rooms, vacation rentals)
- **Food** — detailed spec in progress (restaurant ordering, grocery)
- **Travel** (broader) — flights, ground — likely future

### 6.6 Order Lifecycle

`[UNVERIFIED]` field name conventions (typical of UCP shopping):

- `pending` → `paid` → `processing` → `shipped` → `delivered`
- Side branches: `canceled`, `refunded`, `partial_refund`, `returned`, `disputed`

The core schema is intentionally minimal — fulfillment groups and shipping options are added by a **fulfillment extension**.

### 6.7 Extension Model

Core checkout schema defines universal primitives only. Verticals/features layer in via extensions:

- `fulfillment` extension — shipping options, delivery windows
- `subscriptions` extension — recurring orders
- `gift` extension — gift-wrap, recipient
- Custom extensions are namespaced

---

## 7. Agent-to-UI Protocol (A2UI)

Source: <https://a2ui.org>.

### 7.1 Premise

"Declarative data format, not executable code. Agents can only use pre-approved components from your catalog." Agents render UI to users by emitting structured component descriptions; the client app renders them with native widgets.

### 7.2 Versions

- **v0.8 — Stable** (production-recommended)
  - Surfaces, components, data binding, adjacency-list model
- **v0.9 — Draft**
  - Adds `createSurface` operation
  - Adds client-side functions (allow client to compute derived values)
  - Adds custom catalogs
  - Adds extension specification

### 7.3 Surface Lifecycle (6-step loop)

1. User sends a message to an agent
2. Agent generates A2UI messages (structure + data)
3. Messages stream to client application
4. Client renders using native components
5. User interacts; client sends actions back
6. Agent responds with updated A2UI messages

### 7.4 Adjacency-List Model

Components form a graph, not a tree, expressed as an adjacency list:

- Each component has an ID
- Each component lists its children's IDs
- Layout, conditionals, and dynamic mounting happen by mutating adjacency

### 7.5 Component Catalog (representative)

The standard catalog includes (with v0.8):

- `Card` — surface block with title, body, optional media
- `Form` — input fields with validation
- `Field` types — text, number, date, select, multiselect, checkbox, radio
- `List` — vertical/horizontal list of items
- `Chart` — basic chart types
- `Button` — action trigger
- `Text`, `Heading`, `Image`, `Video`
- `Container` — layout grouping
- `Tabs`, `Accordion`
- `Map` — geo display

Each component instance: `{ id, type, props, children: [ids] }`.

### 7.6 Message Format

A2UI messages stream over A2A (transport). Each message contains:

- `surfaceId` — target surface (created via `createSurface` in v0.9, or implicit in v0.8)
- `components` — adjacency list of components keyed by ID
- `data` — backing data bound into components
- `actions` — callback handlers / form submissions the client can invoke back to the agent

### 7.7 Transport

A2UI uses A2A as its communication transport. The agent → client UI stream is conveyed as an A2A `artifactUpdate` or `message` event with A2UI-specific MIME type.

---

## 8. OWASP Top 10 for LLM Applications (2025)

Source: <https://genai.owasp.org/llmrisk2025/>.

### 8.1 LLM01:2025 — Prompt Injection

User prompts (direct) or external content (indirect) alter the LLM's behavior in unintended ways. Inputs need not be human-readable.

- **Direct** — user input modifies model behavior
- **Indirect** — external sources (websites, files, RAG docs) contain hidden instructions

Common impacts: sensitive info disclosure, system prompt leakage, content manipulation, unauthorized function access, command execution in connected systems.

Mitigations: constrain via role instructions, define output formats with validation, input/output filtering, privilege controls, human approval for high-risk operations, segregate untrusted content, adversarial testing.

Example scenarios (verbatim from spec): support chatbot exfiltrating private data, webpage summary embedded instructions, resume optimization with AI-detector instructions, RAG doc tampering, email assistant exploitation (CVE-2024-5184), payload splitting, multimodal image-text attacks, adversarial suffixes, multilingual/Base64 obfuscation.

### 8.2 LLM02:2025 — Sensitive Information Disclosure

Exposure of PII, financial data, health records, credentials, proprietary algorithms, or business secrets via model outputs. Cases include training data leakage and inference-time RAG leakage. Mitigations: data minimization, differential privacy, output redaction.

### 8.3 LLM03:2025 — Supply Chain

Vulnerabilities introduced through third-party models (Hugging Face artifacts), datasets, pre-trained components, plugins, or dependencies. Mitigations: SBOM for AI, model provenance, signed weights, dataset cards.

### 8.4 LLM04:2025 — Data and Model Poisoning

Malicious manipulation of pre-training, fine-tuning, or embedding data. Includes backdoors that activate on trigger phrases. Mitigations: data lineage, anomaly detection, dataset signing.

### 8.5 LLM05:2025 — Improper Output Handling

Insufficient validation/sanitization of LLM outputs sent downstream to interpreters (XSS, SQLi, command injection, SSRF). Mitigations: treat LLM output as untrusted user input, parameterized queries, sandboxed renderers.

### 8.6 LLM06:2025 — Excessive Agency

Over-granted permissions or functions to LLM-driven systems. Three sub-causes:

- **Excessive functionality** — tool surface area too large
- **Excessive permissions** — tool runs with privileges beyond what user has
- **Excessive autonomy** — actions execute without sufficient confirmation

Mitigations: principle of least privilege per tool, scoped credentials, human-in-loop on high-impact actions, dry-run / preview modes.

### 8.7 LLM07:2025 — System Prompt Leakage

Disclosure of system prompts that reveal credentials, internal logic, or guardrails attackers can use to evade.

Mitigations: don't store secrets in prompts (use secret managers), don't rely on system prompts for security boundaries, monitor for prompt extraction attempts.

### 8.8 LLM08:2025 — Vector and Embedding Weaknesses

Risks in RAG / vector stores: cross-context leakage, embedding inversion attacks (recovering source text from embeddings), poisoned vector entries.

Mitigations: namespace per tenant, embedding access controls, monitor for anomalous similarity queries.

### 8.9 LLM09:2025 — Misinformation

LLM produces confident-but-wrong outputs (hallucinations). Mitigations: ground in retrieval, cite sources, calibrate uncertainty, user disclosure of model limits.

### 8.10 LLM10:2025 — Unbounded Consumption

Resource exhaustion: token-burn DoS, denial-of-wallet via paid model APIs, runaway agent loops. Mitigations: rate limits, token budgets, circuit breakers, cost monitors.

---

## 9. OWASP Top 10 for Agentic Applications (2026 / ASI)

Released by OWASP GenAI Security Project on 2025-12-09. Often labeled "ASI" (Agentic Security Initiative). Source: <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>.

This is distinct from — and additive to — the LLM Top 10. Where the LLM Top 10 focuses on _single-model_ risk, the agentic version covers multi-agent, tool-using, memory-bearing systems.

### 9.1 ASI01:2026 — Agent Goal Hijack

Attackers manipulate agent goals, plans, or decision paths through direct or indirect instruction injection, causing agents to pursue unintended objectives.

Sub-patterns:

- Direct goal manipulation via prompt injection
- Indirect injection through documents / RAG content
- Recursive hijacking propagating through reasoning chains
- Cross-context injection embedding hidden instructions into shared state

### 9.2 ASI02:2026 — Tool Misuse & Exploitation

Agents misuse or abuse tools through unsafe composition, recursion, or excessive execution, despite having valid permissions.

Sub-patterns:

- Recursive tool calls causing resource exhaustion
- Unsafe tool composition in dangerous sequences
- Tool budget exhaustion via excessive invocations
- Cross-tool state leakage between contexts

### 9.3 ASI03:2026 — Agent Identity & Privilege Abuse

Delegated authority, ambiguous agent identity, or trust assumptions lead to unauthorized actions.

Sub-patterns:

- Agent impersonation with higher privileges
- Cross-agent trust abuse exploiting implicit relationships
- Identity inheritance through unauthorized agent chains
- RBAC bypasses

### 9.4 ASI04:2026 — Agentic Supply Chain Compromise

Compromise of external agents, tools, schemas, or prompts that agents dynamically trust or import.

Sub-patterns:

- Schema manipulation corrupting tool/API schemas
- Description deception misleading agents (lying tool descriptions)
- Permission misrepresentation via false declarations
- Registry poisoning (compromised MCP / A2A registries)

### 9.5 ASI05:2026 — Unexpected Code Execution

Agent-generated or agent-triggered code executes without sufficient validation or isolation.

Sub-patterns:

- Unauthorized code generation and execution
- Direct shell command invocation
- Unsafe `eval` of dynamic expressions
- Command injection via malicious outputs reaching shell

### 9.6 ASI06:2026 — Memory & Context Poisoning

Injection or leakage of agent memory or contextual state that influences future reasoning or actions.

Sub-patterns:

- Long-term memory poisoning corrupting persistent stores
- Context injection inserting malicious information mid-stream
- State manipulation altering reasoning across sessions
- Memory leakage exposing sensitive content to a later turn or another user

### 9.7 ASI07:2026 — Insecure Inter-Agent Communication

Manipulation of messages exchanged between agents, planners, and executors.

Sub-patterns:

- Agent-in-the-middle (AITM) interception and modification
- Message injection
- Message spoofing forging trusted agent communications
- Out-of-band channel collusion

### 9.8 ASI08:2026 — Cascading Agent Failures

Small agent failures propagate through connected systems, causing large-scale impact.

Sub-patterns:

- Tool chain errors propagating through sequences
- Agent dependency failures affecting dependent systems
- Resource exhaustion cascading across infrastructure
- Trust chain breakdowns

### 9.9 ASI09:2026 — Human-Agent Trust Exploitation

Exploiting human over-reliance on agents through misleading explanations or authority framing.

Sub-patterns:

- Authority misrepresentation with false credentials
- Misleading explanations deceiving users about agent reasoning
- Over-confidence projection with unwarranted certainty
- Responsibility diffusion deflecting accountability

### 9.10 ASI10:2026 — Rogue Agents

Agents acting beyond intended objectives due to goal drift, collusion, or emergent behavior.

Sub-patterns:

- Goal drift gradually deviating from objectives
- Agent collusion coordinating unintended purposes
- Reward hacking optimizing for proxies
- Runaway autonomy exceeding designed boundaries

### 9.11 LLM-Top-10 → ASI-Top-10 Mapping (Cross-Reference)

| LLM01 Prompt Injection | → | ASI01 Goal Hijack, ASI06 Memory Poisoning |
| LLM02 Sensitive Info Disclosure | → | ASI06 Memory Poisoning (leakage variant) |
| LLM03 Supply Chain | → | ASI04 Agentic Supply Chain |
| LLM04 Data Poisoning | → | ASI06 Memory & Context Poisoning |
| LLM05 Improper Output Handling | → | ASI05 Unexpected Code Execution |
| LLM06 Excessive Agency | → | ASI02 Tool Misuse, ASI03 Identity Abuse |
| LLM07 System Prompt Leakage | → | (covered partially by ASI01 / ASI06) |
| LLM08 Vector & Embedding | → | ASI06 Memory Poisoning (RAG variant) |
| LLM09 Misinformation | → | ASI09 Human-Agent Trust |
| LLM10 Unbounded Consumption | → | ASI02 Tool Misuse, ASI08 Cascading Failures |

### 9.12 Mapping to Injectable Fault Classes

For chaos / fault injection purposes, the agentic risks decompose into injectable failures at four interfaces:

1. **Tool interface (MCP `tools/call` boundary)** — ASI02, ASI05, ASI08
   - Tool returns wrong content / type / structured field
   - Tool timeout
   - Tool returns `isError: true` with adversarial text
   - Tool returns truncated or oversized payload
   - Tool reorders sub-keys to violate output schema
   - Tool returns a `resource_link` to a malicious URI
   - Annotations lie (`readOnlyHint: true` on destructive tool)

2. **Inter-agent interface (A2A `message/send` / `message/stream` boundary)** — ASI03, ASI07, ASI10
   - Spoofed `role` field
   - Task transitions to `TASK_STATE_FAILED` mid-stream
   - SSE stream stalls / disconnects / out-of-order events
   - Push webhook delivers stale `statusUpdate`
   - Forged signed Agent Card claiming wider skills

3. **Memory / RAG interface (vector store)** — ASI06
   - Inject poisoned chunk into retrieval results
   - Slightly mutate a stored memory record
   - Return memory entries belonging to another user (cross-tenant)
   - Empty retrieval for a query that should hit

4. **Model interface (LLM provider)** — ASI01, ASI05, ASI09
   - Inject indirect prompt in retrieved context
   - Force-finish (truncate at max tokens)
   - Return a structured-output JSON that fails downstream schema
   - Latency spike → cascading timeouts
   - Hallucinated tool call (`tool_call.function.name` for a nonexistent tool)

---

## 10. MITRE ATLAS — Adversarial Threat Landscape for AI Systems

Source: <https://atlas.mitre.org/>. As of Feb 2026 (v5.4.0): **16 tactics, 84 techniques, 56 sub-techniques**.

### 10.1 Tactics

ATLAS inherits 13 from ATT&CK and adds three AI-specific tactics. The current 16:

| ID         | Tactic               | Notes                                                                            |
| ---------- | -------------------- | -------------------------------------------------------------------------------- |
| AML.TA0001 | Reconnaissance       | Discover ML artifacts, model ontology, active scanning                           |
| AML.TA0002 | Resource Development | Acquire public ML artifacts, develop adversarial ML capabilities                 |
| AML.TA0003 | Initial Access       | ML supply chain compromise, **prompt injection**                                 |
| AML.TA0004 | ML Model Access      | Inference API access, ML artifacts access                                        |
| AML.TA0005 | Execution            | User Execution, **LLM Plugin Compromise**                                        |
| AML.TA0006 | Persistence          | Modify AI agent configuration                                                    |
| AML.TA0007 | Privilege Escalation | Exploit through ML system                                                        |
| AML.TA0008 | Defense Evasion      | Adversarial perturbation, **LLM meta-prompt extraction**                         |
| AML.TA0009 | Credential Access    | Credentials from AI agent configuration                                          |
| AML.TA0010 | Discovery            | Discover AI agent configuration                                                  |
| AML.TA0011 | Collection           | Data from AI services, RAG database retrieval                                    |
| AML.TA0012 | ML Attack Staging    | Poison training data, backdoor ML model                                          |
| AML.TA0013 | Exfiltration         | Exfiltration via ML inference API, **Exfiltration via AI Agent Tool Invocation** |
| AML.TA0014 | Impact               | Denial of ML service, evade ML model, spamming ML system                         |
| AML.TA0015 | Command and Control  | Reverse shell, AI Service API                                                    |

Source: <https://www.vectra.ai/topics/mitre-atlas>.

### 10.2 Key Techniques (for agent / LLM attacks)

| Technique ID  | Name                                                   |
| ------------- | ------------------------------------------------------ |
| AML.T0020     | Poison Training Data                                   |
| AML.T0024     | Exfiltration via AI Inference API                      |
| AML.T0050     | Command and Scripting Interpreter (in AI context)      |
| **AML.T0051** | **LLM Prompt Injection**                               |
| AML.T0051.000 | LLM Prompt Injection: Direct                           |
| AML.T0051.001 | LLM Prompt Injection: Indirect (via Retrieved Content) |
| **AML.T0054** | **LLM Jailbreak Injection: Direct**                    |
| AML.T0055     | Unsecured Credentials                                  |
| AML.T0057     | LLM Data Leakage                                       |
| AML.T0061     | LLM Prompt Obfuscation `[UNVERIFIED]`                  |
| AML.T0067     | LLM Plugin Compromise                                  |
| AML.T0068     | LLM Trusted Output Components Manipulation             |
| AML.T0070     | RAG Poisoning                                          |
| AML.T0086     | **Exfiltration via AI Agent Tool Invocation**          |
| AML.T0096     | AI Service API (used as C2 channel)                    |

Source: <https://www.startupdefense.io/mitre-atlas-techniques/aml-t0051-llm-prompt-injection>.

### 10.3 LLM Top 10 ↔ ATLAS Mapping (Selected)

| OWASP LLM                       | ATLAS Technique                                   |
| ------------------------------- | ------------------------------------------------- |
| LLM01 Prompt Injection          | AML.T0051 (.000 direct, .001 indirect), AML.T0054 |
| LLM02 Sensitive Info Disclosure | AML.T0024 (via API), AML.T0057, AML.T0086         |
| LLM03 Supply Chain              | AML.T0010 ML Supply Chain Compromise              |
| LLM04 Data Poisoning            | AML.T0020, AML.T0070                              |
| LLM05 Improper Output Handling  | AML.T0050, AML.T0068                              |
| LLM06 Excessive Agency          | AML.T0067 (plugin compromise), AML.T0086          |
| LLM07 System Prompt Leakage     | AML.T0008 (LLM Meta Prompt Extraction)            |
| LLM10 Unbounded Consumption     | AML.TA0014 (Denial of ML Service)                 |

`[UNVERIFIED]` source for full mapping table: <https://medium.com/@ferkhaled2004/mapping-owasp-top-10-for-llm-ai-applications-to-mitre-atlas-a-comprehensive-guide-e97013500bc4>.

---

## 11. NIST AI Risk Management Framework (AI RMF) & GenAI Profile

Source: <https://www.nist.gov/itl/ai-risk-management-framework>.

### 11.1 AI RMF 1.0 (released 2023-01-26)

Four core functions, each subdivided into categories and sub-categories:

| Function    | Purpose                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------ |
| **GOVERN**  | Cultivate a culture of risk management — policies, accountability, transparency, oversight       |
| **MAP**     | Establish context — system purpose, stakeholders, expected use & misuse                          |
| **MEASURE** | Analyze and quantify risk — testing, evaluation, validation, verification (TEVV)                 |
| **MANAGE**  | Allocate resources to address risks and respond when realized — incident response, communication |

### 11.2 NIST AI 600-1 — Generative AI Profile (2024-07-26)

Identifies **12 risk categories** unique to or amplified by GenAI. Released under Executive Order 14110.

1. **CBRN Information or Capabilities** — uplift for chemical/biological/radiological/nuclear threats; specialized biological design tools (BDTs)
2. **Confabulation** — confident-but-false outputs (hallucination)
3. **Dangerous, Violent, or Hateful Content** — speech harms, incitement
4. **Data Privacy** — PII leakage, training data exfiltration, re-identification
5. **Environmental Impacts** — energy/water consumption of training and inference
6. **Harmful Bias or Homogenization** — disparate impact, mode collapse
7. **Human-AI Configuration** — automation bias, mis-calibrated trust
8. **Information Integrity** — deepfakes, synthetic media at scale
9. **Information Security** — model inversion, extraction, prompt injection, jailbreak
10. **Intellectual Property** — training data IP, output IP
11. **Obscene, Degrading, or Abusive Content** — CSAM, NCII
12. **Value Chain and Component Integration** — supply chain across foundation model → fine-tune → app

Source: <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf>.

### 11.3 Agentic Profile (Draft)

CSA has begun an agentic-specific RMF profile draft (`[UNVERIFIED]` for status as of mid-2026). Source: <https://labs.cloudsecurityalliance.org/agentic/agentic-nist-ai-rmf-profile-v1/>.

### 11.4 Relevance for Agent Reliability Testing

Categories that most directly motivate reliability/fault testing:

- **Information Security** (#9) — adversarial robustness, prompt injection, model extraction → red-team protocols
- **Confabulation** (#2) — hallucination detection in grounded outputs → eval harnesses
- **Human-AI Configuration** (#7) — calibration tests for "agent confidence vs actual correctness"
- **CBRN** (#1) — content-restriction tests at the output gate

---

## 12. ARC-AGI & Agent Benchmarks

### 12.1 ARC-AGI

Source: <https://arcprize.org>.

- **ARC-AGI-1** (2019) — original, largely "solved" relative to original target
- **ARC-AGI-2** (2025) — current challenge; SOTA: **Gemini 3 Deep Think at 84.6%** on ARC-AGI-2 (at $13.62/task); best Kaggle-constrained system (NVARC) at 24%; grand prize target = 85% on private eval under Kaggle compute limits. Source: <https://arxiv.org/pdf/2505.11831>.
- **ARC-AGI-3** — announced, future challenge.

Sets: public (dev), semi-private (visible score but ineligible for prize), private (final evaluation).

### 12.2 SWE-Bench (and SWE-Bench Verified)

Source: <https://www.swebench.com>.

Tests an agent's ability to resolve real GitHub issues in real repos. **SWE-Bench Verified** is the 500-task curated subset.

- As of mid-2026: **Claude Sonnet 5 reports 92.4% on SWE-Bench Verified** (single highest); GPT-5.5 around 82.6%; Claude Sonnet 4.6 at 79.6%.
- SWE-Bench Pro (2026) is a much harder follow-on; top scores reach ~46%.
- **Known issue:** OpenAI's audit found some Verified tasks appeared in model training data — partial memorization risk. Source: <https://localaimaster.com/models/swe-bench-explained-ai-benchmarks>.

### 12.3 Tau-Bench / Tau²-Bench

Source: Sierra Research. <https://github.com/sierra-research/tau2-bench>, paper arXiv:2406.12045.

Measures tool-agent-user interaction with API tools and domain policies across retail, airline (and τ²: telecom).

- Overall: Step-3.5-Flash by StepFun leads at 0.882 (May 2026 leaderboard)
- Airline domain: Claude Sonnet 4.5 leads at 0.700
- BenchLM tracks Claude Mythos Preview at 89.2% on the snapshot

### 12.4 WebArena / Online-Mind2Web / BrowseComp

- **WebArena** — 812 self-hosted web tasks across e-commerce, social, dev, content-mgmt sites. Record single-agent task completion: 61.7% (mid-2026).
- **Online-Mind2Web** — 300 tasks across 136 real public websites; current SOTA roughly tracked at <https://awesomeagents.ai/leaderboards/web-agent-benchmarks-leaderboard/>.
- **Mind2Web 2** (NeurIPS 2025) — 130 long-horizon tasks with real-time browsing; >1,000 hours of human annotation.
- **BrowseComp / BrowseComp-V3** — hard QA requiring multi-constraint browsing.
- **MM-BrowseComp** — multimodal; even o3 + tools achieves only 29.02%.
- **WebChoreArena**, **WebVoyager** — additional benchmarks.

### 12.5 AgentBench (Tsinghua)

Source: arXiv:2308.03688. 8-environment multi-task benchmark — OS bash, DB, knowledge graph, card game, lateral thinking, house-holding, web shopping, web browsing.

### 12.6 AppWorld

Long-horizon agent benchmark — full computer environment, code + API calls across diverse apps. Source: Trivedi et al. (2024).

### 12.7 MLAgentBench / RE-Bench / MLGym

- **RE-Bench** (METR, 2024-11) — research engineering benchmark; agents tackle day-long ML R&D tasks vs human baselines. arXiv:2411.15114.
- **MLAgentBench** — proposes ML research tasks as benchmark (`[UNVERIFIED]`).
- **MLGym** (Meta, 2025) — framework + benchmark for AI research agents.

### 12.8 What Each Measures

| Benchmark           | Measures                                                      |
| ------------------- | ------------------------------------------------------------- |
| ARC-AGI             | Skill-acquisition efficiency on novel grid-puzzle tasks       |
| SWE-Bench Verified  | Coding agent — repair GitHub issues end-to-end                |
| Tau-Bench           | Tool-using conversational agents in policy-bound domains      |
| WebArena / Mind2Web | Browser agents — complete real web tasks                      |
| AgentBench          | Cross-environment generalist agent                            |
| AppWorld            | Multi-app long-horizon tasks                                  |
| RE-Bench            | AI-R&D acceleration potential (dangerous-capability adjacent) |

---

## 13. Academic & Public Eval Frameworks

### 13.1 HELM (Holistic Evaluation of Language Models)

Source: Stanford CRFM — <https://github.com/stanford-crfm/helm>, <https://crfm.stanford.edu/helm/>.

- Open-source Python framework for reproducible, multi-scenario eval
- "HELM Capabilities" leaderboard curates capability-targeted scenarios
- Status: enters maintenance mode 2026-06-01
- Recent evaluations include Claude 3.5/3.7 Haiku & Sonnet, Gemini 1.5 Pro, Gemini 2.0 Flash variants

### 13.2 BIG-Bench

Source: <https://github.com/google/BIG-bench>.

204 tasks contributed by 450+ authors targeting capabilities beyond current model abilities at the time of construction (2022). BIG-Bench Hard (BBH) is the 23-task harder subset.

### 13.3 LMSYS Chatbot Arena

Source: <https://chat.lmsys.org/>.

Crowd-sourced human-preference Elo via blind pairwise comparisons. Uses the Bradley-Terry model. As of mid-2026 (`[UNVERIFIED]` snapshot from secondary sources):

- Top overall: Claude Opus 4.6 Thinking at ~1504 Elo
- Gemini 3.1 Pro Preview at ~1493
- Grok 4.20 Beta1 at ~1491
- GPT-5.4 High at ~1484
- Coding sub-leaderboard: Claude Opus 4.6 leads at ~1549

Source: <https://www.swfte.com/lmsys-leaderboard>.

### 13.4 METR (formerly ARC Evals)

Source: <https://metr.org/>.

Non-profit, Berkeley. Specializes in **dangerous capability evaluations** of frontier systems for sabotage, replication, and AI-R&D uplift. Notable artifacts:

- **RE-Bench** — research engineering benchmark
- **MALT** — Manually-reviewed Agentic Labeled Transcripts dataset for sandbagging / reward-hacking behavior
- Methodology emphasizes structured task time, human baseline comparisons, and pre-registered protocols

---

## 14. Red-Team-Specific Protocols, Datasets & Attack Families

### 14.1 Datasets

- **AdvBench** (Zou et al., 2023) — "Harmful Strings" + "Harmful Behaviors" — the canonical eval set for jailbreak research
- **HarmBench** — broader behavior coverage, automated grader
- **DAN ("Do Anything Now")** — community-maintained set of role-play jailbreak prompts
- **JailbreakBench** (Dec 2024) — 1,442 prompts, robustness benchmark
- **HackAPrompt** — competition-derived dataset; world's largest curated prompt-injection dataset (`[UNVERIFIED]` exact composition)
- **CySecBench** — 12,662 prompts across 10 cybersecurity attack categories
- **RedBench** — universal red-team dataset (arXiv:2601.03699)
- **SafetyPrompts.com** — community catalog of red-team prompt sets

### 14.2 Attack Technique Families

#### GCG — Greedy Coordinate Gradient

- Zou et al. 2023
- White-box, optimization-based; produces non-human-readable adversarial suffixes
- High success rate; transferable across models
- Visible to perplexity filters

#### AutoDAN

- Liu et al. 2023, arXiv:2310.15140
- Gradient-based, but produces **human-readable** attacks
- Bypasses perplexity defenses
- Variant: **AutoDAN-Turbo** (Oct 2024, arXiv:2410.05295) — lifelong agent that self-explores jailbreak strategies

#### PAIR — Prompt Automatic Iterative Refinement

- Chao et al. 2023, arXiv:2310.08419
- Black-box; an attacker LLM iteratively rewrites prompts to defeat a target LLM
- Often succeeds in ≤20 queries
- Produces semantically-meaningful jailbreaks

#### TAP — Tree of Attacks with Pruning

- Mehrotra et al. 2023
- Builds a tree of attack candidates; prunes branches that are off-topic; queries-efficient
- Generalizes PAIR

#### Crescendo

- Russinovich et al. 2024, arXiv:2404.01833
- Multi-turn jailbreak — begins benign, escalates by referencing the model's own prior replies
- Highly successful against frontier models with single-turn safety training

#### Logic-Chain Injection / Carrier Articles

- arXiv:2404.04849, arXiv:2408.11182
- Hide a malicious goal inside benign narrative scaffolding (story, news article)

#### Cipher / Encoded Attacks

- Base64, ROT-N, hex, multilingual code-switching, Unicode confusables
- Bypass keyword-based and embedding-similarity safety classifiers

### 14.3 Agentic Red-Team Approaches

- **CoP (Composition of Principles)** — agentic red-teaming via compositional principles (arXiv:2506.00781)
- **Jailbreak-R1** — RL training of jailbreak attacker (arXiv:2506.00782)
- **AgentDojo** (`[UNVERIFIED]`) — security-focused agent benchmark with adversarial environments

### 14.4 Indirect Prompt Injection Specifically

- Greshake et al. 2023 — "Not what you've signed up for" — first major taxonomy
- Maps to ATLAS AML.T0051.001
- Maps to OWASP LLM01 (indirect variant)
- Maps to ASI01 (Goal Hijack — indirect injection)

---

## 15. Interop: OpenInference + A2A + MCP Unified Trace Story

A multi-protocol agent emits a single OpenInference / OTel trace spanning every protocol surface. The clean shape:

### 15.1 Span Hierarchy for a Multi-Protocol Agent

```
[CHAIN]  root: "user request handling"
  ├─ [AGENT]  "orchestrator agent"
  │    ├─ [LLM]  "orchestrator decides next step"
  │    │     llm.output_messages.0.message.tool_calls.0.tool_call.function.name = "search_docs"
  │    │
  │    ├─ [TOOL]  "search_docs"               # MCP tools/call
  │    │     openinference.span.kind = "TOOL"
  │    │     tool.name = "search_docs"
  │    │     tool_call.id = "call_abc"
  │    │     input.value = "{...arguments...}"
  │    │     output.value = "{...CallToolResult content...}"
  │    │
  │    ├─ [AGENT]  "delegate to research-agent"   # A2A peer call
  │    │     openinference.span.kind = "AGENT"
  │    │     agent.name = "research-agent"
  │    │     # under it: child spans emitted BY the remote agent if it cooperates
  │    │     ├─ [LLM]  ...
  │    │     ├─ [RETRIEVER]  ...
  │    │     └─ [LLM]  ...
  │    │
  │    └─ [LLM]  "orchestrator final answer"
```

### 15.2 How MCP Maps to OI

- Every `tools/call` → one `openinference.span.kind = "TOOL"` span
- `tool.name` ← MCP `params.name`
- `input.value` ← serialized MCP `params.arguments`
- `output.value` ← serialized `CallToolResult.content`
- `tool_call.id` ← MCP request ID (or LLM-assigned tool_call id where applicable)
- Tool execution error (`isError: true`) → set OI `exception.*` attributes + status=Error
- `resource_link` content → emit a child `RETRIEVER` span if followed up

### 15.3 How A2A Maps to OI

- Each `message/send` or `message/stream` call to a peer agent → one `openinference.span.kind = "AGENT"` span on the caller side
- `agent.name` ← peer's Agent Card `name`
- `input.value` ← outgoing Message parts (text/data/file URIs)
- `output.value` ← final agent reply Message
- If the peer cooperates with trace propagation (W3C `traceparent` carried in A2A `metadata` or HTTP headers), the peer emits child spans under the same trace ID
- Each `statusUpdate` SSE event → optionally an OI span event (`event.name = "task.status_changed"`) on the AGENT span
- Task lifecycle states (`TASK_STATE_*`) → set as attributes or events; failed/canceled → status=Error

### 15.4 How AP2 Maps to OI

`[UNVERIFIED]` — no canonical mapping yet. Reasonable convention:

- `openinference.span.kind = "TOOL"` for the payment leg
- `tool.name = "ap2.payment"`
- Custom attributes: `ap2.intent_mandate.id`, `ap2.cart_mandate.id`, `ap2.payment_mandate.id`, `ap2.modality`, `ap2.amount`, `ap2.currency`, `ap2.settlement_rail`
- Each signed mandate is an `event` on the span with a hash of the VC

### 15.5 How A2UI Maps to OI

`[UNVERIFIED]`. Reasonable convention:

- The A2UI message-emission step → `openinference.span.kind = "CHAIN"` or a custom `UI` kind
- `output.mime_type = "application/a2ui+json"`
- `output.value` = serialized A2UI message

### 15.6 OTel Compatibility (Both Conventions Side-by-Side)

A dual-emitting instrumentation sets both:

- `openinference.span.kind = "TOOL"` (OI side)
- `gen_ai.operation.name = "execute_tool"` (OTel side)
- `tool.name` (OI) AND `gen_ai.tool.name` (OTel) — same value
- `llm.token_count.prompt` (OI) AND `gen_ai.usage.input_tokens` (OTel) — same value

Backends that consume only one namespace see consistent data either way.

### 15.7 What a Single Trace ID Buys

For chaos / fault injection:

- A single fault injected at the MCP tool layer → visible as one specific `TOOL` span's `isError: true`
- Whether that fault cascades through subsequent `AGENT` / `LLM` / `TOOL` spans is visible as continued spans (or status flips) on the same trace
- Mean-time-to-detection = wall-clock between fault-injection event and first downstream `status=Error` span
- Blast radius = count of spans with `status=Error` downstream of the fault
- Recovery time = wall-clock until subsequent spans return to `status=Ok`

---

## 16. Sources

### MCP

- <https://modelcontextprotocol.io/specification/>
- <https://modelcontextprotocol.io/specification/2025-11-25/basic>
- <https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle>
- <https://modelcontextprotocol.io/specification/2025-11-25/basic/transports>
- <https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization>
- <https://modelcontextprotocol.io/specification/2025-11-25/server>
- <https://modelcontextprotocol.io/specification/2025-11-25/server/tools>
- <https://modelcontextprotocol.io/specification/2025-11-25/client>
- <https://github.com/modelcontextprotocol/specification>

### A2A

- <https://a2a-protocol.org>
- <https://a2a-protocol.org/latest/>
- <https://a2a-protocol.org/latest/specification/>
- <https://github.com/a2aproject/A2A>

### OpenInference

- <https://github.com/Arize-ai/openinference>
- <https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md>
- <https://github.com/Arize-ai/openinference/blob/main/spec/traces.md>
- <https://arize-ai.github.io/openinference/spec/>

### OpenTelemetry GenAI

- <https://opentelemetry.io/docs/specs/semconv/gen-ai/>
- <https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/>
- <https://opentelemetry.io/docs/specs/semconv/attributes-registry/gen-ai/>
- <https://niteagent.com/blog/2026-05-25-openinference-vs-otel-agent-tracing/>

### AP2

- <https://ap2-protocol.org/>
- <https://github.com/google-agentic-commerce/AP2>
- <https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol>
- <https://docs.connect.worldline-solutions.com/documentation/ConnectAI/agent-payments-protocol-ap2>
- <https://www.descope.com/learn/post/ap2>
- <https://cloudsecurityalliance.org/blog/2025/10/06/secure-use-of-the-agent-payments-protocol-ap2-a-framework-for-trustworthy-ai-driven-transactions>

### UCP

- <https://ucp.dev/>
- <https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/>
- <https://github.com/Universal-Commerce-Protocol/ucp>
- <https://github.com/Universal-Commerce-Protocol/ucp-schema>
- <https://shopify.engineering/ucp>
- <https://developers.google.com/merchant/ucp/guides/ucp-profile>

### A2UI

- <https://a2ui.org>

### OWASP

- <https://owasp.org/www-project-top-10-for-large-language-model-applications/>
- <https://genai.owasp.org/llm-top-10/>
- <https://genai.owasp.org/llmrisk2025/>
- <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>
- <https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/>
- <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>
- <https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>
- <https://www.trydeepteam.com/docs/frameworks-owasp-top-10-for-agentic-applications>
- <https://www.lakera.ai/blog/the-progressive-breach-model-behind-the-owasp-top-10-for-agentic-applications>
- <https://auth0.com/blog/owasp-top-10-agentic-applications-lessons/>
- <https://labs.lares.com/owasp-agentic-top-10/>

### MITRE ATLAS

- <https://atlas.mitre.org/>
- <https://atlas.mitre.org/pdf-files/SAFEAI_Full_Report.pdf>
- <https://www.vectra.ai/topics/mitre-atlas>
- <https://www.startupdefense.io/mitre-atlas-techniques/aml-t0051-llm-prompt-injection>
- <https://www.trydeepteam.com/docs/frameworks-mitre-atlas>
- <https://www.getastra.com/blog/security-audit/mitre-atlas/>
- <https://medium.com/@ferkhaled2004/mapping-owasp-top-10-for-llm-ai-applications-to-mitre-atlas-a-comprehensive-guide-e97013500bc4>

### NIST AI RMF

- <https://www.nist.gov/itl/ai-risk-management-framework>
- <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf>
- <https://www.libertify.com/interactive-library/nist-ai-600-1-generative-ai-profile/>
- <https://docs.modulos.ai/frameworks/nist-ai-rmf/generative-ai-profile>
- <https://labs.cloudsecurityalliance.org/agentic/agentic-nist-ai-rmf-profile-v1/>

### Benchmarks

- <https://arcprize.org/>
- <https://arcprize.org/leaderboard>
- <https://arxiv.org/pdf/2505.11831> (ARC-AGI-2)
- <https://arxiv.org/pdf/2601.10904> (ARC Prize 2025 Technical Report)
- <https://www.swebench.com>
- <https://localaimaster.com/models/swe-bench-explained-ai-benchmarks>
- <https://github.com/sierra-research/tau2-bench>
- <https://arxiv.org/pdf/2406.12045> (Tau-Bench)
- <https://awesomeagents.ai/leaderboards/web-agent-benchmarks-leaderboard/>
- <https://browser-use.com/posts/online-mind2web-benchmark>
- <https://arxiv.org/pdf/2504.12516> (BrowseComp)
- <https://arxiv.org/pdf/2508.13186> (MM-BrowseComp)
- <https://arxiv.org/abs/2308.03688> (AgentBench)
- <https://metr.org/research/>
- <https://arxiv.org/abs/2411.15114> (RE-Bench)

### Eval Frameworks

- <https://crfm.stanford.edu/helm/>
- <https://github.com/stanford-crfm/helm>
- <https://github.com/google/BIG-bench>
- <https://chat.lmsys.org/>
- <https://www.swfte.com/lmsys-leaderboard>
- <https://metr.org/>

### Red-Team Datasets & Attacks

- <https://arxiv.org/pdf/2310.08419> (PAIR)
- <https://arxiv.org/pdf/2310.15140> (AutoDAN)
- <https://arxiv.org/html/2410.05295> (AutoDAN-Turbo)
- <https://arxiv.org/pdf/2404.01833> (Crescendo)
- <https://arxiv.org/pdf/2404.04849> (Logic-Chain Injection)
- <https://arxiv.org/pdf/2408.11182> (Carrier Articles)
- <https://arxiv.org/pdf/2405.20413> (Cipher Characters)
- <https://arxiv.org/html/2506.00781v2> (CoP — Agentic Red-team)
- <https://arxiv.org/pdf/2506.00782> (Jailbreak-R1)
- <https://arxiv.org/pdf/2601.03699> (RedBench)
- <https://arxiv.org/pdf/2501.01335> (CySecBench)
- <https://safetyprompts.com/>
- <https://github.com/Libr-AI/OpenRedTeaming>
- <https://www.sciencedirect.com/science/article/pii/S2666827025001987> (algorithmic red-team survey)
- <https://www.trydeepteam.com/docs/red-teaming-adversarial-attacks-crescendo-jailbreaking>
- <https://www.cybernetist.com/2024/09/23/some-notes-on-adversarial-attacks-on-llms/>
