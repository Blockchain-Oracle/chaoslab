# 01 — First-Principles Capabilities of the Google Cloud Rapid Agent Stack

> Source files: `02b-gemini-enterprise-agent-platform.md`, `partner-arize.md`, `partner-elastic.md`, `partner-fivetran.md`, `partner-gitlab.md`, `partner-mongodb.md`, `partner-dynatrace.md`. All citations inline as §.

---

## 1. Methodology

The platform marketing language ("Agent Runtime", "Agent Optimizer", "Memory Bank") describes **products**, not capabilities. A capability is the atomic unit of *what the system can do that other systems cannot*. To find them, I read each component asking: *"strip the brand name off — what is the smallest unit of value this primitive provides that I could not assemble from a vanilla Python script + the Gemini API alone?"* Anything reducible to "could be hand-rolled in 20 lines" gets discarded. What remains is the irreducible primitive surface. I then ask the inverse: *"what composition of two or three primitives unlocks a class of agent that is structurally impossible on a competitor stack (OpenAI/Anthropic/Bedrock/AutoGen)?"* — those are the wedge-defining combinations. Capabilities are extracted independently of which product surfaces them; the **Source primitive** field maps capability back to product.

---

## 2. Atomic capabilities of the Google-side platform

### G1. Sub-second agent cold start with up to 7-day execution lifetime
- **Capability:** Spin up an agent from cold in <1s and let it run continuously for up to 7 days on the same managed runtime instance.
- **Without this:** You're forced into either (a) cron-driven short-lived Lambda-style invocations that can't hold long state, or (b) self-managed K8s pods with hand-rolled checkpointing. Multi-day deliberation loops become operationally untenable.
- **Composes with:** G2 (Memory Bank), G6 (multi-agent A2A), G11 (Agent Optimizer's feedback loop).
- **Source primitive(s):** Agent Runtime (formerly Agent Engine / Reasoning Engine). See `02b §5`.

### G2. Persistent cross-session user-scoped memory
- **Capability:** The agent remembers facts, preferences, and prior reasoning across distinct user sessions without the developer wiring a vector DB, Redis, or session-state machine.
- **Without this:** You either rebuild a memory store (Redis + vector index + retrieval logic) or send the entire conversation history into the prompt every turn, which inflates token cost and dies at context-window scale.
- **Composes with:** G3 (Sessions for in-session continuity), P5 (Elastic memory layer for richer search over remembered docs).
- **Source primitive(s):** Memory Bank. See `02b §7`.

### G3. Auto-tracked multi-turn conversation state per user
- **Capability:** Per-user / per-custom-ID session state is captured for free with no developer effort — every turn, every tool call, every model response is auto-bound to a session.
- **Without this:** You have to design and implement a session ID convention, persist it, recover it on restarts, and reconcile it with multiple concurrent users.
- **Composes with:** G2, G7 (Identity-per-agent for auditability).
- **Source primitive(s):** Agent Sessions. See `02b §6`.

### G4. Sandboxed code-execution + UI-interaction in a managed environment
- **Capability:** The agent can write and execute arbitrary code, or drive a legacy UI (RPA-style), inside a sandbox the runtime brings up automatically.
- **Without this:** Code-running agents require operator-managed containers, gVisor configs, or you ban code execution entirely. UI-driving agents require Playwright + isolation infra you build yourself.
- **Composes with:** G1 (long-running so the sandbox can persist between thinking steps), P11 (GitLab pipeline triggers from generated code).
- **Source primitive(s):** Agent Sandbox (a.k.a. Code Execution). See `02b §8`.

### G5. Agent-as-IAM-principal (one identity per deployed agent)
- **Capability:** Every deployed agent gets its own IAM principal — actions taken by the agent are attributable to *that specific agent*, not the developer who deployed it.
- **Without this:** Audit trails collapse — "did the human or the agent take this action?" becomes unanswerable, which blocks regulated-industry deployment.
- **Composes with:** Any production-shaped wedge in finance/healthcare/compliance.
- **Source primitive(s):** Agent Identity. See `02b §9`.

### G6. Native agent-to-agent (A2A) inter-process protocol
- **Capability:** Agents discover each other and communicate as microservices over an open standard, without rolling custom queues, RPC, or message buses.
- **Without this:** Multi-agent systems devolve into ad-hoc subprocess plumbing, or you pick one framework's proprietary orchestrator and lock in.
- **Composes with:** G1 (long-running parent agent coordinating worker agents), G8 (Registry to discover peers), G9 (A2UI for the UI agent).
- **Source primitive(s):** A2A protocol + Agent Registry. See `02b §10` and protocol table.

### G7. Auto-cataloged tool/agent discovery (Registry)
- **Capability:** Agents discover available MCP servers and peer agents at runtime, without hardcoded endpoint lists.
- **Without this:** Tool wiring becomes a static config problem; you can't have one agent that *dynamically chooses which other agents to delegate to* based on what's currently registered.
- **Composes with:** G6 (A2A), partner MCPs (auto-discovery of Phoenix/Atlas/Elastic/etc.).
- **Source primitive(s):** Agent Registry. See `02b §10`.

### G8. Agent-generated dynamic UI (A2UI)
- **Capability:** The agent emits a UI specification per query — a different interface for different intents — rather than fitting all answers into one fixed app shell.
- **Without this:** You ship a chatbot, a dashboard, or a form. The "interface that morphs to the intent" pattern requires a custom rendering layer + protocol.
- **Composes with:** G6 (A2A — UI as a peer agent), partner data MCPs (the UI reflects what the data agent fetched).
- **Source primitive(s):** A2UI protocol. See `02b §1.4` protocol table. Sleeper: almost no hackathon entrant will use this.

### G9. Agent-initiated payments (AP2)
- **Capability:** Agent autonomously transacts via a standard payment protocol — it doesn't just *recommend* the buy, it *executes* it.
- **Without this:** You're locked into Stripe-as-tool wrappers per provider, with no standard counterparty signal that "the actor here is an agent, not a human."
- **Composes with:** G5 (Identity — *which* agent paid), P2 (Phoenix groundedness eval — block payment if confidence is low), partner data MCPs (for "decide what to buy").
- **Source primitive(s):** AP2 protocol. See `02b §1.4`.

### G10. Self-improvement loop over agent failure signals (Optimizer)
- **Capability:** A managed feedback loop ingests failure signals from the agent's own runs and refines its instructions — without the developer hand-curating prompt diffs.
- **Without this:** Prompt engineering stays manual. The agent never improves between hackathon and v1.0 unless a human re-reads logs.
- **Composes with:** P1 (Phoenix traces as the failure-signal source), P3 (Phoenix datasets as the regression set), G1 (long-running so the loop is continuous).
- **Source primitive(s):** Agent Optimizer. See `02b §20`.

### G11. Native multi-step interaction evaluation (non-deterministic test harness)
- **Capability:** Auto-evaluate that a *multi-step* agent transcript matches a desired outcome, despite LLM non-determinism. Equivalent of `forge test` but for fuzzy traces.
- **Without this:** You ship without a regression suite. Every prompt edit is a guess. Compares to Arize §3 — Google's native Agent Evaluation overlaps Phoenix here.
- **Composes with:** G12 (Simulation generates the inputs; Evaluation grades the outputs).
- **Source primitive(s):** Agent Evaluation. See `02b §18`.

### G12. Auto-generated edge-case scenario synthesis (Simulation)
- **Capability:** Auto-generates thousands of synthetic interactions to stress-test the agent before prod. Inputs are platform-synthesized, not hand-written.
- **Without this:** Edge case discovery is manual — you only find the failure modes you imagine. Long-tail failures stay hidden.
- **Composes with:** G11 (Evaluation grades them), G10 (Optimizer learns from failures).
- **Source primitive(s):** Agent Simulation. See `02b §19`.

### G13. Native PII / prompt-injection sanitization at the model boundary
- **Capability:** Input prompts get scrubbed for injection attacks, output responses for PII leaks, without code-side regex work.
- **Without this:** You either ship the risk, or build the sanitizer yourself (regex + entity recognition + DLP rules + maintenance).
- **Composes with:** Any regulated-domain wedge.
- **Source primitive(s):** Model Armor. See `02b §12`.

### G14. Five-protocol composition surface (MCP + A2A + A2UI + AP2 + UCP)
- **Capability:** A single agent process can natively speak five open agent protocols simultaneously — tools, peers, UIs, payments, commerce — without bridging libraries.
- **Without this:** You pick a framework that supports one or two protocols (OpenAI Assistants → tools only; AutoGen → custom A2A; LangChain → tools). Multi-protocol agents become custom adapters.
- **Composes with:** Everything. This is the meta-capability.
- **Source primitive(s):** ADK + protocol clients shipped with the stack. See `02b §1.4`.

---

## 3. Atomic capabilities of each partner MCP

### 3.1 Arize / Phoenix MCP — `@arizeai/phoenix-mcp`

#### P1. Agent reads its own OpenTelemetry execution traces
- **Capability:** The agent queries its own past spans — tool calls, model calls, latencies, errors — as structured data at runtime.
- **Without this:** Traces are for humans only. Agents can't introspect their own failure modes; they re-run blind.
- **Composes with:** G10 (Optimizer), G11 (Evaluation feeds back to traces), G6 (one agent reads *another* agent's traces).
- **Source primitive(s):** Phoenix MCP `list_traces`, `get_span`, `list_spans`. See `partner-arize.md §MCP tools`.

#### P2. Agent runs an A/B prompt experiment from inside its own loop
- **Capability:** The agent picks two prompt variants, runs both against a dataset, compares scores, ships the winner — autonomously.
- **Without this:** Prompt A/B is human-driven. The agent can't optimize itself between requests.
- **Composes with:** G10 (Optimizer proposes; Phoenix experiment validates).
- **Source primitive(s):** Phoenix MCP `experiments`. See `partner-arize.md §MCP tools`.

#### P3. Agent curates and grows an eval dataset programmatically
- **Capability:** When the agent finds a new failure mode at runtime, it adds the input as a synthetic dataset example for future regression testing.
- **Without this:** Datasets are static. Regression coverage stays at whatever the developer thought of on day 1.
- **Composes with:** P1 (find failures in traces), P2 (run experiment against new dataset).
- **Source primitive(s):** Phoenix MCP `datasets` (`add_dataset_example`). See `partner-arize.md §MCP tools`.

#### P4. Agent versions and tags its own prompts
- **Capability:** The agent can read, list, update, and tag (`prod`/`staging`/`latest`) its own prompt templates as first-class artifacts.
- **Without this:** Prompts are code strings, edited by humans, deployed by humans. The agent has no surface to evolve them.
- **Composes with:** P2 (variant testing), G10 (Optimizer proposes new prompt versions).
- **Source primitive(s):** Phoenix MCP `prompts`. See `partner-arize.md §MCP tools`.

#### P5. Agent attaches LLM-as-judge scores back to its own spans
- **Capability:** Every span gets graded (correctness, groundedness, toxicity, tool-call-accuracy) and the score is attached back — queryable later.
- **Without this:** Quality signals stay external to the trace. You can't filter "show me my low-groundedness spans from the last hour."
- **Composes with:** P1 (filter spans by score), G9 (AP2 — block payment if score below threshold).
- **Source primitive(s):** Phoenix annotation configs + judge framework. See `partner-arize.md §Core surface`.

### 3.2 Elastic MCP — Agent Builder endpoint in Kibana

#### P6. Single-query hybrid search: keyword + vector + structured filter
- **Capability:** One MCP call returns docs ranked by fused score across BM25, vector similarity, and structured predicates (`bedrooms >= 3 AND city = "Boston"`).
- **Without this:** You wire Elastic for BM25, Pinecone/Weaviate for vectors, and Postgres for filters — three systems, three sync problems, no fused ranking.
- **Composes with:** Any RAG wedge; G2 (Memory Bank as semantic store).
- **Source primitive(s):** Elastic Agent Builder MCP. See `partner-elastic.md §Core surface 1`.

#### P7. Auto-embed-on-write via `semantic_text` field
- **Capability:** Drop a string into a `semantic_text` field and the platform handles chunking + embedding + indexing transparently.
- **Without this:** You write the chunking strategy, pick the embedding model, batch-call the embedding API, manage failures, version it.
- **Composes with:** P6 (immediately queryable), P10 (Fivetran pipes raw → Elastic indexes embedded).
- **Source primitive(s):** Elasticsearch `semantic_text` exposed via Agent Builder. See `partner-elastic.md §Core surface 1`.

#### P8. Custom ES|QL tools defined declaratively in Kibana
- **Capability:** Define a parameterized analytical tool ("aggregate player xG by position over the last N matches") in Kibana with a description; the agent picks it by description and parameters at runtime.
- **Without this:** Every analytical tool is a function in your agent code, with hand-written descriptions, params, and tests.
- **Composes with:** G14 (MCP protocol exposes the tool), G6 (other agents discover and reuse).
- **Source primitive(s):** Elastic Agent Builder Tools. See `partner-elastic.md §Core surface 2-3`.

#### P9. Agentic long-term memory via semantic search over a memory index
- **Capability:** Write session summaries / facts as docs to an Elastic index; recall semantically. Memory is structured, queryable by metadata, persistable beyond one Memory Bank instance.
- **Without this:** You're choosing between vanilla Memory Bank (managed, opaque) or a self-built vector store. Elastic gives a *queryable* memory you can also full-text search.
- **Composes with:** G2 (complement to Memory Bank — Elastic for searchable structured memory).
- **Source primitive(s):** Elastic indices accessed via Agent Builder. See `partner-elastic.md §Core surface 5`.

### 3.3 Fivetran MCP — `fivetran-mcp`

#### P10. Pre-joined SaaS data without writing a single connector
- **Capability:** Salesforce + Stripe + HubSpot + Zendesk → one BigQuery schema, kept in sync, schema-drift-handled. The agent reads pre-joined business data with zero ingestion code.
- **Without this:** You write 700-connector-equivalent integrations, manage auth refresh, handle pagination, deal with schema migrations.
- **Composes with:** Any business-Q&A wedge; P12 (freshness-gated reasoning).
- **Source primitive(s):** Fivetran connectors + destination warehouse. See `partner-fivetran.md §Core surface 1-3`.

#### P11. Agent triggers an ELT pipeline refresh on demand
- **Capability:** Mid-conversation, the agent decides "data is stale, sync now" and triggers Fivetran sync — *before* answering.
- **Without this:** Data freshness is operationally separate from agent reasoning. The agent either trusts whatever is in the warehouse, or refuses to answer.
- **Composes with:** P10 (the data being refreshed), P12 (freshness check that gates the trigger).
- **Source primitive(s):** Fivetran MCP `trigger_sync`, `manage_pipeline`. See `partner-fivetran.md §MCP tools`.

#### P12. Agent introspects pipeline freshness / health as a tool call
- **Capability:** "Is my Salesforce data fresh? When did it last sync? Are any connections failing?" — the agent gets answers without leaving the conversation.
- **Without this:** Trust-in-data becomes a tribal-knowledge problem. The agent answers from stale data and the user can't tell.
- **Composes with:** P11 (introspect → trigger), G10 (Optimizer learns "always check freshness before X-type queries").
- **Source primitive(s):** Fivetran MCP `get_connection_status`, `get_last_sync`, `list_connections`. See `partner-fivetran.md §MCP tools`.

#### P13. Agent reads schema-change history programmatically
- **Capability:** "What columns changed in the Salesforce.opportunities table in the last 7 days?" — answerable as a tool call.
- **Without this:** Schema drift is invisible to the agent. Downstream dashboard breakage cascades without warning.
- **Composes with:** P12 (freshness), GitLab P15 (auto-open MR to fix dependent code).
- **Source primitive(s):** Fivetran MCP metadata + schema history. See `partner-fivetran.md §MCP tools`.

### 3.4 GitLab MCP — official server at `/api/v4/mcp`

#### P14. Agent authors and updates merge requests with reviewers
- **Capability:** Open MRs with assignees, labels, source/target branches; comment threaded reviews on diffs; tag for approval — all from one tool surface.
- **Without this:** Code-changing agents are stuck at "suggestion → human implements" rather than "MR is open, here is the diff, please review."
- **Composes with:** G4 (Sandbox writes the code), P16 (CI runs on the MR), G9 (AP2 — pay for the result of CI).
- **Source primitive(s):** GitLab MCP `create_merge_request`, `get_merge_request_diffs`, `create_workitem_note`. See `partner-gitlab.md §Exposed tools`.

#### P15. Agent reads diffs + commits + pipeline outcomes as one correlated object
- **Capability:** "What did this MR change, what tests ran on it, which jobs failed, on which commit?" — a single contextual view the agent reasons over.
- **Without this:** You correlate `git diff` + a CI log file + a job artifact yourself. The reasoning chain breaks across three APIs.
- **Composes with:** P17 (semantic code search to find the root cause), G10 (Optimizer learns common fix patterns).
- **Source primitive(s):** GitLab MCP `get_merge_request_diffs` + `get_merge_request_pipelines` + `get_pipeline_jobs`. See `partner-gitlab.md §Exposed tools`.

#### P16. Agent triggers / retries / cancels CI/CD pipelines
- **Capability:** Pipeline lifecycle is a first-class tool surface, not a webhook receiver.
- **Without this:** CI is fire-and-forget. The agent can react to outcomes but can't actively *drive* the pipeline (retry the flaky job, run only one stage, etc.).
- **Composes with:** P14 (open MR → trigger CI), G9 (gated release on AP2 payment).
- **Source primitive(s):** GitLab MCP `manage_pipeline`. See `partner-gitlab.md §Exposed tools`.

#### P17. Semantic code search across the repo (not grep)
- **Capability:** "Find code that does X" — by meaning, not by exact text. The agent locates the relevant function even when the user describes intent rather than keywords.
- **Without this:** You ship grep-based agents that fail on rename, paraphrase, or semantic equivalence.
- **Composes with:** P15 (correlate failure to semantic code locus).
- **Source primitive(s):** GitLab MCP `semantic_code_search`. See `partner-gitlab.md §Exposed tools`.

### 3.5 MongoDB MCP — `mongodb-mcp-server` (Winter 2026 release)

#### P18. Insert-with-auto-embedding (single MCP call)
- **Capability:** `insert-many` with a text field → MCP server calls Voyage AI, embeds, stores embedding + doc atomically.
- **Without this:** You orchestrate "call embedding model → wait → store both" yourself, with failure modes at each step.
- **Composes with:** P19 ($vectorSearch over the same docs).
- **Source primitive(s):** MongoDB MCP `insert-many` with embed config. See `partner-mongodb.md §Vector Search`.

#### P19. `$vectorSearch` + `$match` + `$lookup` in one aggregation pipeline
- **Capability:** Vector similarity + structured filter + join — single round-trip, fused ranking, one query language.
- **Without this:** Three systems (Pinecone + Postgres + glue code), three latencies, three failure modes, three configs.
- **Composes with:** P18 (the inserted docs), G2 (Memory Bank backed by Mongo).
- **Source primitive(s):** MongoDB Atlas `$vectorSearch`. See `partner-mongodb.md §Core surface 3`.

#### P20. Agent provisions its own database infrastructure
- **Capability:** Agent calls `atlas-create-free-cluster`, `atlas-create-db-user`, `atlas-create-access-list` — it owns the lifecycle, not the dev.
- **Without this:** Database provisioning is a human-only step. Agents can't instantiate isolated workspaces per user/per-tenant on demand.
- **Composes with:** G5 (Identity bound to the cluster the agent provisioned), G9 (AP2 — pay-as-you-provision).
- **Source primitive(s):** MongoDB MCP atlas-* tools. See `partner-mongodb.md §Exposed tools`.

#### P21. Real-time stream ingestion + agent reaction in one stack
- **Capability:** Kafka → Atlas Stream Processing → MongoDB → agent's `$vectorSearch` query reacts to the streamed event semantically.
- **Without this:** Stream ingestion (Flink/Beam) and agent reasoning are separate stacks. Stream → vector search round-trip is custom infra.
- **Composes with:** P19, G1 (long-running consumer agent), Dynatrace P24 (correlated trace alongside the stream event).
- **Source primitive(s):** Atlas Stream Processing MCP tools. See `partner-mongodb.md §Core surface 5`.

### 3.6 Dynatrace MCP — `@dynatrace-oss/dynatrace-mcp-server`

#### P22. Agent queries live production telemetry across logs+traces+metrics in one query language
- **Capability:** `execute_dql` spans every signal type (logs, traces, metrics, security events) — one query language, one round-trip.
- **Without this:** Multi-signal RCA requires querying three or four backends and joining client-side.
- **Composes with:** P23 (Davis causal RCA), GitLab P15 (correlate prod incident to MR), P25 (workflow trigger).
- **Source primitive(s):** Dynatrace MCP `execute_dql`. See `partner-dynatrace.md §Grail`.

#### P23. Agent reads Davis causal-RCA output as structured data
- **Capability:** "Metric X spiked because deploy Y changed config Z on upstream service W" — delivered as machine-readable causal graph, not a chart.
- **Without this:** Causal RCA is a human-eyeballed-graph task. Agents can't chain it into automated remediation.
- **Composes with:** G10 (Optimizer learns from RCA), GitLab P14 (open MR to revert deploy Y), P26 (open security ticket).
- **Source primitive(s):** Dynatrace MCP `chat_with_davis_copilot`, `execute_davis_analyzer`. See `partner-dynatrace.md §Exposed tools`.

#### P24. NL→DQL synthesis and DQL→NL explanation as MCP-level helpers
- **Capability:** The agent doesn't need to *know* DQL — it asks Dynatrace to generate the query from intent and back-translate results.
- **Without this:** Agents need DQL expertise baked in, or you train a fine-tune for it.
- **Composes with:** P22 (the actual execution).
- **Source primitive(s):** Dynatrace MCP `generate_dql_from_natural_language`, `explain_dql_in_natural_language`. See `partner-dynatrace.md §Grail`.

#### P25. Agent triggers operational workflows (Slack/email/runbooks/custom events)
- **Capability:** Same call-graph as the diagnostic — once root cause is known, the agent fires the remediation channel from the same MCP surface.
- **Without this:** Diagnosis and remediation are separate stacks (Datadog for read, PagerDuty/Jira for write).
- **Composes with:** P23 (RCA → action), G5 (Identity stamps the action).
- **Source primitive(s):** Dynatrace MCP `create_workflow_for_notification`, `send_slack_message`, `send_event`. See `partner-dynatrace.md §Exposed tools`.

#### P26. Runtime CVE / vulnerability exposure (not source-side)
- **Capability:** "Which CVEs are actually loaded into running JARs in production right now?" — not "what's listed in `package.json`."
- **Without this:** You scan source code; the running runtime can differ wildly (dynamic class-loading, dependency override, lazy-loaded modules). Agents miss real exposure.
- **Composes with:** GitLab P14 (open MR with patch), P22 (correlate to incident).
- **Source primitive(s):** Dynatrace MCP `list_vulnerabilities`. See `partner-dynatrace.md §Exposed tools`.

---

## 4. Capability combinations that nothing else can do

### C1. Self-debugging payment agent
- **Combination:** P1 (read own traces) + P5 (judge groundedness) + G9 (AP2) + G10 (Optimizer)
- **What it enables:** An agent that autonomously transacts (AP2) but *refuses to transact* when its own groundedness eval on the proposed transaction drops below a threshold — and rewrites its own decision prompt when its rolling failure rate increases.
- **Why this stack uniquely enables it:** Anthropic/OpenAI ship Claude/GPT + tools but no native payment protocol, no built-in optimizer, no self-trace MCP. AWS Bedrock has Guardrails but no AP2-equivalent. AutoGen has multi-agent but no native eval-backed gating + payment protocol.
- **Example agent:** An autonomous procurement agent for SME ops — it buys cloud credits / SaaS seats / commodity supplies, but auto-halts and self-reflects when groundedness on the supplier choice drops.

### C2. Schema-drift to merge-request reflex
- **Combination:** P13 (Fivetran schema-change history) + P17 (GitLab semantic_code_search) + P14 (open MR) + G4 (Sandbox to write code)
- **What it enables:** When a source SaaS column changes, the agent immediately finds every line of downstream code that consumes it (semantic, not grep), writes the migration patch in the sandbox, opens the MR with the diff + a regression test, and pings the right reviewer.
- **Why this stack uniquely enables it:** Requires Fivetran's first-class schema event surface + GitLab's semantic code search + sandboxed execution — no single competitor stack offers all three. ELT vendors (Airbyte/Stitch) don't expose schema-history-as-tool; GitHub Copilot has code-edit but no Fivetran tool; nobody else has all three under one agent.
- **Example agent:** "DataContract sentinel" — on every Fivetran schema_change event, the agent opens a patching MR within minutes.

### C3. Production-incident-to-fix conveyor
- **Combination:** P22 (DQL live telemetry) + P23 (Davis causal RCA) + P15 (GitLab MR diffs + pipelines) + P14 (open MR) + G6 (A2A for multi-agent split)
- **What it enables:** Pager fires → telemetry agent queries DQL → Davis identifies the upstream commit → code agent fetches that MR's diff and semantic-searches related code → revert MR is filed and queued → SRE just approves.
- **Why this stack uniquely enables it:** OpenAI/Anthropic can have one model that does all of this only as a monolithic prompt chain with hand-rolled tools. Here it's two specialized A2A peers; telemetry agent passes the causal-graph object directly to the code agent. No competitor stack ships Dynatrace + GitLab MCPs + native A2A.
- **Example agent:** "SRE Conveyor" — pager → revert PR queued for review in <5 minutes.

### C4. Live-data adaptive UI
- **Combination:** P6 (Elastic hybrid search) + P19 (Mongo $vectorSearch) + G8 (A2UI) + G2 (Memory Bank)
- **What it enables:** A user query like "show me what's happening at our stores this week" returns *a different UI shape* per query — a map if it's geo, a table if it's numeric, a timeline if it's chronological — populated from live hybrid search across structured (Mongo metadata) + unstructured (Elastic free-text) sources, with the layout choice persisted to memory for the next session.
- **Why this stack uniquely enables it:** A2UI is a protocol almost nobody else implements. Combined with two hybrid-search MCPs and Memory Bank, you get UI that's data-shape-aware, semantic, and adaptive. Streamlit + custom front-end is the alternative — 10x the work.
- **Example agent:** A retail-HQ ops console that morphs based on the question — "store health" gives a heatmap, "vendor invoices" gives a queue, "trending complaints" gives a clustered timeline.

### C5. Agent that benchmarks itself against alternative prompt variants live
- **Combination:** P2 (Phoenix experiments) + P4 (Phoenix prompts versioning) + G10 (Agent Optimizer) + G11 (Agent Evaluation) + P3 (datasets) + G12 (Simulation)
- **What it enables:** The agent runs both `prompt-v3` and `prompt-v4` against a Simulation-generated edge case set every N minutes, scores them via Phoenix, and ships whichever wins — without a human touching anything between deploys.
- **Why this stack uniquely enables it:** Competitor frameworks ship one or two of these (PromptLayer has versioning + experiments; LangSmith has eval) but nobody combines Simulation (input synthesis) + Optimizer (instruction-rewrite) + Phoenix (judge + dataset + experiments) + native runtime that survives 7 days of continuous experimentation.
- **Example agent:** "Prompt-Ops daemon" — runs as a sibling A2A agent, autopilots prompt evolution for any peer agent registered in the Agent Registry.

### C6. Provision-on-demand multi-tenant agent
- **Combination:** P20 (Mongo Atlas provisioning) + G5 (Identity per agent) + G9 (AP2) + G14 (multi-protocol)
- **What it enables:** A meta-agent that, when a new tenant signs up (and pays via AP2), provisions an isolated Mongo cluster, attaches a fresh agent identity, registers it in the Registry, and the tenant gets their own private agent with their own backing store — all without a human.
- **Why this stack uniquely enables it:** Provisioning agents exist (Terraform-as-tool) but no other stack pairs DB provisioning MCP + agent identity-per-deployment + native payment protocol + dynamic registry in one process.
- **Example agent:** B2B SaaS distribution where every new customer = one provisioned agent + one cluster.

### C7. Causal-RCA-driven prompt evolution
- **Combination:** P23 (Davis causal RCA) + P1 (Phoenix traces) + G10 (Optimizer)
- **What it enables:** When the agent's own production behavior degrades (Davis detects it), Davis explains "the regression is because service-X (= your Gemini agent) started taking longer reasoning paths after deploy Y." Phoenix traces confirm. Optimizer rewrites the instruction. This is *causal* prompt iteration, not correlational.
- **Why this stack uniquely enables it:** Combines two observability worlds (production APM via Dynatrace + LLM-trace via Phoenix) that are siloed in every competitor stack. You'd need to wire OpenTelemetry → Dynatrace + Phoenix manually elsewhere.
- **Example agent:** A self-tuning customer-support agent that doesn't just measure its own quality (Phoenix) but understands its own production-system degradation cause (Davis) and rewrites itself accordingly.

### C8. Fresh-data-gated reasoning with eval-bounded answer
- **Combination:** P12 (Fivetran freshness) + P11 (sync trigger) + P5 (Phoenix groundedness eval) + G9 (AP2 optional)
- **What it enables:** Agent receives a business question → checks Fivetran freshness → triggers sync if stale → answers → judges its own groundedness on the answer → if score is high, optionally executes a transaction (AP2). The decision pipeline is structurally honest about both *data freshness* and *answer confidence*.
- **Why this stack uniquely enables it:** Most agents trust data and don't self-grade. Combining ELT-aware freshness + eval-bounded answer + optional payment is unique to having Fivetran + Phoenix + AP2 in the same agent.
- **Example agent:** A trading desk research copilot that won't issue a "buy" recommendation if Stripe revenue data is >4h old OR if its own groundedness eval is <0.85.

---

## 5. Structural advantages this stack has over competing stacks

### S1. Five-protocol composition is the platform's moat
- MCP + A2A + A2UI + AP2 + UCP are all open standards, and ADK speaks all five natively. Competitors typically ship one or two. Building a "buy something based on a peer agent's recommendation with a custom UI for the result" is one ADK setup; it's a custom adapter project on every other stack. See `02b §1.4`.

### S2. <1-second cold start + 7-day continuous reasoning lifetime
- This single spec window enables agent shapes that don't exist on Lambda/Cloud Functions (too short) or self-hosted K8s (too operationally heavy). 7 days = "the agent can deliberate over a business week before acting." See `02b §5`.

### S3. Native self-improvement loop (Optimizer + Evaluation + Simulation)
- Three primitives that, combined, give you a closed-loop self-improving agent without any third-party stitching. Equivalent on competitor stacks requires three vendors + custom glue. See `02b §16-20`.

### S4. Native A2A peer discovery via Agent Registry
- The Registry auto-catalogs first-party MCPs, third-party A2A agents, and partner MCP servers — so multi-agent / multi-tool systems don't need static config files. Compare to AutoGen where peer wiring is hand-coded. See `02b §10`.

### S5. Partner MCP servers ship as MCP primitives, not SDKs
- Phoenix, Mongo, Elastic, Fivetran, GitLab, Dynatrace — all expose their full surface as MCP. The agent uses one protocol to reach all of them. On AWS Bedrock or Anthropic-only stacks, you'd be wiring six SDKs by hand. See partner files §MCP server sections.

---

## 6. Structural disadvantages / constraints to design around

### D1. Hackathon rules forbid competing LLM runtimes as primary orchestrator
- Per the rules (see `02a` / `mcp-primer`), Claude / OpenAI / LangChain-as-primary are banned for this hackathon. Gemini must be the LLM, ADK the orchestrator. This kills any wedge that depends on a non-Gemini frontier model. (Hackathon-specific; not a permanent platform limit.)

### D2. Code-first runtime mandatory for Phoenix tracing (and most evaluation depth)
- Visual Agent Builder alone cannot be OpenInference-instrumented. Any Arize-track wedge must use ADK / Agent Runtime / Cloud Run. See `partner-arize.md §Gotchas`.

### D3. 14-day partner trial squeeze (Elastic, Fivetran) and 15-day (Dynatrace)
- Trials expire mid-judging if started too early. Recording demo video while trial is live is the operational backstop. Limits long-horizon eval demos to <14 days of real history. See partner files §Free tier.

### D4. Agent Policies + Agent Gateway are private preview
- Fine-grained IAM-for-agents and single-ingress-chokepoint policies aren't accessible to hackathon participants. Wedges that depend on "agent A can call tool X but not Y" are demoable only in narrative, not in code. See `02b §11, §13`.

### D5. $100 promo credit ceiling on token spend
- Caps the size of any continuous-evaluation demo. A naive "run 1000 simulated interactions per hour" loop will blow through credit. Designs must be sample-efficient or pre-recorded. (Estimate from `02b`'s pricing references; verify at submission.)

### D6. Dynatrace requires real telemetry data (no sample dataset)
- Unlike Phoenix (auto-instrument → free traces) or Mongo (free M0 + sample docs), Dynatrace needs OneAgent installed on a real workload generating real traffic for 24h+. This eats 30-40% of build time on Dynatrace-primary wedges. See `partner-dynatrace.md §Trial`.

### D7. Voyage AI separate API key for Mongo auto-embedding
- The MCP auto-embed feature requires a Voyage AI key (separate signup). Workaround: embed via Vertex AI's text-embedding-005 and insert as plain arrays — but you lose the "single MCP call" elegance of P18. See `partner-mongodb.md §Free tier`.

---

## 7. Open questions

1. **Does Gemini 3.5 Flash / 3.1 Pro pricing fit within $100 credit for a continuous-eval loop?** `02b §model version note` calls this out as needing re-verification at https://ai.google.dev/gemini-api/docs/pricing.
2. **Does A2UI have working examples / SDKs in ADK as of June 2026?** Protocol exists (`a2ui.org`) and `02b §1.4` lists it, but no demo code is referenced in the research files. UNVERIFIED whether the rendering layer is ergonomic for a 9-day build.
3. **Does AP2 have a sandbox payment provider for hackathon use?** Going from `ap2-protocol.org` reference to a working "agent paid for a thing" demo requires a payment-rail counterparty. UNVERIFIED if one ships in ADK or if Stripe-test integration is the bridge.
4. **Can a single ADK agent register itself in Agent Registry programmatically, or is registration a deploy-time admin step?** `02b §10` describes auto-catalog but doesn't clarify the self-registration ergonomics.
5. **Can Agent Optimizer be triggered from inside the agent's own loop, or is it a separate batch operation?** `02b §20` implies a continuous feedback loop, but the trigger mechanism is unclear from the research files. If it's an off-line batch, combinations C5 and C7 need adjustment.
6. **Does Phoenix MCP expose write access to span annotations from inside the agent, or is annotation a human-only / batch path?** Most P5 examples reference reading annotations; the self-attaching path during an agent run is implied but UNVERIFIED.
7. **Is Memory Bank semantic (vector-indexed) or key-value?** `02b §7` describes it functionally but not architecturally. Affects whether G2 + P9 (Elastic memory) are complementary or redundant.
8. **What's the latency profile of A2A inter-agent calls vs an in-process function call?** Affects whether the C3 SRE conveyor pattern is realistic at "pager fired → MR queued in <5 min" timing.
