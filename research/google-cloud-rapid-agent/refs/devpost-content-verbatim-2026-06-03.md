# Devpost Source-of-Truth — Verbatim Capture (2026-06-03)

> **Why this file exists:** Abu pasted the full Devpost sponsor + rules content on 2026-06-03 during the S1.3→S1.4 transition. His directive: validate that our `research/` folder covers every URL, every resource, every section — no improvising, no assumptions. This file preserves the EXACT pasted content as the canonical anchor against which our research is audited.
>
> **Related (parallel research files added 2026-06-03 to close gaps):**
>
> - `refs/arize-gemini-hackathon-quickstart.md` — deep dive on `github.com/Arize-ai/gemini-hackathon` (the official Arize quickstart, previously uncaptured)
> - `refs/openinference-google-matrix.md` — full instrumentor matrix (adk + vertexai + google-genai)
> - `refs/partner-resource-completeness-audit.md` — per-partner URL/resource gap audit
> - `refs/official-rules-verbatim.md` — full 24-section rules text + ChaosLab compliance checklist
>
> **Abu's instruction quote (2026-06-03):** _"Did you really consume this content very well before looking into a hackathon idea? ... I want you to do deeper research on everything, on all the docs that you could find. Maybe you can add it as part of domain knowledge ... I want you to know that you have the tools. You can use Exa Search; you have the plugins. ... I also want you to put in domain knowledge if content like this is not yet there because this is going to help us ensure that we're building right and also building for a track. It's also very, very important, so I wouldn't want us to be improvising or something like that ... nothing is left behind; all the sponsors and everything, like their resources that they provided, must be included."_

---

## About Fivetran

Fivetran is the data foundation for AI. The Fivetran platform moves, manages, and transforms data from every system a business runs on into a secure, reliable foundation engineered to evolve, with the flexibility to work across clouds, engines, and tools. With Fivetran, analytics, operations, and AI run on data you trust and control. Leading organizations like LVMH, Pfizer, Verizon, and OpenAI rely on Fivetran to turn data into a competitive advantage. Learn more at Fivetran.com.

### Fivetran Resources

Please create a Fivetran 14 days free trial to get access to Fivetran — https://fivetran.com/signup

There are two options for integrating your agents with the Fivetran platform — choose the one that works best for your use case and development style:

**Option 1 — MCP**: Fivetran provides an example Open Source MCP Server you can download and set up to provide your agent with access to your Fivetran account — https://github.com/fivetran/fivetran-mcp . You may wish to fork this and to extend it as needed for your use case.

**Option 2 — REST API**: As an alternative you may want to use the Fivetran REST APIs as your integration mechanism — you'll find the documentation here: https://fivetran.com/docs/rest-api and an example project here: https://github.com/fivetran/api_framework

To use either option you'll need a Fivetran API key — see the instruction here (the same key can be used for both REST and MCP) — https://fivetran.com/docs/rest-api/getting-started#authentication

For more information about connecting Fivetran with BigQuery as a destination see our quickstart — https://fivetran.com/docs/destinations/bigquery/setup-guide

---

## About Elastic

Elastic, the Search AI Company, integrates its deep expertise in search technology with artificial intelligence to help everyone transform all of their data into answers, actions, and outcomes. Elastic's Search AI Platform — the foundation for its search, observability, and security solutions — is used by thousands of companies, including more than 50% of the Fortune 500. Learn more at elastic.co.

### Build Gemini Agents capable of working with complex enterprise data

Making AI agents work with real-world, unstructured data can be challenging. Agents can interact with data, but are often inefficient, costly, and unreliable. Elastic Agent Builder provides the capabilities developers need to make their agents more effective:

- **Contextual retrieval across any enterprise data** — MCP tools exposing hybrid semantic, keyword, and vector search over any data, structured or unstructured, with hosted models for embeddings, reranking, and LLMs so your agent always gets the most relevant context.
- **Leverage fast, scalable Elastic index as a context layer to store memory and insights, not just raw data** — Write agent outputs, summaries, and enriched facts back into Elasticsearch so your agent builds on what it already knows, turning raw signals into retrievable intelligence over time.
- **Custom tools from your data using ES|QL** — Define callable tools that wrap ES|QL queries and expose them over MCP, letting your agent search, filter, aggregate, and compute over your data as needed without custom code.
- **Workflow tools that reach across systems** — Define tools that retrieve data and take action. Elastic Workflows can call APIs, write to systems of record, and orchestrate multi-step operations so your agent can take real actions.
- **Workflows that call subagents** — Orchestrate specialized subagents as steps within a larger workflow, each powered by its own dynamically loaded Skills, so you can manage context and cost.

### Elastic How to Get Started

