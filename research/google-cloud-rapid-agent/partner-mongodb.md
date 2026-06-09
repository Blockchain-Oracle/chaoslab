# Partner: MongoDB — Rapid Agent Hackathon Track

> **Prize:** 1st $5K / 2nd $3K / 3rd $2K (per partner bucket).
> **Deadline:** June 11, 2026.
> **Stack required:** Code orchestrator = Google Cloud Agent Builder / ADK / Agent Runtime / Cloud Run. Agent must integrate MongoDB's official MCP server.

---

## What the product actually is

MongoDB is a document database. You store JSON-shaped documents (technically BSON) in collections, query them with a JSON-shaped query language (`find`, `$match`, `$group` aggregation pipelines), and you don't have to declare a schema up front. For a blockchain-native dev: think of it as "the EVM event log, but persistent, queryable, and indexable" — flexible schema, document-shaped, designed for fast reads of nested data.

MongoDB Atlas is the managed cloud version. It runs on AWS, GCP, and Azure. You spin up a cluster (free tier exists — M0 shared, 512MB storage, no time limit [UNVERIFIED — verify current limits in Atlas console]), get a connection string, and you're querying. On top of the database, Atlas bundles **Atlas Search** (BM25 full-text search via Lucene under the hood) and **Atlas Vector Search** ($vectorSearch aggregation stage backed by HNSW indexes). The whole AI-pivot for MongoDB hinges on the line: _one database, document + full-text + vector, no separate vector DB needed_.

For this hackathon, MongoDB is the easiest partner if you understand vector embeddings. The MCP server is the most mature of the three (40+ tools), the docs are best-in-class, and there's a dedicated Gemini CLI extension (`mongodb-partners/mongodb-gemini-extension`) that wraps the MCP server specifically for Gemini-driven agents.

## Core product surface

The 3-5 things MongoDB is genuinely best at:

1. **Flexible-schema document storage.** No migrations. Add a field, write it. Query nested arrays and objects natively without joins.
2. **Aggregation pipelines.** `$match` → `$lookup` → `$group` → `$project` is incredibly expressive. The `aggregate` MCP tool exposes the entire pipeline.
3. **Atlas Vector Search.** `$vectorSearch` is now a first-class aggregation stage. With the Winter 2026 MCP update, you can `insert-many` with auto-embedding (Voyage AI under the hood) and `aggregate` with `$vectorSearch` from the same tool — no separate Pinecone / Weaviate stack.
4. **Atlas Search.** Lucene-powered BM25 + faceting + autocomplete in the same database.
5. **Atlas Stream Processing.** Kafka-connected real-time pipelines, surfaced via four MCP tools (`atlas-streams-discover/build/manage/teardown`). Useful if your agent needs to react to live events.

## Their MCP server

