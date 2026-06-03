# Partner Track: Elastic (Elasticsearch + Agent Builder)

Hackathon: Google Cloud Rapid Agent Hackathon — https://rapid-agent.devpost.com/
Deadline: June 11, 2026 @ 2:00pm PDT. Judging: June 22 – July 6, 2026.
Prize per partner bucket: 1st $5,000 / 2nd $3,000 / 3rd $2,000.

---

## What the product actually is

**Elasticsearch** is the search-and-analytics database that pretty much every company uses for full-text search, log search, and now vector/semantic search. You stuff documents in, and you get back relevant ones — by keywords, by vector similarity, by a hybrid of both, or by structured filters. It's the engine behind Wikipedia search, Uber's logs, Slack's search, etc. ([elastic.co](https://www.elastic.co/cloud/cloud-trial-overview))

For this hackathon the relevant surface is **Elastic Agent Builder** — a layer Elastic added in Elasticsearch 9.2+ that exposes Elasticsearch indices + custom **ES|QL tools** + **semantic search** to AI agents over MCP. You define tools in Kibana ("this tool searches our `policies` index, takes `query`+`product_line`, returns top 5 docs with citations"), and Elastic surfaces them as MCP tools. Your Gemini agent calls them and gets back grounded, sourced results. ([elasticsearch labs — agent builder GA](https://www.elastic.co/search-labs/blog/agent-builder-elastic-ga))

For a blockchain dev: think of Elasticsearch as **the indexer layer for off-chain unstructured data**. If The Graph indexes EVM events into queryable subgraphs, Elastic indexes documents (PDFs, transcripts, support tickets, product catalogs) into queryable indices. ES|QL is Elastic's SQL-shaped query language — analogous to GraphQL queries against a subgraph. Vector/semantic search is the part that has no on-chain analog — it's RAG at scale. Agent Builder = the on-chain MCP wrapper around the indexer, so an agent can ask "find me docs about X" without writing raw query DSL.

## Core product surface

Five things Elasticsearch is genuinely best at:

1. **Hybrid search (keyword + vector + filter).** The killer feature. `semantic_text` field auto-embeds; you query with natural language plus structured filters (`bedrooms >= 3 AND city = "Boston"`) and get fused-rank results. ([elasticsearch labs — MCP intelligent search](https://www.elastic.co/search-labs/blog/mcp-intelligent-search))
2. **ES|QL** — Elastic's SQL-like query language. Statistical aggregations + search in one query. PHAROS (a prior Elastic hackathon winner) did pharmacovigilance stats entirely in ES|QL. ([elastic hackathon recap](https://www.elastic.co/blog/the-elasticsearch-agent-builder-hackathon))
3. **Agent Builder + Tool definitions.** Define a reusable tool with a query template, parameter schema, and natural-language description. The agent picks tools by description match. Tools are versioned in Kibana.
4. **RAG over private corpora.** This is the canonical Elastic agent shape: stuff your private docs into an index, vector-embed, semantic-search at runtime, return cited chunks. Production-tested at scale.
5. **Memory store for agents.** Elastic's blurb in the partner page calls it "a context layer to store memory and insights" — i.e. agent long-term memory persisted as documents, retrievable next session.

## Their MCP server

There are **TWO** Elastic MCP options and you need to know which one is current.

### Recommended (current): Elastic Agent Builder MCP endpoint

- Available in **Elasticsearch 9.2+** (Cloud Serverless has this by default).
- Defined in Kibana → Agent Builder → Tools, then surfaced at an MCP endpoint URL inside the Agent Builder UI.
- Partner page quote: _"Point Google Cloud Agent Builder at the Elastic MCP server endpoint found in the Agent Builder Tools UI in Kibana."_ ([elastic-resources](https://rapid-agent.devpost.com/details/elastic-resources))
- Exposes "all built-in and custom tools you can use to power agentic workflows." Tools include: keyword search, semantic search, ES|QL execution, index/mapping inspection, plus any custom tool you define from a query template. ([elastic.co/docs/solutions/search/mcp](https://www.elastic.co/docs/solutions/search/mcp))
- **Status: production** (Agent Builder went GA per Elasticsearch Labs).

### Deprecated (do not use for new work): `mcp-server-elasticsearch`

- The old stdio/HTTP Rust server: `docker.elastic.co/mcp/elasticsearch` ([github.com/elastic/mcp-server-elasticsearch](https://github.com/elastic/mcp-server-elasticsearch))
- Tools exposed: `list_indices`, `get_mappings`, `search`, `esql`, `get_shards`.
- Status: **deprecated** — security updates only. Elastic's official docs say to use Agent Builder MCP instead for 9.2+.
- Reason to know about it: if you self-host an older cluster, it's your only option. For a hackathon on Elastic Cloud Serverless, it is **not** the right path.

### Agent-side install (calling Elastic MCP from a Gemini ADK agent)

For the current recommended path (Agent Builder endpoint), you wire the endpoint URL + Elastic API key into your Gemini agent's MCP client config. For the deprecated stdio server:

```bash
docker run -i --rm \
  -e ES_URL=$ES_URL \
  -e ES_API_KEY=$ES_API_KEY \
  docker.elastic.co/mcp/elasticsearch stdio
```

## Free tier / trial details + gotchas

**The Elastic track is the most schedule-fragile of the three.** Read this section twice.

- **Trial length: 14 days** of full-feature Elastic Cloud (vector search, ML, semantic_text, Agent Builder). No credit card. ([elastic cloud trial overview](https://www.elastic.co/cloud/cloud-trial-overview))
- **CANNOT BE EXTENDED.** Self-managed has a `trialextension` request form; Elastic Cloud SaaS trial does not.
- **Gotcha:** signing up for Elastic Cloud via Microsoft Azure or Google Cloud Marketplace does **not** include the free trial. You must register through https://cloud.elastic.co directly (AWS-backed registration path).
- **Hackathon-specific workaround (per the prompt brief):**
  - New email + remote-reindex into a fresh trial cluster.
  - **Demo video is the backstop.** Judging runs June 22 – July 6, so even if your trial expires June 25 mid-judging, your locked 3-minute video demo is what the judges grade against. **Record the video while the cluster is live.**
- **Timing playbook:**
  - Hackathon starts May 5, deadline June 11. If you start a trial on May 5, it dies May 19 (before submission).
  - Optimal: trial signup ~May 28 → trial alive through ~June 11 (submission day) → record demo video right before deadline → if you need to fire it back up for judges (Jun 22 – Jul 6), use a fresh email + reindex.

**Other gotchas (from elastic-resources page):**

1. **Use Elastic Cloud Serverless**, not classic Elasticsearch self-hosted. Agent Builder is the value prop and it's serverless-first.
2. **Vector / semantic search must be used.** Track risk explicitly: a keyword-only search submission misses the modern Elastic value prop.
3. **Define tools in Kibana, not in code.** The partner page emphasizes "Define tools using ES|QL or semantic search" inside Agent Builder. Defining tools imperatively in your agent code while ignoring Agent Builder tooling weakens the integration story.

## What problems this partner is set up to solve well

1. **Grounded RAG over a private corpus.** Any "answer questions about my company's 50,000 PDFs / policies / past tickets" agent. Elastic is the production default for this shape.
2. **Hybrid retrieval where exact-match + semantics matter.** Finance (regulatory filings + numerical filters), real-estate (text + structured filters), healthcare (codes + free-text symptoms), retail SKU search.
3. **Persistent agent memory + session context.** Long-running agents that need to remember conversations across days; Elastic's index + semantic search makes it a "memory layer" the agent queries naturally.
4. **Log/event analytics inside an agent.** ES|QL agents that crunch event streams and produce stats in one tool call. (PHAROS-shaped pattern.)

## Concrete agent ideas that fit this partner

### Idea 1 — "WorldCup-Concierge" semantic-search agent

_Problem:_ Fans visiting host cities for the 2026 World Cup need real-time, multilingual answers to "where's the nearest halal restaurant within 5km of Gillette Stadium that's open after the match," fusing scraped city data + match schedules + dietary filters.
_Why Elastic wins this:_ Hybrid (semantic + geo + filter) search is exactly Elastic's killer use case. Vector embeddings let the agent handle multilingual queries; geo + open-hours filters use structured fields.
_Tools the agent calls:_ Elastic MCP `semantic_search` on a `venues` index, `esql` aggregation for "venues within 5km open at T+match*end," `keyword_search` on a transport index.
\_Judging fit:* Potential Impact (real-world tournament audience), Design (mobile-first multilingual UX), Technological Implementation (hybrid search done right).

### Idea 2 — "ComplianceCorp" regulated-doc Q&A agent for Financial Services

_Problem:_ A junior bank analyst spends hours hunting for the right paragraph in 10-Ks + internal compliance memos.
_Why Elastic wins this:_ Citations are mandatory in finance. Elastic's semantic*text returns chunks with stable doc IDs, which the agent surfaces as inline citations. ES|QL aggregations summarize trend findings ("how many of the last 50 filings mention X").
\_Tools the agent calls:* Custom Kibana-defined tools: `search_10k`, `search_internal_memos`, `count_by_filing_year`. All MCP-exposed.
_Judging fit:_ Quality of Idea (citation-first finance agent), Technological Implementation (custom Agent Builder tools).

### Idea 3 — "ShelfSense" retail visual-similarity agent

_Problem:_ A retail merchandiser wants to find products in the catalog visually similar to a competitor's hot item.
_Why Elastic wins this:_ Elastic's vector search handles image embeddings (CLIP-style) just as well as text. Combine with structured filters (`category`, `price_tier`, `availability`).
_Tools the agent calls:_ Elastic MCP `vector_search` on image embeddings index, `esql` for sales-trend join, custom tool `find_similar_skus`.
_Judging fit:_ Design (visual UX is the selling point), Potential Impact (retail merchandising is a real budget line).

### Idea 4 — "TicketScout" multi-tenant support agent (Brick & Mortar Retail HQ)

_Problem:_ A retail chain's HQ support team needs an agent that triages incoming store-manager tickets against past resolutions and SOP documents.
_Why Elastic wins this:_ Elastic excels at this exact shape (ticket index + SOP index + hybrid search + memory). Persisted agent memory ("we've seen this issue 3 times this month at the West Coast stores") makes it agentic, not just searchy.
_Tools the agent calls:_ `search_tickets`, `search_sops`, `save_memory` (writes a session-summary doc), `recall_memory` (semantic*text on memory index).
\_Judging fit:* Technological Implementation (memory loop), Potential Impact (replace L1 support).

### Idea 5 — "MatchAnalytics" ES|QL stats-on-demand for World Cup

_Problem:_ Sports journalist needs "show me every player with >0.5 xG in the last 10 matches who plays a fullback role" in 5 seconds.
_Why Elastic wins this:_ ES|QL is Elastic's analytics weapon. PHAROS (prior hackathon winner) used the same pattern for pharma. Stats-in-one-query is faster than BigQuery for sub-100M-row sports event tables.
_Tools the agent calls:_ Custom Kibana tools `aggregate_player_stats`, `filter_by_position`, `match_metadata_lookup`. All ES|QL.
_Judging fit:_ Quality of Idea (Bloomberg-terminal-for-sports angle), Technological Implementation (ES|QL agentic).

### Idea 6 — "DealDesk" SME-loan underwriting copilot (Financial Services)

_Problem:_ SME loan officers manually piece together credit memos from prior similar deals.
_Why Elastic wins this:_ Vector search over historical credit memos surfaces structurally similar deals; ES|QL aggregates risk distributions; Agent Builder lets the underwriter add custom tools per industry.
_Tools the agent calls:_ `find_similar_deals` (semantic), `aggregate_default_rates` (ESQL), `pull_memo_template` (keyword), Phoenix-style memory write to track decisions over time.
_Judging fit:_ Potential Impact (concrete revenue lever for banks), Quality of Idea (deal-precedent reasoning).

## Track-specific judging risks (things that kill a submission)

1. **Building a search UX instead of an agent.** If your demo looks like Google for documents (user types → results render), you've lost. The track wants **multi-step planning**: agent plans → calls tool A → reads result → decides to call tool B → produces an action, not a result list.
2. **No vector / semantic search.** Keyword-only Elastic = "I could have done this with Postgres FTS." Judges will mark this down. The semantic*text + hybrid search is \_the* differentiator.
3. **Trial expires before judging finishes.** Without a recorded demo video while the cluster was live, the judges see a dead deployment. **Record demo BEFORE the trial dies.**
4. **Not using Agent Builder tools.** Imperatively querying Elasticsearch from your agent code while ignoring Agent Builder weakens the integration story. The track explicitly wants you to define tools in Kibana.
5. **Static demo where the data isn't live.** A pre-baked JSON of search results, not a live agent query against the index, is detectable in the video.
6. **One tool, one query, done.** Real agents chain multiple tools; one-shot retrieval looks like a chatbot, not an agent.

## Verified facts table

| Fact                                                | Value                                                                | Source                                               |
| --------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| Trial length                                        | 14 days, Elastic Cloud                                               | elastic.co/cloud/cloud-trial-overview                |
| Trial extension                                     | NOT available for SaaS trial                                         | partner brief + elastic.co                           |
| Trial signup path that grants free trial            | https://cloud.elastic.co (NOT Azure/GCP marketplace)                 | elastic.co/cloud/cloud-trial-overview                |
| Recommended MCP server                              | Elastic Agent Builder MCP endpoint (in Kibana)                       | rapid-agent.devpost.com/details/elastic-resources    |
| Deprecated MCP server                               | `docker.elastic.co/mcp/elasticsearch` (security updates only)        | github.com/elastic/mcp-server-elasticsearch          |
| Minimum Elasticsearch version for Agent Builder MCP | 9.2+                                                                 | elastic.co/docs/solutions/search/mcp                 |
| Agent Builder status                                | GA (general availability)                                            | elastic.co/search-labs/blog/agent-builder-elastic-ga |
| SDK languages                                       | Python, JS/TS, Java, Go, Rust, .NET (official Elasticsearch clients) | github.com/elastic/elasticsearch-py                  |
| Required surface                                    | Vector / semantic search + ES                                        | QL tools via Agent Builder                           | rapid-agent.devpost.com/details/elastic-resources |
| Demo video                                          | ≤3 minutes, English, public link (used as backstop if trial expires) | rapid-agent.devpost.com/rules                        |
| Judging period                                      | June 22 – July 6, 2026                                               | rapid-agent.devpost.com/rules                        |

## Opinion: Elastic is the highest-ceiling, highest-risk track for a blockchain solo dev

**Pro:** The "search over private corpus" pattern is the most universally understandable demo. A judge instantly groks "ask any question about my 50k docs, get a sourced answer." High demoability, high judge legibility, broad domain fit.

**Con (the killer):** The 14-day trial is brutal for a 5-week hackathon. If you start the trial early to learn Agent Builder, it dies before you submit. If you start it too late, you're learning Agent Builder + Kibana + ES|QL + semantic_text under deadline pressure. The new-email-+-reindex workaround works but adds operational risk.

**Con (subtler):** Elastic's surface is wide and a blockchain dev has zero exposure to ES|QL, Kibana tool definitions, or semantic_text. Compared to Arize (just instrument and eval) or Fivetran (just connect a source), Elastic has the steepest learning curve.

**Verdict for a blockchain-native solo dev:** Skip Elastic unless you have a _specific_ idea where hybrid search is irreplaceable. If you do pick it, your day-1 priority is: open the trial as late as possible (~May 28), index a private corpus immediately, define 3-5 Agent Builder tools, wire ADK + Cloud Run, then iterate.

## Sources

- Hackathon overview: https://rapid-agent.devpost.com/
- Hackathon rules: https://rapid-agent.devpost.com/rules
- Elastic partner page: https://rapid-agent.devpost.com/details/elastic-resources
- Elastic Cloud trial: https://www.elastic.co/cloud/cloud-trial-overview
- Elastic MCP docs: https://www.elastic.co/docs/solutions/search/mcp
- Elastic deprecated MCP server: https://github.com/elastic/mcp-server-elasticsearch
- Agent Builder GA blog: https://www.elastic.co/search-labs/blog/agent-builder-elastic-ga
- MCP for intelligent search (hybrid pattern): https://www.elastic.co/search-labs/blog/mcp-intelligent-search
- How to build an MCP server with Elastic: https://www.elastic.co/search-labs/blog/how-to-build-mcp-server
- Prior Elastic hackathon recap (PHAROS, Gauntlet, Duplicate Detection): https://www.elastic.co/blog/the-elasticsearch-agent-builder-hackathon
- Elasticsearch-py: https://github.com/elastic/elasticsearch-py