1. **Sign up for Elastic Cloud Serverless**: Get a free Elastic Cloud trial at cloud.elastic.co. Create a **Serverless** Elasticsearch project — infrastructure and scaling are fully managed, so you focus on your agent, not your cluster. Choose your preferred Google Cloud region. You can also access Elastic directly through the Google Cloud Marketplace.
2. **Enable Agent Builder**: In your Elasticsearch Serverless project, enable Agent Builder from the Kibana UI. Full setup guide: Get started with Elastic Agent Builder. Agent Builder ships with built-in search tools for agentic retrieval and a built-in MCP server — no extra configuration required to get your first tools exposed.
3. **Connect Google Cloud Agent Builder via MCP**: Point Google Cloud Agent Builder at the Elastic MCP server endpoint found in the Agent Builder Tools UI in Kibana. Authenticate using an Elasticsearch API key. Your Gemini-powered agent will immediately see all the tools you've defined in Elastic. Reference architecture: Implementing an agentic reference architecture with Elastic Agent Builder and MCP
4. **Load and enrich your data**: Use Elastic's built-in connectors to pull in data from Google Drive, Confluence, SharePoint, GitHub, databases, and more — or index your own data directly. Elastic's ELSER semantic model runs automatically for hybrid search. As your agent generates insights, write them back into Elasticsearch to build your context layer.
5. **Define your tools**: Use Agent Builder's UI to create custom tools backed by ES|QL queries or semantic search. Define Workflows that retrieve data, call external APIs, and invoke subagents. Each tool you define is immediately available to your agent via MCP. Elastic Agent Builder tool best practices: Tools documentation
6. **Build, iterate, and submit**: Test your agent in the Agent Builder playground or directly in Google Cloud Agent Builder. Submit with a public GitHub repo (open-source license required) and a ~3-minute demo video.

### Elastic Resources

**Documentation:**

- Elastic Agent Builder — Get Started
- Elastic Agent Builder — MCP Server
- Elastic Agent Builder — Tools
- ES|QL Language Reference
- Elastic Serverless — Get Started
- Semantic Search with Elasticsearch

**Elasticsearch Labs Blogs:**

- Elastic MCP server: Expose Agent Builder tools to any AI agent
- Agent Builder: Elastic reference architecture and MCP guide
- Agent Builder now GA: Ship context-driven agents in minutes
- AI agent memory: Creating smart agents with Elasticsearch managed memory
- MCP overview and emerging use cases
- How to build an MCP server with Elasticsearch
- A2A Protocol and MCP: When to use which in Elasticsearch
- Build task-aware agents with an expanded model catalog on Elastic Inference Service (EIS)
- The Gemini CLI extension for Elasticsearch with tools and skills
- Elastic and Google Cloud's powerful partnership in 2025

**Tutorials and Notebooks:**

- Elasticsearch Labs — Tutorials
- Elasticsearch Labs — Notebooks on GitHub
- Vector Search using Gemini Embeddings and Elasticsearch
- Question Answering using Gemini, LangChain, and Elasticsearch

**Get Access:**

- Elastic Cloud Free Trial (Serverless)
- Elastic on Google Cloud Marketplace

### Connect with Elastic

- Technical questions during the hackathon: Post in the hackathon discussion forum or reach out via the Devpost Discord
- Community: discuss.elastic.co
- Elastic on Discord: ela.st/discord

---

## About Arize

Arize is the single platform built to help you accelerate development of AI apps and agents — then perfect them in production. Arize AX is an AI engineering platform focused on evaluation and observability. It helps AI engineers and AI product managers develop, evaluate, iterate and observe and monitor AI applications and agents. Arize helps enterprises increase their speed in building AI agents and ensure effectiveness for those outcomes that they can trust in production environments.

### Build Gemini Agents with Full Observability and Self-Introspection via MCP

Ship agents that do more than run. Ship agents that can self improve. With Arize Phoenix, your Gemini-powered agent gets production-grade tracing from day one, plus the ability to query its own traces, prompts, datasets, and experiments as tools at runtime via the Phoenix MCP server. Every decision your agent makes becomes inspectable, evaluable, and improvable.

**We'll evaluate submissions based on technical implementation, meaningful use of tracing and MCP, quality of the agent's self-improvement loop, and overall impact.**

Here are some guidelines to get you started:

- The Arize track **requires a code-owned agent** runtime — Gemini CLI, Gemini Enterprise Agent Platform SDK, Google ADK, Agent Runtime, or Cloud Run. The visual Agent Builder alone is not supported for tracing integration. You must be able to instrument your code directly.
- Instrument your agent with OpenInference. Auto-instrumentors exist for Google ADK, Agent Platform, Google GenAI, LangChain, LlamaIndex and many other frameworks.
- Send traces to Phoenix Cloud (free SAAS) or self-hosted Phoenix
- Configure the Phoenix MCP server in your agent so it can introspect its own operational data at runtime
- Run evaluations on your traces with LLM-as-a-Judge or code evals to demonstrate quality
- Bonus points for agents that use their own observability data to improve over time