**Name:** MongoDB MCP Server (official, maintained by `mongodb-js`).
**Repo:** [https://github.com/mongodb-js/mongodb-mcp-server](https://github.com/mongodb-js/mongodb-mcp-server)
**Package:** `mongodb-mcp-server` on npm. License Apache-2.0.
**Docs:** [https://www.mongodb.com/docs/mcp-server/tools/](https://www.mongodb.com/docs/mcp-server/tools/)
**Status:** GA, actively maintained (Winter 2026 release added auto-embedding + vector index support).

**Install (canonical):**

```bash
npx -y mongodb-mcp-server@latest --readOnly
```

With env vars for both database connection and Atlas API:

```bash
export MDB_MCP_CONNECTION_STRING="mongodb+srv://user:pass@cluster.mongodb.net/db"
export MDB_MCP_API_CLIENT_ID="<atlas-service-account-public-key>"
export MDB_MCP_API_CLIENT_SECRET="<atlas-service-account-private-key>"
npx -y mongodb-mcp-server@latest
```

**Gemini CLI extension (recommended for this hackathon):**

```bash
gemini extensions install https://github.com/mongodb-partners/mongodb-gemini-extension.git
```

This wraps the same `mongodb-mcp-server` package but ships pre-configured for Gemini CLI users with automatic upstream updates. README: [https://github.com/mongodb-partners/mongodb-gemini-extension](https://github.com/mongodb-partners/mongodb-gemini-extension).

### Exposed MCP tools (40+, grouped)

Verified from [https://www.mongodb.com/docs/mcp-server/tools/](https://www.mongodb.com/docs/mcp-server/tools/):

**Atlas Cluster Management**

- `atlas-list-orgs`, `atlas-list-projects`, `atlas-create-project`
- `atlas-list-clusters`, `atlas-inspect-cluster`
- `atlas-create-free-cluster` — spins up an M0 free cluster in code
- `atlas-connect-cluster` — temporary 4-hour DB user via service account
- `atlas-upgrade-cluster` (Free→Flex, Free→M10, Flex→M10)

**Atlas Security & Access**

- `atlas-inspect-access-list`, `atlas-create-access-list`
- `atlas-list-db-users`, `atlas-create-db-user`
- `atlas-list-alerts`

**Database Operations** (core CRUD + query)

- `connect`, `switch-connection`
- `find`, `aggregate`, `count`, `explain`
- `insert-many` (supports auto-embedding with Voyage AI key)
- `update-one`, `update-many`, `delete-many`

**Collection Management**

- `create-collection`, `rename-collection`, `drop-collection`, `list-collections`
- `collection-schema`, `collection-storage-size`, `collection-indexes`

**Index Management**

- `create-index` (handles both traditional AND vector search indexes — same tool)
- `drop-index`

**Database Admin**

- `list-databases`, `drop-database`, `db-stats`, `mongodb-logs`, `export`

**Vector Search** (key for this hackathon)

- `create-index` with vector config
- `insert-many` with auto-embedding (Voyage AI: `voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`, `voyage-code-3`)
- `aggregate` with `$vectorSearch` stage
- `collection-indexes` lists vector indexes

**Local Atlas (Docker)**

- `atlas-local-list-deployments`, `atlas-local-create-deployment`, `atlas-local-connect-deployment`, `atlas-local-delete-deployment`

**Atlas Stream Processing**

- `atlas-streams-discover`, `atlas-streams-build`, `atlas-streams-manage`, `atlas-streams-teardown`

**Performance Advisor** (M10+ required)

- `atlas-get-performance-advisor` — slow queries, index suggestions, schema advice

**Assistant / Knowledge**

- `list-knowledge-sources`, `search-knowledge` — query MongoDB's knowledge base directly

That's the broadest MCP surface area of all three hackathon partners.

## Free tier / trial details + gotchas

Per the hackathon brief (verified against Abu's intake):

- **Atlas free tier (M0)** works for the hackathon. Limited storage (~512MB) and shared CPU [UNVERIFIED — confirm current limit in Atlas console at signup]. No time-bound expiry — M0 is free-forever.
- **MongoDB Gemini CLI extension is FREE.** It's just a thin wrapper around the open-source `mongodb-mcp-server` package. Apache-2.0.
- **Sign up for Atlas via Google Cloud Marketplace** so any hackathon GCP credits flow cleanly. This is the official path; signing up directly on mongodb.com creates a separate billing relationship.
- **Voyage AI key required for auto-embedding.** Voyage AI has its own free tier (separate API key). If you don't use Voyage, you can still do vector search by generating embeddings yourself (e.g., via Vertex AI's `text-embedding-005`) and inserting them as a plain float array — `$vectorSearch` doesn't care who generated them.

**Other gotchas:**

- M0 free tier does NOT support Performance Advisor (requires M10+). Don't plan a demo around `atlas-get-performance-advisor` unless you upgrade.
- M0 has a hard connection limit (~500 concurrent connections). For a demo it's fine; for a real product, plan for Flex/M10.
- `atlas-connect-cluster` creates a _temporary_ DB user with 4-hour expiry — fine for a one-shot demo, but if your agent runs longer you need a long-lived user.
- Read-only mode (`--readOnly` flag) blocks writes — useful for safety during dev, but turn off before recording demo if your agent needs to write.
- Local Atlas deployments via `atlas-local-create-deployment` require Docker AND read-only mode disabled. For demo purposes, just use cloud M0.

## What problems MongoDB is set up to solve well

The natural-fit problem shapes:

1. **RAG (Retrieval-Augmented Generation) where you need flexible schema.** Document store + vector search + BM25 in one query is the whole pitch. If your idea involves "give me docs semantically similar to X _and_ filter by metadata Y _and_ full-text-match Z" — MongoDB wins.
2. **Agents that need to ingest, store, and query their own state.** Conversation history, tool call logs, intermediate reasoning — all naturally document-shaped. `insert-many` + `find` + `$vectorSearch` over agent memory.
3. **Real-time data + agent reactions.** Atlas Stream Processing can pipe Kafka events into MongoDB, and your agent's `aggregate` queries can detect anomalies. Live ops.
4. **Anywhere "polyglot persistence" was the old answer** (Postgres for relational + Elasticsearch for search + Pinecone for vectors). MongoDB collapses all three.

MongoDB is _not_ set up well for: hard relational workloads with deep joins (use Postgres), graph-shaped data (use Neo4j), or anything where ACID across multiple aggregates is the core requirement.

## Concrete agent ideas

Six ideas. Each: problem statement → why MongoDB → tools the agent calls → judging fit.

### 1. World Cup 2026 Match Intelligence Agent (Devpost domain)

**Problem:** "Fan wants to ask 'show me all matches where Argentina conceded a goal in the first 15 minutes and Messi played' in natural language."
**Why MongoDB:** Match events are document-shaped (nested arrays of goals, cards, substitutions). `$vectorSearch` over commentary text + structured `$match` over event metadata in the same aggregation pipeline.
**Tools:** `insert-many` (with auto-embedding on commentary), `create-index` (vector), `aggregate` ($vectorSearch + $match + $lookup).
**Judging fit:** Hits Devpost World Cup example head-on. Strong on Idea Quality and Technological Implementation.

### 2. Financial Services Document RAG Agent (Devpost domain)

**Problem:** "Compliance analyst needs to query 10K filings, earnings transcripts, and regulatory notices semantically with metadata filters (sector, date, ticker)."
**Why MongoDB:** Documents have wildly different schemas (10K vs earnings call vs RegNotice). Vector search on body + structured metadata filter in one `aggregate` call.
**Tools:** `insert-many` (auto-embed), `create-index` (vector + text), `aggregate` ($vectorSearch + $match), `search-knowledge`.
**Judging fit:** Devpost FinServ domain. Strong on Potential Impact.

### 3. Brick-and-Mortar Retail Inventory Whisperer (Devpost domain)

**Problem:** "Store manager asks 'which products in my back-of-house are similar to the trending TikTok item and have >20 units?' — needs semantic product match + stock filter."
**Why MongoDB:** Product catalog with embeddings on description, store-level stock as nested doc. Single aggregation does similarity search + stock threshold + store filter.
**Tools:** `insert-many` (products with auto-embedding), `aggregate` ($vectorSearch + $match on stock), `collection-indexes`.
**Judging fit:** Devpost retail domain. Strong on Idea Quality + Design (real customer-facing UX).

### 4. Multi-Modal Customer Support Triage

**Problem:** "Support tickets arrive as text + screenshots + sometimes voice. Route to the right team based on semantic similarity to past resolved tickets."
**Why MongoDB:** Store tickets with embeddings, transcripts, image URLs in one document. `$vectorSearch` on the embedding, `$match` on priority/team.
**Tools:** `insert-many`, `aggregate` ($vectorSearch), `create-workitem`-equivalent via `update-many` to mark routed, `find` on resolved similar.
**Judging fit:** Solid on Potential Impact. Differentiate via multi-modal handling.

### 5. Agentic Code Knowledge Base (dev-tools angle)

**Problem:** "Solo dev wants 'how did I solve X in any of my past 50 projects?' Answer requires semantic search across git history + comments + READMEs."
**Why MongoDB:** Ingest commit messages + diffs + READMEs as documents, embed with `voyage-code-3`, vector search.
**Tools:** `insert-many` (with `voyage-code-3` embedding), `create-index`, `aggregate` ($vectorSearch).
**Judging fit:** Medium on Idea Quality (has been done) but strong implementation surface.

### 6. Live Anomaly Detector with Stream Processing

**Problem:** "Fraud team needs an agent that watches real-time transactions, flags anomalies semantically similar to past fraud patterns, opens a case."
**Why MongoDB:** Atlas Stream Processing pipes Kafka transactions in. Agent runs periodic `$vectorSearch` against known-fraud embeddings + threshold check.
**Tools:** `atlas-streams-build`, `atlas-streams-manage`, `aggregate` ($vectorSearch + $match), `insert-many` (open case as doc).
**Judging fit:** Strong on Technological Implementation (Stream Processing is a flex). Risk: requires more setup than a 3-min demo can show clean.

## Track-specific judging risks

What kills a MongoDB submission:

1. **Using Atlas as a dumb K/V store with no vector search.** The brief is explicit: judges look for "why MongoDB specifically." If your agent just does `find` + `insert-many` and the demo is "look, I'm storing JSON" — you've used 5% of the surface and signaled you don't understand the product. **Use `$vectorSearch` at minimum.**
2. **Generating embeddings outside the MCP server when you didn't need to.** The Winter 2026 release added auto-embedding via Voyage AI specifically to make this clean. If you're embedding via Vertex AI and stuffing arrays manually, fine — but show why. Default to MongoDB-managed embeddings.
3. **No real corpus.** A demo with 5 documents is a smoke test, not a vector search story. Load at least a few thousand documents for the demo (use a public dataset — Wikipedia chunks, SEC filings, product reviews).
4. **Forgetting the orchestrator requirement.** Even if MongoDB is the star, the agent must be built on Agent Builder / ADK / Agent Runtime / Cloud Run. Deploy your ADK agent to Cloud Run; show it in the demo.
5. **Hardcoded credentials in the demo video.** Atlas connection strings contain passwords. Don't show them on camera. Use env vars and a `.env.example`.

## Verified facts table

| Fact                   | Value                                                                 | Source                                               |
| ---------------------- | --------------------------------------------------------------------- | ---------------------------------------------------- |
| Prize bucket           | $5K / $3K / $2K                                                       | rapid-agent.devpost.com                              |
| Required orchestrator  | Google Cloud Agent Builder / ADK / Agent Runtime / Cloud Run          | hackathon brief                                      |
| Demo video length      | ~3 minutes                                                            | rapid-agent.devpost.com                              |
| MCP server name        | MongoDB MCP Server (`mongodb-mcp-server`)                             | github.com/mongodb-js/mongodb-mcp-server             |
| MCP server status      | GA, Winter 2026 release                                               | mongodb.com/company/blog                             |
| Install command        | `npx -y mongodb-mcp-server@latest`                                    | mongodb.com/docs/mcp-server                          |
| Number of tools        | 40+ across 7 categories                                               | mongodb.com/docs/mcp-server/tools                    |
| Vector search support  | Full ($vectorSearch + auto-embedding)                                 | mongodb.com/company/blog (Winter 2026)               |
| Embedding models       | Voyage AI: voyage-3-large, voyage-3.5, voyage-3.5-lite, voyage-code-3 | mongodb.com/docs/mcp-server/tools                    |
| Free tier              | M0 shared cluster, 512MB [UNVERIFIED current limit]                   | mongodb.com/pricing                                  |
| Gemini CLI extension   | FREE, wraps mongodb-mcp-server                                        | github.com/mongodb-partners/mongodb-gemini-extension |
| GCP Marketplace signup | Recommended for hackathon credit hygiene                              | hackathon brief                                      |
| License                | Apache-2.0                                                            | github.com/mongodb-js/mongodb-mcp-server             |
| Performance Advisor    | M10+ required (NOT on free tier)                                      | mongodb.com/docs/mcp-server/tools                    |
| Stream Processing      | Available (4 MCP tools)                                               | mongodb.com/docs/mcp-server/tools                    |

## Opinionated take for Abu

**MongoDB is the lowest-friction track for a blockchain-native solo dev.** Three reasons:

1. **You already grok document stores.** EVM logs, transaction receipts, JSON-RPC responses — your mental model maps directly onto BSON. No new abstraction.
2. **Vector search collapses the stack.** No separate vector DB to provision, no embedding pipeline to wire up. `insert-many` with auto-embed + `$vectorSearch` aggregation is a 30-line implementation.
3. **The MCP surface is the most mature of the three partners.** 40+ tools, GA status, well-documented. Less time fighting the platform, more time on the agent idea.

**Biggest leverage:** Pick a Devpost example domain (World Cup, FinServ, Retail), build a real RAG agent with a real corpus (a few thousand docs minimum), and make `$vectorSearch` the demo's centerpiece. The Match Intelligence Agent (#1) and Retail Inventory Whisperer (#3) are both visually compelling for a 3-minute demo video.

**Skip:** The plain CRUD ideas. Anyone can `find`. Win on vector search.

## Sources

- [MongoDB MCP Server tools reference](https://www.mongodb.com/docs/mcp-server/tools/)
- [mongodb-js/mongodb-mcp-server GitHub](https://github.com/mongodb-js/mongodb-mcp-server)
- [What's New in the MongoDB MCP Server: Winter 2026 Edition](https://www.mongodb.com/company/blog/product-release-announcements/whats-new-mongodb-mcp-server-winter-2026-edition)
- [mongodb-partners/mongodb-gemini-extension](https://github.com/mongodb-partners/mongodb-gemini-extension)
- [MongoDB Atlas Vector Search](https://www.mongodb.com/products/platform/atlas-vector-search)
- [Rapid Agent Hackathon home](https://rapid-agent.devpost.com/)
- [Google ADK docs](https://google.github.io/adk-docs/)
- [Deploy ADK agent to Cloud Run](https://docs.cloud.google.com/run/docs/ai/build-and-deploy-ai-agents/deploy-adk-agent)
- [MongoDB Smart Shopping Cart Medium tutorial (Gemini + Vector Search + MCP)](https://medium.com/mongodb/the-smart-shopping-cart-ai-agents-with-gemini-mongodb-atlas-vector-search-and-the-mcp-toolbox-7667b9e9805c)

## Devpost-listed resources (audit 2026-06-03)

The Devpost MongoDB resources tab lists 9 specific URLs. Coverage check + fill-in:

| Devpost-listed resource                                                | Status                          |
| ---------------------------------------------------------------------- | ------------------------------- |
| sample_mflix sample dataset (with `embedded_movies` vector collection) | ❌ missing — add below          |
| Data Modeling docs                                                     | ❌ missing — add below          |
| MongoDB MCP Server get-started                                         | ✅ covered (in body)            |
| MongoDB Database Tools                                                 | ❌ missing — add below          |
| MongoDB Aggregations                                                   | ❌ missing — add below          |
| MongoDB Atlas Search                                                   | ⚠ named in body; URL not pinned |
| MongoDB Atlas Vector Search                                            | ✅ covered                      |
| MongoDB AI Learning Hub (use-cases/artificial-intelligence)            | ❌ missing — add below          |
| AI Search & Retrieval product page                                     | ❌ missing — add below          |

### Amendments

- **`sample_mflix.embedded_movies`** — https://www.mongodb.com/docs/atlas/sample-data/sample-mflix — **Critical for demo speed.** `sample_mflix` is Atlas's bundled sample dataset (6 collections: `movies`, `comments`, `theaters`, `users`, `sessions`, `embedded_movies`). The `embedded_movies` collection is a Western/Action/Fantasy subset **pre-enriched with vector embeddings** (1536-dim OpenAI + 2048-dim Voyage AI, stored as binary). **This is the fastest path to a Vector-Search demo** — load sample data in 1 click in Atlas UI, point `$vectorSearch` at the existing `plot_embedding_voyage_3_large` field, query against it. Saves 4-8 hours of embedding pipeline setup. The Devpost brief implicitly endorses this dataset.
- **Data Modeling docs:** https://www.mongodb.com/docs/manual/data-modeling/ — Flexible-schema design patterns: embed vs reference, one-to-one / one-to-many / many-to-many relationships, schema design for access patterns. Useful when designing a custom corpus schema (not using sample_mflix).
- **MongoDB Database Tools:** https://www.mongodb.com/try/download/database-tools — Apache-2.0 CLI tools: `mongodump`/`mongorestore` (backup/restore), `mongoimport`/`mongoexport` (JSON/CSV/TSV import-export), plus admin utilities. Linux/macOS/Windows. **Use `mongoimport` to seed a custom corpus from CSV/JSON** if not using sample_mflix.
- **Aggregation Pipelines:** https://www.mongodb.com/docs/manual/aggregation/ — Multi-stage pipeline reference. `$match → $group → $sort → $limit` and the rest. Single-purpose methods (`count()`, `distinct()`) as the simpler alternative. **`$vectorSearch` is itself a pipeline stage** — to combine semantic + filter + group you write a single aggregate, not three queries. Master `$lookup` (joins) too.
- **Atlas Search (BM25 full-text):** https://www.mongodb.com/docs/atlas/atlas-search/ — Lucene-backed BM25 full-text search. Separate from Vector Search but composable in one aggregate (`$search` stage for BM25, `$vectorSearch` stage for semantic, then fuse via `$unionWith` + `$group`). **Hybrid search story is what distinguishes a great MongoDB submission from a basic vector-only one.**
- **AI Learning Hub:** https://www.mongodb.com/resources/use-cases/artificial-intelligence — Self-paced tracks for building AI apps with MongoDB. Includes vector-DB primer, RAG application guide, skill badges, notebooks with OpenAI + Voyage AI embeddings. **Skim for the RAG notebook patterns specifically** — they map directly onto Devpost World-Cup / FinServ / Retail idea shapes.
- **AI Search & Retrieval product page:** https://www.mongodb.com/products/platform/ai-search-and-retrieval — Marketing page that frames the combined BM25 + vector + filter story as one "search & retrieval" surface. Useful as Devpost write-up framing language ("MongoDB unified search and retrieval" sounds stronger than "I used Vector Search").
- **Voyage AI documentation** — referenced in Devpost; closest URL is the Voyage AI section of the MongoDB Vector Search docs. Embedding model identifiers (`voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`, `voyage-code-3`) are already listed in our body table.

Coverage status: **all 9 Devpost-listed MongoDB resources now covered.**