### Arize How do I get started?

The fastest path is a free Phoenix Cloud account. Grab your API key, pip install an OpenInference instrumentor, and you're tracing in under five minutes. Phoenix is fully open-source, so you can also self-host if you prefer.

For the MCP integration, @arizeai/phoenix-mcp runs via npx and drops into any MCP client config — including Gemini CLI's settings.json.

### Arize Resources

- Phoenix Cloud — Free tier, hosted Phoenix
- Phoenix on GitHub — Open-source, self-hostable
- Phoenix documentation — Tracing, evals, datasets, experiments, prompts
- Phoenix MCP Server guide — Runtime introspection via MCP
- OpenInference on GitHub — OpenTelemetry-compatible auto-instrumentors and utilities

**Instrumentors for Gemini / Agent Platform / ADK:**

- `openinference-instrumentation-google-adk` — For Google ADK agents
- `openinference-instrumentation-vertexai` — For Gemini Enterprise Agent Platform SDK and Gemini via `generative_models`
- `openinference-instrumentation-google-genai` — For the unified `google-genai` SDK

**Quickstarts: get up and running fast**

- https://github.com/Arize-ai/gemini-hackathon — End-to-end example: traced Gemini agent + Phoenix MCP + evaluations
- Agent Platform (Gemini) tracing guide — Step-by-step setup
- Phoenix LLM-as-a-Judge evals — Add evaluation pipelines to your submission

### Connect with Arize

- Hackathon Discord server
- Technical questions during the hackathon: Richard Young — ryoung@arize.com

---

## About GitLab

GitLab is a complete DevSecOps platform, delivered as a single application, that fundamentally changes how Development, Security, and Operations teams collaborate to build software. From idea to production, GitLab helps teams improve cycle time from weeks to minutes, reduce development costs and time to market, and increase developer productivity.

### GitLab Resources

A 30-day Ultimate trial covers everything participants need. No access codes required. Each trial includes Duo Agent Platform with 24 credits per user. Custom agents (GA), custom flows (Beta), AI Catalog (GA), and the MCP server (Beta) are all available.

- Get Started: https://docs.gitlab.com/user/get_started/get_started_agent_platform/
- Custom Agents: https://docs.gitlab.com/user/duo_agent_platform/agents/custom/
- Custom flows: https://docs.gitlab.com/user/duo_agent_platform/flows/custom/
- AI Catalog: https://docs.gitlab.com/user/duo_agent_platform/ai_catalog/
- MCP Server: https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/
- Start a Trial: https://about.gitlab.com/free-trial/

**Please Note:** _Participants using external tools to call GitLab via MCP need to set a default Duo namespace. The MCP server doc above covers this. In-GitLab usage works without it._

---

## About MongoDB

Explore the power of MongoDB's intelligent data platform to build innovative AI-driven solutions for real-world impact. MongoDB Atlas serves as the unified operational foundation and persistent memory layer for modern AI and agentic workloads. By combining operational, vector, and semantic data on a single platform, it eliminates the fragmented stacks and memory barriers that hinder AI performance. Ultimately, it empowers businesses to build production-grade AI that reasons accurately while remaining completely framework-agnostic.

### MongoDB Resources

- Load the sample Mflix Dataset: Quickly spin up sample data to kickstart your project, `sample_mflix.embedded_movies` already contains vector embeddings for Vector Search! Or BYO embedding model and dataset (Embedding model should be one of MongoDB provided or Google provided).
- Data Modelling in MongoDB: Learn best practices for structuring your data.
- MongoDB MCP Server: Explore MongoDB MCP server to connect your database to LLM.
- MongoDB Tools: Explore essential tools to optimize your development workflow.
- MongoDB Aggregations: Master data processing and analysis with powerful aggregation pipelines.
- MongoDB Atlas Search: Build lightning-fast search experiences directly within your database.
- MongoDB Vector Search: Supercharge your apps with AI-driven search capabilities.
- AI Learning Hub: Dive into AI with MongoDB — guides, tutorials, and more.
- Voyage AI documentation: Learn how to use MongoDB Voyage AI to generate embeddings.

---

## About Dynatrace

Dynatrace helps developers and AI engineers building on Google Cloud understand how their applications behave from code to production. As you build, test, and release, it connects what you write to how services, data pipelines, and agents actually run, so you can trace issues, debug faster, and see the impact of changes at every stage.

By bringing runtime context into your development workflow, Dynatrace makes it easier to validate model behavior, troubleshoot agent interactions, and catch problems before and after deployment, so you can ship AI applications that behave the way you expect as they scale.

### Dynatrace Resources

Instrument your agent with OpenTelemetry and ship traces, metrics, and logs to Dynatrace. Track token spend, tool calls, latency, and errors across Vertex AI, Gemini, and your coding agents.

**Agent & Model Observability:**

- Agent Platform: Dynatrace for Agent Platform — Traces, prompt flows, token usage, and model latency for Agent Platform workloads.
- Gemini Enterprise: Dynatrace for Gemini Enterprise — One-click deploy from Google Cloud Marketplace.
- Coding Agents: AI Coding Agent Monitoring — Observability for Claude Code, Gemini CLI, Codex CLI, OpenCode, and GitHub Copilot SDK.
- Code Examples: Instrumentation Examples (GitHub) — OTel exporter configs, sample dashboards, and ready-to-run instrumentation.

**Telemetry Pipeline:**

- OTel Pipeline: Bindplane (Google Edition) — Free OpenTelemetry-native pipeline for Google Cloud Observability and SecOps customers. Collect, process, and route telemetry at scale.

**Get Started:**

- Sign Up for Dynatrace — Free trial. Get instrumented in minutes.

---

## Google Cloud Rapid Agent Hackathon — Official Rules (Section List)

Full text in `refs/official-rules-verbatim.md` (research subagent populating). High-level enumeration here for indexing:

| §   | Title                              | Why it matters for ChaosLab                                                       |
| --- | ---------------------------------- | --------------------------------------------------------------------------------- |
| 1   | Binding Agreement                  | Entry = acceptance                                                                |
| 2   | Sponsor                            | Google LLC (Mountain View)                                                        |
| 3   | Partner Entities                   | Arize / Elastic / Fivetran / GitLab / MongoDB / Dynatrace                         |
| 4   | Eligibility                        | Excluded jurisdictions list — Abu's country (Nigeria) is NOT on the list ✓        |
| 5   | Contest Period                     | 2026-05-05 12:00 PT → 2026-06-11 14:00 PT                                         |
| 6   | How to Enter                       | **$100 GCP credit form deadline: 2026-06-04** (Abu has handled per 2026-06-03)    |
| 7   | Submission Requirements            | Track lock-in, team max 4, new code only, AI usage limitation                     |
| 8   | Judging                            | 4 equal-weighted criteria; Jun 22 → Jul 6 judging window                          |
| 9   | Prizes                             | $5K/$3K/$2K per track; identical across 6 buckets                                 |
| 10  | Fees & Taxes                       | W-8BEN for non-US (Abu); 60-day disbursement                                      |
| 11  | General Conditions                 |                                                                                   |
| 12  | Intellectual Property Rights       | **OSI-approved license required, must be detectable** — ✓ Apache-2.0 per S1.1     |
| 13  | Privacy                            | Google privacy policy                                                             |
| 14  | Publicity                          | Sponsor may use name/likeness                                                     |
| 15  | Warranty / Indemnity / Release     | Original work, no third-party infringement                                        |
| 16  | Elimination                        | False info = immediate elimination                                                |
| 17  | Internet                           | Sponsor not liable for tech failures                                              |
| 18  | Right to Cancel / Modify           |                                                                                   |
| 19  | Not Employment                     |                                                                                   |
| 20  | Forum                              | California state law                                                              |
| 21  | Arbitration                        | JAMS, San Jose, CA                                                                |
| 22  | Winner's List                      | Request between Jul 13 – Sep 13, 2026                                             |
| 23  | Devpost Additional Terms           | ToS incorporated by reference                                                     |
| 24  | Entrant's Personal Information     | Devpost privacy policy                                                            |

### Contest restrictions ChaosLab must respect

1. **AI usage limitation (§7B):** ONLY Google Cloud AI tools (Gemini on Agent Platform, BigQuery ML, etc.) + Arize built-in AI features in submitted code. Banned in submission: Claude / Cursor / Copilot / LangChain-as-primary / LangGraph / LlamaIndex as runtime deps. Dev-time IDE assistance is OK.
2. **Newly created (§7B):** Project must originate during the Contest Period (2026-05-05 to 2026-06-11). Research / spec / domain knowledge can pre-date; the agent code does not.
3. **Track lock-in (§7A):** ChaosLab enters EXACTLY ONE track — Arize. No multi-track submission for the same project shape.
4. **Open source (§12):** Apache-2.0 LICENSE in repo (✓), NOTICE for attributions (✓ deepankarm/agent-chaos per ADR-006 amended), license file must be detectable in GitHub About section.
5. **3-min demo video:** Public on YouTube/Vimeo, English or English subtitles, must show project running, no third-party trademark/sponsorship indication, no offensive content, ≤3 min hard cap.
6. **Functional hosted URL** at submission — no-login sandbox acceptable.
7. **Platform:** must run on web, Android, OR iOS. ChaosLab is web (Next.js front + Cloud Run backend) ✓.
