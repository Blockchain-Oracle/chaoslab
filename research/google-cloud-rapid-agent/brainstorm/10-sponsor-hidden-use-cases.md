# 10 — Sponsor "Hidden" Use Cases (high-leverage hackathon ideas the sponsors hint at but nobody has built yet)

> **Built:** 2026-06-03. **Method:** WebSearch + WebFetch against each sponsor's official docs / search-labs / blogs / GitHub READMEs + judge-employee LinkedIn / Twitter / podcast triangulation. Cross-checked absence by searching DevPost galleries, GitHub repo search, and community forums for the specific use-case shape.
>
> **Output shape:** 3-5 hidden use cases per sponsor (18+ total). Each item has: capability → verbatim hint → source URL → why nobody's built it → judging fit → 3-min demo arc → build surface.
>
> **What "hidden" means:** the sponsor product can do X, the sponsor has published a doc/blog post that hints at X, and a deliberate search of GitHub + DevPost + community forums turns up no built example of X. The closer the use case is to the sponsor's own published vision (not a random arbitrary mashup), the more likely the partner judges score it favorably — because the judges _wrote those hints_.

---

## TL;DR — top 3 hidden use cases overall

| Rank | ID                  | Why it ranks #1                                                                                                                                                                                                                                                                                        |
| ---- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 🥇   | HIDDEN-arize-01     | "Closed-loop ground-truth labeling agent" — combines every Phoenix primitive (datasets + experiments + judge + annotations + prompt registry + MCP) into the one loop Arize publishes a blog about every quarter but ships no end-to-end demo agent for. Track-fit perfect.                            |
| 🥈   | HIDDEN-gitlab-01    | "Team-velocity DORA coach" — uses semantic_code_search + manage_pipeline + MR diffs + the Knowledge Graph to give a team an in-line coach on cycle time, deploy frequency, and review latency. GitLab measures DORA, never built a coach agent. Judges live in this metric.                            |
| 🥉   | HIDDEN-dynatrace-01 | "AI-Coding-Agent Budget Guardrail" — Dynatrace literally shipped the OTel monitoring for Claude Code / Gemini CLI / Codex CLI, hinted at FinOps/guardrails in the launch blog, but no community has built the _guardrail agent_ that watches the OTel stream and pre-emptively kills runaway sessions. |

**Strongest "underused-by-community" sponsor signal: Arize.** Their own blog (turingpost.com guest post, Prompt Learning cookbook) explicitly describes the self-improving closed loop, ships the GitHub starter repo (`Arize-ai/gemini-hackathon`), publishes a Gemini CLI extension wrapping `@arizeai/phoenix-mcp` — yet there is **no shipped, vendor-neutral, end-to-end closed-loop agent in the DevPost galleries** for this hackathon family. The track-side of the hackathon (Arize judges + Phoenix MCP) is the most explicit "we WILL bonus the self-improvement loop" call any of the 6 partners makes (verbatim, partner-arize.md citing rapid-agent.devpost.com/details/arize-resources). That's a hackathon judge openly broadcasting what they want to see.

---

# 1. Arize (Phoenix)

**Judge panel:** Richard Young (Dir. Partner Solutions) — author of AWS Bedrock AgentCore Observability blog; LinkedIn quote "AI without observability is like launching a rocket without telemetry". Clay Miner (Head of Solutions Strategy). Both have published on closed-loop agent eval; their bias is toward submissions that _prove_ the eval loop closes, not just instrument-and-dashboard.

**Hint-density check:** Highest of any sponsor. The Arize partner-resources Devpost page literally says "agents that use their own observability data to improve over time get bonus consideration."

---

### HIDDEN-arize-01: Closed-loop ground-truth labeling agent (the keystone idea)

- **Sponsor capability:** Datasets + Experiments + LLM-as-judge + annotation API + prompt registry — combined via `@arizeai/phoenix-mcp`.
- **What the sponsor hints at:** _"Generate or manually create an initial set of test cases, with ground truth output labels → Use DSPy to create an optimized prompt → Save that prompt in Phoenix → Run the agent in production, capturing tracing → Use LLM evals to label traces at scale → (Optionally) Verify these traces with a human labeler → Add the new traces along with their labels to the training dataset. Return to step 2."_ — verbatim from the Turing Post guest article.
- **Source:** [Guest Post: Building a Self-Improving Agent with Arize Phoenix and DSPy — Turing Post, 2026](https://www.turingpost.com/p/arize1) + the Devpost partner brief quote ("self-improvement loop = bonus consideration") at [rapid-agent.devpost.com/details/arize-resources](https://rapid-agent.devpost.com/details/arize-resources).
- **Why nobody's built it:** The Turing Post article is a _narrative_ description of the loop. The Phoenix Prompt Learning cookbook ([arize.com/docs/phoenix/cookbook/prompt-engineering/optimizing-coding-agent-prompts-prompt-learning](https://arize.com/docs/phoenix/cookbook/prompt-engineering/optimizing-coding-agent-prompts-prompt-learning)) implements the _optimizer_ but uses Cline + SWE-Bench Lite — it never closes the loop via MCP, and there is no agent reading back its own annotations live. GitHub search for `phoenix-mcp agent` returns only the `Arize-ai/gemini-hackathon` starter (an empty template), `Arize-ai/text-to-graphql-mcp` (different product), and the `phoenix-mcp` package itself. **No project on DevPost or GitHub combines all five primitives in one closed loop driven by the agent itself via MCP.**
- **Why it'd win the hackathon:** Hits every judging criterion. Tech Impl: 5 primitives in one loop is the deepest possible Phoenix usage. Idea Quality: "agent that grades itself and writes its own training data" is the freshest framing of LLMOps. Potential Impact: anyone running a production agent needs this. Design: the loop is naturally visualizable as a flywheel diagram.
- **Demo arc (3 min):** (1) User runs ADK agent against a domain (retail SKU questions). Phoenix shows live traces. (2) Built-in judge LLM scores ~30% as "wrong"; agent reads back failures via `phoenix-mcp`, generates 5 candidate new prompt variants, runs them as a Phoenix **experiment**, picks the winner by judge score. (3) Agent **writes the failing-but-now-corrected traces as new dataset examples** and tags the new prompt as `production`. Re-run shows accuracy climb from 70 → 91% on a side-by-side panel.
- **What you'd actually have to build:** ADK agent → instrument with `openinference-instrumentation-google-adk` → ADK FunctionTool wrapper around `phoenix.client.AsyncClient()` (per ADR-005 in our own spec — Phoenix MCP is partial for `run_experiment` + `log_span_annotations`, so wrap via the official Python client; this exact wrapping is the technical moat of the submission). Judge LLM = `gemini-3.5-flash`. The loop is a Python coroutine driven by ADK `LoopAgent`.

---

### HIDDEN-arize-02: Multi-judge ensemble + human-in-loop disagreement detector

- **Sponsor capability:** Phoenix annotations API supports `annotator_kind` of `HUMAN`, `LLM`, or `CODE` on the same span (`/v1/span_annotations`).
- **What the sponsor hints at:** _"Mitigation strategies for LLM judge evaluation involve robust prompt and rubric design, bias-detection and flagging, model calibration with domain-specific data, multi-judge or ensemble aggregation, and maintenance of human-in-the-loop for high-stakes outcomes."_ + the Phoenix docs say _"calibrate automated scores against ground truth human judgments so you can trust what your evals are actually measuring."_
- **Source:** [arize.com/llm-as-a-judge](https://arize.com/llm-as-a-judge/) + [arize.com/docs/phoenix/tracing/how-to-tracing/feedback-and-annotations/capture-feedback](https://arize.com/docs/phoenix/tracing/how-to-tracing/feedback-and-annotations/capture-feedback) (annotation API spec).
- **Why nobody's built it:** Phoenix has the _primitive_ (three annotator kinds attachable to one span) but every published example uses a single judge. Search for `"phoenix" multi-judge ensemble github` returns research papers (`Multi-Agent Debate for LLM Judges`, arXiv 2510.12697) — nothing built on Phoenix MCP. Engineering reason: building an "agent that fans out to N judges, detects disagreement, and routes disagreed-on samples to a human queue" requires both ADK orchestration + Phoenix annotation writes + a UI for the human reviewer. Three-axis problem nobody has stitched.
- **Why it'd win the hackathon:** Solves the #1 known failure mode of LLM-as-judge (judge bias) without leaving the Phoenix surface. Potential Impact is huge for any regulated domain. Quality of Idea is fresh — "disagreement is the signal" framing is from very recent (2026) research that isn't in any DevPost gallery yet.
- **Demo arc (3 min):** Three judges (gemini-3.5-flash, gemini-3.5-pro, gemini-3.5-flash with adversarial prompt) score the same agent span. Phoenix records all three as separate annotations. Agent reads `/v1/span_annotations` via MCP, computes pairwise disagreement, and when Cohen's-kappa drops below 0.6, surfaces a human-review queue. Human approves/rejects; result becomes the canonical label, propagated to dataset.
- **What you'd actually have to build:** ADK `ParallelAgent` for the 3 judges → annotation-write wrapper (Python client, since MCP doesn't expose this) → a Cloud Run web UI (Next.js + visx tree of disagreed spans) → human label → backprop to dataset.

---

### HIDDEN-arize-03: Phoenix-driven cost-aware model router

- **Sponsor capability:** Phoenix traces capture token counts + model ID per span; datasets + experiments let you A/B _different models_ against the same prompt+input.
- **What the sponsor hints at:** _"Phoenix's prompt management lets you swap LLMs in seconds and re-run an experiment to see exact cost-vs-quality tradeoff per model."_ Implicit: experiments aren't just for prompt variants, they're for model variants too.
- **Source:** [arize.com/docs/phoenix/prompt-engineering/tutorial](https://arize.com/docs/phoenix/prompt-engineering/tutorial) + the Phoenix Playground feature docs.
- **Why nobody's built it:** GitHub search for `phoenix model routing` / `phoenix cost-aware agent` returns nothing built. The pattern is mentioned only in framing language; the actual _implementation_ of "agent inspects current span cost, queries Phoenix for which model historically nailed this rubric cheapest, routes to that model" is unbuilt. Implementation barrier: requires a stable rubric → model performance mapping, which is exactly what Phoenix experiments produce — but no one has closed the loop _back into the agent's routing logic_.
- **Why it'd win the hackathon:** "FinOps for agents" is the 2026 hot button (Andreessen, Fivetran's readiness index all call it out). Tech Impl is novel — model routing driven by your own historical Phoenix data, not a static rules table. Potential Impact: cuts agent inference cost 60-80% on simple intents.
- **Demo arc (3 min):** Agent receives a query. Pre-call: it queries `phoenix-mcp` for "experiments where rubric=X scored ≥0.9 — sort by cost ascending." Picks `gemini-3.5-flash-lite`. Runs. Span records cost + judge score. After 100 queries, agent autonomously re-balances routing weights based on accumulated Phoenix data.
- **What you'd actually have to build:** ADK `LlmAgent` with a pre-call hook → `phoenix-mcp.list_experiments` filter by rubric → simple cost-vs-quality argmin → model swap (Gemini Flash / Flash-Lite / Pro) per call → tag every span with the routing decision so the data feeds the next iteration.

---

### HIDDEN-arize-04: Prompt-registry-as-feature-flag (agent-driven A/B at runtime)

- **Sponsor capability:** Phoenix prompt registry supports tags (`prod`, `staging`, `latest`) + creation/update of prompt versions via MCP.
- **What the sponsor hints at:** _"Prompts Management: Create, list, update, and iterate on prompts"_ — from the `@arizeai/phoenix-mcp` README. Implicit hint in the Turing Post post: "the prompt becomes a first-class artifact, not a string in code … updated prompts deploy via Phoenix tags."
- **Source:** [github.com/Arize-ai/phoenix/blob/main/js/packages/phoenix-mcp/README.md](https://github.com/Arize-ai/phoenix/blob/main/js/packages/phoenix-mcp/README.md) + [turingpost.com/p/arize1](https://www.turingpost.com/p/arize1).
- **Why nobody's built it:** Built examples treat Phoenix prompts as a version-control mirror. Nobody has built an agent that _routes traffic between prompt versions in real time_ based on per-segment scoring (e.g., "Spanish-language users → prompt-v3 because the eval score on that segment is higher"). The primitive is there; the routing layer + segment-aware annotation aren't combined anywhere.
- **Why it'd win the hackathon:** Mirrors the Optimizely / LaunchDarkly playbook applied to prompts — a category the panel will recognize but hasn't seen _implemented on Phoenix MCP_. Idea Quality bonus.
- **Demo arc (3 min):** Agent receives query. Detects language = `es`. Calls `phoenix-mcp.get_prompt_by_tag(name="customer-support", tag="prod-es")`. Runs with that prompt. After 50 queries per segment, agent reads `list_experiments` filtered by segment, auto-promotes the best-performing prompt for that segment to `prod-es`.
- **What you'd actually have to build:** ADK agent + segment-detection FunctionTool + `phoenix-mcp.get_prompt_by_tag` → run → write span tagged with `segment` + `prompt_version` attribute → background `LoopAgent` reads experiments grouped by segment and updates the tag.

---

### HIDDEN-arize-05: Trace-replay regression suite (the Foundry-fork-tests-for-agents pattern)

- **Sponsor capability:** Phoenix datasets can be _materialized from filtered span queries_ — i.e. "every span tagged `incident=Y` becomes a dataset example."
- **What the sponsor hints at:** _"You can filter traces by annotation values to narrow down to interesting samples and export your selection to a dataset for things like experimentation, fine-tuning, or building a human-aligned eval."_
- **Source:** [arize.com/docs/phoenix/cookbook/annotations/using-human-annotations-for-eval-driven-development](https://arize.com/docs/phoenix/cookbook/annotations/using-human-annotations-for-eval-driven-development).
- **Why nobody's built it:** The "incident replay against new agent version" pattern is standard in EVM tooling (Tenderly forks) but no published Phoenix example demonstrates it. Tooling gap: turning a Phoenix filter query into a _first-class regression test that runs in CI_ requires wiring Phoenix experiments to GitHub Actions + grading the diff between baseline and PR-branch agent runs.
- **Why it'd win the hackathon:** Speaks directly to a Splunk/Akamai SRE-shaped judge (Richard Young's background). Demo is visually striking — "the agent that broke incident #142 in prod, replayed against the new agent, now succeeds."
- **Demo arc (3 min):** Past incident span filtered into a dataset (`high_severity_incidents_2026Q1`). New agent variant pushed. Phoenix `run_experiment` against the dataset, side-by-side diff: baseline 4/10 passed, new variant 9/10. GitHub Action posts the diff to the PR.
- **What you'd actually have to build:** Span-filter UI → "save as dataset" button → ADK agent reimplemented from spec → `phoenix.client.experiments.run_experiment` wrapper (since MCP doesn't expose this — ADR-005 amendment confirmed) → GitHub Actions integration.

---

**Why this sponsor will judge favorably:** Richard Young's career (Splunk → Akamai → WhyLabs → Arize) is _exactly_ the SRE-becomes-LLMOps-engineer arc. Submissions that show "I treated agents like prod systems, with regression tests + canary deploys + on-call replay" will resonate. His Couchbase + AWS Bedrock partner blogs all emphasize _trustworthy production_ over flashy demos. Clay Miner's Solutions Strategy role biases toward submissions that map cleanly to enterprise sales motion — i.e., "this could be sold to a Fortune 500" beats "this is creative but niche." Build for both: HIDDEN-arize-01 (closed loop = trust) + HIDDEN-arize-02 (multi-judge = compliance) are the two highest-judge-fit ideas.

---

# 2. Elastic (Agent Builder)

**Judge panel:** Anish Mathur (Dir. PM) — owner of Agent Builder roadmap. Philipp Krenn (`@xeraa`, Dir. DevRel) — long Twitter history on ELSER, vector search, hybrid retrieval, ESQL; his vision is _"help users be successful by showing them what is possible"_. Heavy DevRel weighting on the panel means demo-craft matters as much as depth.

**Hint density:** Very high in Search Labs blog (2026 has been an Agent-Builder content firehose).

---

### HIDDEN-elastic-01: Code-review agent that uses Elasticsearch as its own memory across PRs

- **Sponsor capability:** Agent Builder Subagents + ELSER `semantic_text` + hybrid search + dedicated `agent-memory` index.
- **What the sponsor hints at:** _"There's still knowledge available in Elasticsearch that you cannot access via standard tools. To access internal knowledge during the planning phase, you can create a Claude Code subagent by making a retrieval agent using Agent Builder."_ AND _"Elasticsearch acts as the data backbone … storing long-term memory (agent-memory index)."_ AND _"ELSER matched the error to the commit 'Removed null safety checks' with zero shared keywords"_ (verbatim, an Elastic skills repo example).
- **Source:** [elastic.co/search-labs/blog/subagents-with-elastic-agent-builder](https://www.elastic.co/search-labs/blog/subagents-with-elastic-agent-builder) + [elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch](https://www.elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch) + [github.com/elastic/agent-skills](https://github.com/elastic/agent-skills).
- **Why nobody's built it:** The pieces — subagents, agent-memory index, ELSER hybrid — are documented separately. No published example **combines** them into a code-review agent that (a) ingests every PR diff + commit history as ELSER-embedded docs, (b) stores reviewer rationale as episodic memory, (c) on the next PR semantically retrieves "the last 3 times we touched this code path and what went wrong." GitHub search `elastic agent code review memory` returns the basic GitHub Copilot SDK blog template — single-shot, no memory persistence across PRs.
- **Why it'd win the hackathon:** Code review is the most familiar agent pattern on the judge panel (Elastic itself dogfoods this internally). Differentiator = **persistent agent memory** vs. every other "review my PR" agent on DevPost. Quality of Idea: the framing "Elasticsearch as the agent's brain, not its filesystem" is exactly Krenn's `xeraa.net` style.
- **Demo arc (3 min):** Open a PR that re-introduces a known anti-pattern from 6 months ago. Agent (planning subagent → retrieval subagent → reviewer subagent) queries `agent-memory` index via Agent Builder MCP. ELSER surfaces the 3 prior incidents semantically. Agent posts a review comment "We tried this in MR #142, rolled back because of <reason>. Suggest <alternative>."
- **What you'd actually have to build:** Define 3 Agent Builder tools in Kibana (`search_pr_history`, `recall_decision_memory`, `save_review_decision`) → ELSER `semantic_text` field on commit messages + diff bodies + reviewer rationale → ADK `SequentialAgent` chain planning → retrieval → review → write_memory → GitLab/GitHub webhook trigger.

---

### HIDDEN-elastic-02: Cost-aware "model-tier-per-task" agent via Elastic Inference Service (EIS)

- **Sponsor capability:** EIS catalog — agents pick model tier per step (fast+cheap → mid → frontier reasoning) without provisioning infra.
- **What the sponsor hints at:** _"Teams can mix and match models in an agent workflow so each step uses the model best suited to the task. For example, simple interactions, such as answering 'What is our holiday policy?', do not require an expensive frontier model and can be handled by a fast, low-cost option."_
- **Source:** [elastic.co/search-labs/blog/build-ai-agents-elastic-inference-service](https://www.elastic.co/search-labs/blog/build-ai-agents-elastic-inference-service).
- **Why nobody's built it:** EIS is brand-new (Oct 2025 announcement, GA early 2026). The blog _describes_ the pattern but ships no end-to-end demo. GitHub search `elastic inference service agent example` returns the EIS docs page only, no implementations. Implementation barrier: requires agent code that _introspects upcoming subtask complexity_ and routes pre-call — non-trivial planning surface.
- **Why it'd win the hackathon:** Mirrors HIDDEN-arize-03 but ANCHORED IN ELASTIC's infra. Krenn's DevRel angle = "look at this cool thing you can do with our brand-new service." First-mover advantage in the Elastic bucket. Tech Impl: routing logic + EIS API. Potential Impact: real cost reduction.
- **Demo arc (3 min):** Customer support agent receives "Where is my order?" → uses EIS cheap-tier model. Receives "Compare delivery delays across our top-100 SKUs over Q4 and explain root causes" → upgrades to frontier-tier model. Phoenix-style cost chart shows 78% cost reduction vs. always-frontier.
- **What you'd actually have to build:** Pre-call complexity scorer (Gemini-3.5-flash-lite labels incoming queries low/med/high) → EIS API client → per-tier inference endpoint config in Agent Builder → final ADK agent orchestrates.

---

### HIDDEN-elastic-03: Document-level-security selective memory (DLS-aware agent)

- **Sponsor capability:** Elasticsearch DLS — document-level security with role-based filters applied to retrieval.
- **What the sponsor hints at:** _"Adds document-level security for selective memory retrieval — agents only see context-appropriate memories. Reduces token usage + context pollution."_
- **Source:** [elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch](https://www.elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch).
- **Why nobody's built it:** DLS is well-documented for traditional search but no published example uses it for _agent memory partitioning_. The clearest hidden use case: a multi-tenant SaaS agent where each customer's memory is isolated by DLS rules — the agent's tools never need to know tenant boundaries, ES enforces them. GitHub search `elastic agent multi-tenant DLS memory` returns no built example.
- **Why it'd win the hackathon:** Compliance-critical. Finance, healthcare, legal panels all light up at "your agent literally cannot leak across tenants because the database refuses to return the data." Tech Impl is sophisticated; Potential Impact is real revenue.
- **Demo arc (3 min):** Two simulated tenants. Tenant A agent queries memory, gets back only A's history. Tenant B agent makes the _same query_ — gets B's. Switch agent's API key to invalid tenant — agent gets back zero results, can't even hallucinate the existence of other tenants. Tracing shows ES enforced the filter.
- **What you'd actually have to build:** Kibana DLS role config per tenant → Agent Builder tools with role mapping → ADK agent with per-session role token → demo UI showing the two tenants side-by-side.

---

### HIDDEN-elastic-04: ES|QL agent that writes its own queries from natural-language anomaly hypotheses

- **Sponsor capability:** ES|QL + Agent Builder Workflows + LLM prompt step.
- **What the sponsor hints at:** _"A workflow that searches for flight delays uses an agent to summarize the impact with triggers, steps that get data from Elasticsearch, ask the agent to reason over the data, and print the agent's summary."_ Implicit hint: workflows + ES|QL + agent reasoning collapses into a "natural-language analytics" agent.
- **Source:** [elastic.co/search-labs/blog/agent-builder-one-workflow](https://www.elastic.co/search-labs/blog/agent-builder-one-workflow) + [elastic.co/blog/elastic-workflows-technical-preview](https://www.elastic.co/blog/elastic-workflows-technical-preview).
- **Why nobody's built it:** Workflows + Agent Builder integration is brand-new (preview). The Search Labs demo is a one-shot delay summary. Nobody has built the "agent forms hypothesis → writes ES|QL → reads result → revises hypothesis → re-queries" loop with multiple iterations. Recall PHAROS (prior Elastic hackathon winner) was static aggregation, not iterative.
- **Why it'd win the hackathon:** Krenn's wheelhouse — ES|QL is his stated favorite Elastic feature. Bloomberg-terminal-for-sports type framing (per our existing Idea 5 in partner-elastic.md) but ELEVATED via iteration. Quality of Idea: agent that genuinely _reasons_ about data, not just summarizes.
- **Demo arc (3 min):** Sports analyst asks "explain Brazil's defensive collapse in the 75th minute against Argentina." Agent writes ES|QL #1 (goals + cards by time window). Sees pattern. Writes ES|QL #2 (positional heatmap from the same window). Synthesizes a textual hypothesis with citations to both queries.
- **What you'd actually have to build:** YAML workflow with trigger=user-question, step1 = ES|QL-from-NL agent, step2 = result reading, step3 = follow-up ES|QL, step4 = synthesis. The YAML itself becomes the demo artifact.

---

### HIDDEN-elastic-05: A2A + MCP composed agent (Elastic = retrieval-side, A2A = coordination-side)

- **Sponsor capability:** Elastic's A2A blog explicitly framed: "A2A coordinates multiple agents; MCP gives one agent tools. They compose — A2A on top, MCP underneath."
- **What the sponsor hints at:** _"A2A protocol vs MCP for LLM agents … they compose — A2A on top, MCP underneath. Useful framing if pitching a multi-agent submission."_
- **Source:** [elastic.co/search-labs/blog/a2a-protocol-mcp-llm-agent-newsroom-elasticsearch](https://www.elastic.co/search-labs/blog/a2a-protocol-mcp-llm-agent-newsroom-elasticsearch).
- **Why nobody's built it:** A2A is brand new (mid-2025) and Elastic's blog is conceptual, not a built demo. Building "two ADK agents A2A-coordinated, each holding their own Elastic Agent Builder MCP tools" is feasible but unbuilt on DevPost. GitHub search `a2a elasticsearch agent` returns the Elastic blog + a2a-sdk → no projects.
- **Why it'd win the hackathon:** First A2A + Elastic submission likely wins on novelty. Tech Impl is deep — three protocols (A2A, MCP, OpenInference traces) playing together. Anish Mathur's PM seat means he's reading roadmap-shaped submissions favorably.
- **Demo arc (3 min):** Newsroom scenario. Reporter agent (Agent A) receives breaking story, A2A-delegates fact-checking to Verifier agent (Agent B). Both use Elastic Agent Builder MCP for retrieval but A2A-coordinate over hypothesis sharing. Joint output: a fact-checked draft with citations.
- **What you'd actually have to build:** Two ADK agents, each registered with the a2a-sdk → A2A handoff messages → both pointed at the same Elastic Agent Builder MCP endpoint → segregated subagent retrieval tools per role (reporter retrieves drafts; verifier retrieves canonical sources).

---

**Why this sponsor will judge favorably:** Philipp Krenn (`@xeraa`) lives on Twitter posting ELSER + ES|QL examples. He doesn't get excited by "I called the search API." He gets excited when you've gone deep into a _new_ primitive (Workflows, EIS, A2A, DLS-for-memory). HIDDEN-elastic-02 (EIS), HIDDEN-elastic-04 (ES|QL iterative), and HIDDEN-elastic-05 (A2A) all hit Krenn's "show me the new thing in action" sweet spot. Anish Mathur (PM) will judge favorably anything that maps cleanly to the published roadmap — HIDDEN-elastic-03 (DLS) speaks to enterprise sales motion. Don't build a generic RAG agent in this bucket; everyone will.

---

# 3. Fivetran

**Judge panel:** Elijah Davis (Lead Solutions Architect) — already built the production internal MCP-driven Fivetran governance system (100s of connectors, 99.9% uptime). Andrew Madson (Principal DevRel + Head of DevRel) — wrote "AI agents fail in production not because models are weak, but because the data stack is" + the 2026 Agentic AI Readiness Index. Both bias toward "real production data discipline" over "cute demo."

**Hint density:** Medium-high on the FinOps/governance + data-readiness angles. Low on "fun creative ideas" — the panel is enterprise-pragmatic.

---

### HIDDEN-fivetran-01: Agent-curated data quality rules (agent learns "good data" from warehouse history)

- **Sponsor capability:** Fivetran MCP `get_connection_schema_history` + `get_connection_status` + `_FIVETRAN_SYNCED` timestamp + BigQuery as the destination + Fivetran Activations.
- **What the sponsor hints at:** _"Schema drift detection is a key capability for AI agents in data engineering, flagging column renames before downstream breaks occur."_ AND _"The most cited barriers to achieving agentic AI goals are data quality and lineage (42%)."_ AND _"Fivetran's 2026 Agentic AI Readiness Index … only 15% of organizations are fully prepared."_
- **Source:** [fivetran.com/blog/85-of-enterprises-are-running-agentic-ai-on-a-data-foundation-that-isnt-ready](https://www.fivetran.com/blog/85-of-enterprises-are-running-agentic-ai-on-a-data-foundation-that-isnt-ready) + [fivetran.com/blog/how-fivetran-and-ai-turn-raw-data-into-operational-intelligence](https://www.fivetran.com/blog/how-fivetran-and-ai-turn-raw-data-into-operational-intelligence) + [github.com/fivetran/fivetran-mcp](https://github.com/fivetran/fivetran-mcp).
- **Why nobody's built it:** Fivetran ships schema-drift events; no published agent USES them to _autonomously infer expectations_ about every column ("nullability rate of `email` field has been 0.2% for 90 days → if it spikes to 8%, fire alert"). The lineage data exists, the schema-change events exist, the BigQuery query surface exists. No project on GitHub or DevPost combines them into a "data-quality rules learned by the agent, not authored by the engineer" workflow. Implementation barrier: requires bootstrapping a per-column profile, distinguishing legitimate drift from anomaly, and writing tests back as Fivetran webhook-triggered jobs.
- **Why it'd win the hackathon:** Hits Andrew Madson's published thesis dead-center. Tech Impl is genuinely novel (rule-inference is unbuilt in the agentic stack). Potential Impact: this is the #1 cited blocker (42% of enterprises). Quality of Idea: not just an agent that monitors, but an agent that _teaches itself what to monitor_.
- **Demo arc (3 min):** Agent boots, scans last 30 days of `_FIVETRAN_SYNCED` history + `INFORMATION_SCHEMA` for every Fivetran-managed table. Generates a "profile" per column (null rate, cardinality, distribution). Today's sync shows `users.signup_country` null rate jumped from 0% to 12% — agent flags as anomaly, files a Jira ticket, drafts a hypothesis ("looks like the new Stripe API field is missing in the source"), and via Fivetran MCP `get_connection_schema_history` confirms the source connector changed schema yesterday.
- **What you'd actually have to build:** ADK agent → BigQuery profiling tool (compute null-rate, cardinality across last-30d) → Fivetran MCP for schema-history fetch → anomaly-detection prompt → Jira tool → an inference-explanation prompt that ties profile drift to schema events.

---

### HIDDEN-fivetran-02: Freshness-gated agent SLOs (agent refuses to answer if data is stale)

- **Sponsor capability:** Fivetran MCP `get_last_sync` + `trigger_sync` + per-connector freshness windows.
- **What the sponsor hints at:** Speakeasy customer case study: _"Claude checks Snowflake for data age, triggers a Fivetran sync if the data is stale, runs dbt to rebuild the views, and confirms the data's freshness, all in about 5 minutes."_
- **Source:** [speakeasy.com/customers/fivetran](https://www.speakeasy.com/customers/fivetran) + [fivetran.com/blog/integrate-data-faster-using-natural-language-fivetran-and-mcp](https://www.fivetran.com/blog/integrate-data-faster-using-natural-language-fivetran-and-mcp).
- **Why nobody's built it:** The Speakeasy snippet is _the closest published example_, and it's used as a marketing anecdote, not a built agent. Nobody has _productized_ this as a "freshness SLO middleware" — the pattern where the agent refuses to commit to an answer unless freshness is within tolerance. The pattern is mentioned in the partner-fivetran.md (our own research) as Idea 1 + 2 but no actual third-party implementation exists.
- **Why it'd win the hackathon:** Elijah Davis's day job is governance + audit trails. A "freshness SLO" pattern speaks directly to his architectural taste. Potential Impact: prevents the classic "agent answered with stale revenue numbers, exec made wrong call" disaster.
- **Demo arc (3 min):** CFO asks the agent "what's today's revenue?" Agent calls Fivetran MCP `get_last_sync(connection="stripe-prod")` → finds last sync was 4 hours ago, SLO requires <30 min. Agent: "I cannot answer reliably; Stripe is 4 hours stale. Triggering sync now — back in 90 seconds." `trigger_sync` → wait → re-check → answer with citation `_FIVETRAN_SYNCED=2026-06-03T16:09:14Z`.
- **What you'd actually have to build:** ADK agent with a "freshness gate" pre-call middleware → SLO config YAML → Fivetran MCP integration → BigQuery analytical tool → a clean refusal UX in the web frontend.

---

### HIDDEN-fivetran-03: AI-authored custom Connector SDK connectors (NL → deployable connector)

- **Sponsor capability:** `fivetran-connector-sdk` Python framework + `fivetran_csdk_tools` AI coding agent skills (build/test/deploy).
- **What the sponsor hints at:** _"By exposing Fivetran's Connector SDK and platform APIs as MCP servers, it's possible to enable customers to use AI agents to build custom connectors through natural language … The agent learns context from the API documentation, then uses the MCP server to create the connector files, debugs connection issues, and deploys the solution to Fivetran where it appears immediately in the dashboard."_
- **Source:** [github.com/fivetran/fivetran_csdk_tools](https://github.com/fivetran/fivetran_csdk_tools) + [github.com/fivetran/fivetran_connector_sdk/blob/main/ai_and_connector_sdk/agents.md](https://github.com/fivetran/fivetran_connector_sdk/blob/main/ai_and_connector_sdk/agents.md) + [dbta.com — Elijah Davis built one in 30 minutes](https://www.dbta.com/Editorial/Trends-and-Applications/Sponsored-Content-How-I-Built-a-Data-Connector-in-30-Minutes-with-AI-and-Why-You-Should-Try-it-at-the-AI-Accelerate-Unlocking-New-Frontiers-Hackathon-171572.aspx).
- **Why nobody's built it:** The csdk_tools repo ships skills for Claude Code / Codex CLI / Gemini CLI but **no end-to-end ADK-driven agent that goes URL → deployed connector** has been built. Elijah Davis used Cursor (not ADK) for his 30-minute build. The hackathon banned-AI rule disqualifies Cursor in the SUBMISSION, but ADK + Gemini = legal — and nobody has done it yet.
- **Why it'd win the hackathon:** Literally a judge (Elijah Davis) blogged about doing this with the wrong tool (Cursor). Building it with the _right_ tool (ADK + Gemini) is essentially saying "I built what you wanted built." Tech Impl is the deepest possible Fivetran integration — touching both MCP + Connector SDK. Potential Impact: any data team can add a custom source in minutes.
- **Demo arc (3 min):** User pastes an API docs URL ("Acme CRM v2 API"). Agent reads docs, generates `connector.py`/`config.json`/`requirements.txt` per Fivetran SDK conventions, runs local test against the API, deploys via Fivetran MCP, schedules a sync. New table appears in BigQuery 5 minutes later.
- **What you'd actually have to build:** ADK agent + a Connector SDK code-generation prompt + a sandboxed Python exec tool (Cloud Run job) + Fivetran MCP for deploy → schedule → verify. The agent's first iteration always fails; the loop is "test → read error → patch → retest" until green.

---

### HIDDEN-fivetran-04: Cross-source agentic data join with provenance

- **Sponsor capability:** Fivetran MCP's `get_connection_metadata` returns full schema+lineage per connector. BigQuery is the destination.
- **What the sponsor hints at:** _"Cross-source unification is the entire value prop. Salesforce + Stripe + HubSpot + Zendesk → BigQuery → agent does cross-source analysis ('which Stripe-paying customers have stalled Salesforce deals AND open Zendesk tickets?')."_
- **Source:** Our own partner-fivetran.md (cites the partner brief) + [fivetran.com/learn/data-curation](https://www.fivetran.com/learn/data-curation).
- **Why nobody's built it:** Multi-source joins are routine, but no published agent **annotates every joined row with its source-of-record lineage** ("this row came from Salesforce sync at T1, joined with Stripe sync at T2, total provenance trust score = 0.87"). GitHub search returns lineage tools (Atlan, Datafold) but no agentic implementation in the Fivetran MCP context.
- **Why it'd win the hackathon:** Provenance-tracking is the data-governance hot button (cited in 39% of Fivetran's 2026 Readiness Index as a blocker). Davis's audit-trail emphasis. Madson's governance emphasis.
- **Demo arc (3 min):** User asks "list at-risk enterprise customers." Agent joins Salesforce.accounts × Stripe.subscriptions × Zendesk.tickets. Returns a list — but every cell of the answer has a provenance tooltip: source connector + sync timestamp + row count.
- **What you'd actually have to build:** ADK agent + Fivetran MCP per-source metadata fetcher + BigQuery analytical query + a frontend renderer that ties result cells to lineage metadata.

---

### HIDDEN-fivetran-05: Schema-drift impact predictor (the dbt-test-killer)

- **Sponsor capability:** Fivetran MCP `get_connection_schema_history` + BigQuery `INFORMATION_SCHEMA` + agent reasoning over downstream consumers.
- **What the sponsor hints at:** _"Schema drift in source SaaS silently breaks downstream dashboards … Fivetran tracks schema changes as first-class events. Agent monitors `schema_change` events via Fivetran MCP, evaluates downstream impact."_
- **Source:** Our own partner-fivetran.md Idea 6 (citing the brief).
- **Why nobody's built it:** Schema-change events are documented but no published example **predicts downstream breakage** (compute which BigQuery views, dbt models, Looker dashboards depend on the changed column — alert _those_ owners specifically). The pre-work for this requires graph-walking the BQ DAG. GitHub: nothing built.
- **Why it'd win the hackathon:** Madson's published "data quality + lineage = top 2 blocker" thesis. Tech Impl: agent walks BigQuery dependency graph autonomously. Potential Impact: the entire "data contract" movement is about this.
- **Demo arc (3 min):** Source Salesforce drops the `lead_source_v2` column overnight. Fivetran MCP surfaces the schema event. Agent traces BQ DAG: 7 downstream views depend on it. 3 belong to Marketing, 4 to RevOps. Agent posts a per-team Slack alert with the impact graph. Marketing's "MQL pipeline" dashboard is going to break in 4 hours.
- **What you'd actually have to build:** Fivetran MCP webhook listener → BigQuery `INFORMATION_SCHEMA.VIEW_TABLE_USAGE` walker → owner-lookup tool → Slack tool → ADK SequentialAgent.

---

**Why this sponsor will judge favorably:** Elijah Davis and Andrew Madson both have a public stake in "the data foundation is the real bottleneck for agents." Their published Readiness Index says only 15% of orgs are ready, and ALL of these hidden use cases address the gaps in that index. Davis's hands-on architecture experience means he'll grade harshly on submissions with hardcoded mock data and softly on submissions that show real lineage + freshness + governance. HIDDEN-fivetran-01 (rule-inference) and HIDDEN-fivetran-03 (NL → connector) are the two that map most directly to his and Madson's published positions. **The bias of this judging panel against "creative but unbusiness-like" submissions is the highest of any partner — match it.**

---

# 4. GitLab

**Judge panel:** Regnard Raquedan (Sr. Solutions Architect, Google Cloud Lead — author of "Secure and fast deployments to Google Agent Engine with GitLab"). Nick Veenhof (Dir. Contributor Success — ran the GitLab AI Hackathon 2026 with 7,000 builders, 600+ projects; explicitly framed "not chatbots that answer questions, but agents that jump into workflows, respond to events, and act on your behalf"). The panel cares most about **agents that ACT**, not agents that talk.

**Hint density:** Highest of any sponsor for "workflow that acts" — the entire Duo Agent Platform thesis IS this. But also the highest "already-built" risk because the Feb–Mar 2026 internal hackathon (Devpost: gitlab.devpost.com) produced 600 projects. Hidden uses must specifically avoid that 600.

---

### HIDDEN-gitlab-01: Team-velocity DORA coach (the keystone GitLab idea)

- **Sponsor capability:** `semantic_code_search` + `manage_pipeline` + `get_merge_request_diffs` + GitLab DORA metrics + Knowledge Graph + AI Catalog (publish coach agent for the team).
- **What the sponsor hints at:** _"You can measure impact on DORA metrics and create dashboards to showcase the benefits of AI implementation."_ AND _"Having GitLab Duo AI agents embedded in the system of record for code, tests, CI/CD, and the entire software development lifecycle boosts productivity, velocity, and efficiency."_ Plus the existence of `analytics/dora_metrics` endpoints in the GitLab API.
- **Source:** [docs.gitlab.com/user/analytics/dora_metrics/](https://docs.gitlab.com/user/analytics/dora_metrics/) + [docs.gitlab.com/user/duo_agent_platform/](https://docs.gitlab.com/user/duo_agent_platform/) + [docs.gitlab.com/user/project/repository/knowledge_graph/](https://docs.gitlab.com/user/project/repository/knowledge_graph/).
- **Why nobody's built it:** Of the 600+ projects from GitLab Hackathon 2026 (Feb–Mar 2026), the winners are bug/security/code-review agents (Gitdefender, Aegis, GraphDev, RepoWarden, MR Compliance Auditor, stregent — per the winners blog). **None of them is a team-velocity coach.** The DORA metrics API + Duo Agent Platform combination is hinted at in docs but never built as an agentic coach. Implementation barrier: requires reading DORA metrics, correlating with MR/Pipeline patterns, and _coaching_ the team (suggesting workflow changes) — not just reporting.
- **Why it'd win the hackathon:** Veenhof's stated vision ("agents that act, not chatbots") + Raquedan's enterprise focus = a DORA coach that _acts on the team's behalf_ (auto-prioritizes stale MRs, reorders the merge queue, suggests reviewers) is exactly the shape they want. Quality of Idea wins because no one in the 600 thought of _coaching_ (everyone built _doing_). Potential Impact: every engineering org tracks DORA, almost none has an active coach.
- **Demo arc (3 min):** Open a team dashboard. Agent computes current DORA: deploy frequency 1.4/day, lead time 3.2 days, change failure rate 12%. Identifies cycle-time bottleneck: "PRs sit in review state for 18 hrs on average; this MR has been open 4 days." Agent auto-pings the reviewer via `create_workitem_note`, semantic-searches the codebase to find a more recent contributor to that file, reassigns the review, and posts a thread "I noticed Alice merged the previous change to this file 3 weeks ago and is more likely to clear this fast."
- **What you'd actually have to build:** ADK `LoopAgent` → GitLab MCP `manage_pipeline` + `search` + `semantic_code_search` + `get_merge_request_diffs` + `create_workitem_note` + DORA metrics API (REST, not MCP yet) → coach prompt that reasons over the metrics + suggests interventions → publish as AI Catalog entry.

---

### HIDDEN-gitlab-02: Knowledge Graph + MCP code-archaeology agent

- **Sponsor capability:** GitLab Knowledge Graph (live graph of files, directories, classes, functions, relationships) + `semantic_code_search` + MCP integration.
- **What the sponsor hints at:** _"The Knowledge Graph turns your codebase into a live, embeddable graph database for AI agents."_ AND _"The Deep Research Agent leverages the GitLab Knowledge Graph and semantic search capabilities to traverse your epic and all related issues, and explore the related codebase and surrounding context."_
- **Source:** [docs.gitlab.com/user/project/repository/knowledge_graph/](https://docs.gitlab.com/user/project/repository/knowledge_graph/) + [Codex CLI on GitLab blog](https://codex.danielvaughan.com/2026/04/07/codex-cli-gitlab-integration-duo-agent-platform/).
- **Why nobody's built it:** Knowledge Graph is in beta, ships with the platform — no published example uses it for _historical archaeology_ ("why was this line written? trace it back through every issue, MR, and discussion that produced it"). Among 600 hackathon projects, only RepoWarden ("Living Specification Engine") gets close, but that's about _capturing_ not _excavating_ history. The agent that does the reverse — given a function in `main`, walks the Graph backward to the first issue that motivated it — is unbuilt.
- **Why it'd win the hackathon:** Raquedan's "Vertex AI on Google Cloud advancing agentic development" angle: a code-comprehension agent that uses GitLab's unique multi-product graph (issues, MRs, pipelines, code) as one searchable surface. No competing platform can offer this graph; building on it advertises GitLab's specific moat.
- **Demo arc (3 min):** New engineer hovers over an obscure function in `payments.py`. Agent traces it through Knowledge Graph: function added in MR #847 by Bob, which closed Issue #823 ("PCI compliance audit failure"), which referenced Epic #45 ("Q3 2024 SOX remediation"), which cited a now-deleted Confluence link. Agent surfaces the whole archaeological tree in 4 seconds.
- **What you'd actually have to build:** ADK agent + GitLab MCP `semantic_code_search` + `get_merge_request` + `get_issue` + Knowledge Graph queries (REST or MCP wrap) + visualization (visx graph view).

---

### HIDDEN-gitlab-03: Multi-project triage agent (cross-project search + AI Catalog)

- **Sponsor capability:** `search` (full-instance), `search_labels`, AI Catalog (share the agent across the org).
- **What the sponsor hints at:** _"The AI Catalog is a central list of agents and flows that you can add to your project to orchestrate agentic AI tasks … promoting consistency, reusability, and collaboration."_
- **Source:** [docs.gitlab.com/user/duo_agent_platform/ai_catalog/](https://docs.gitlab.com/user/duo_agent_platform/ai_catalog/) + [about.gitlab.com/blog/ai-catalog-discover-and-share-agents/](https://about.gitlab.com/blog/ai-catalog-discover-and-share-agents/).
- **Why nobody's built it:** AI Catalog is the discovery/publishing surface. Among 600+ hackathon projects, all are project-scoped. No published agent is _built for AI Catalog publishing_ as a first-class concern (multi-project, label-portable, parameterizable). The "publish your agent for re-use" muscle is exactly the contributor-success surface Nick Veenhof owns.
- **Why it'd win the hackathon:** Direct play to Veenhof's role + GitLab's open-source ethos. Tech Impl: parameterized agent definitions + AI Catalog metadata. Potential Impact: viral re-use across the GitLab community.
- **Demo arc (3 min):** Engineering org with 50 projects. Engineer publishes "SecurityTriage" agent to the AI Catalog. Three other projects install it from the Catalog in 30 seconds each. Same agent, different label filters per project (`security::critical` in project A; `vuln::p0` in project B). Each project's customization is parameter-overridden, the agent code is shared.
- **What you'd actually have to build:** A custom Agent (in GitLab Duo Custom Agent format) + custom flow → publish to AI Catalog → demo install-and-customize from a second project.

---

### HIDDEN-gitlab-04: World Cup 2026 release conductor (high-fit Devpost domain, schedule-aware deploys)

- **Sponsor capability:** `manage_pipeline` + external scheduling API integration via Workflows.
- **What the sponsor hints at:** Our own partner-gitlab.md Idea 3 calls this out as the strongest Devpost-domain fit; the GitLab docs describe pipeline gating in terms of environment + approvals, but no AI agent gating deploy based on a _external real-time event feed_ (match schedule).
- **Source:** [docs.gitlab.com/ci/yaml/](https://docs.gitlab.com/ci/yaml/) (pipeline rules + when:manual) + [docs.gitlab.com/user/duo_agent_platform/flows/](https://docs.gitlab.com/user/duo_agent_platform/flows/).
- **Why nobody's built it:** Pipeline gating by external feeds is doable manually (cron + manual approval), but no agent does it autonomously. Demo opportunity is unique because the World Cup 2026 IS during the judging window (June 22 – July 6, 2026 judging period overlaps with World Cup group/knockout play).
- **Why it'd win the hackathon:** Hits Devpost example domain head-on. Quality of Idea: real-world coordination problem. Demo is theatrical (match kickoff timer ticking down, deploy pipeline auto-pauses).
- **Demo arc (3 min):** Match schedule fetched from an external sports API. Engineer pushes a deploy. Agent intercepts via Duo Flow trigger, checks current time against next kickoff, sees Argentina vs. Brazil starts in 23 minutes, auto-defers the deploy with `manage_pipeline(action="cancel")` and posts a comment "Deferred to T+90min post-match per release-window policy." After match, agent resumes pipeline.
- **What you'd actually have to build:** External sports schedule API integration + Duo Custom Flow + ADK agent with GitLab MCP for pipeline control + a fake "production service" to deploy to.

---

### HIDDEN-gitlab-05: Compliance evidence collector with SOC 2 mapping

- **Sponsor capability:** `search`, `semantic_code_search`, `get_merge_request_diffs`, `create_workitem_note`, `create_issue` — combined with a SOC 2 controls KB.
- **What the sponsor hints at:** GitLab Hackathon 2026 winner "MR Compliance Auditor" got close: "collects evidence across merge requests, maps it to SOC 2 controls, and streams compliance scores to a live dashboard." But it's collection + scoring, not active intervention.
- **Source:** [about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/](https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/).
- **Why nobody's built it (in the augmented form):** MR Compliance Auditor is purely retrospective. The hidden gap: a _forward-looking_ agent that **prevents** non-compliant MRs (blocking + auto-suggesting remediation) rather than just scoring after the fact. Different shape, different code surface.
- **Why it'd win the hackathon:** Differentiates from the existing winner. Veenhof's "agents that act" vision specifically rewards _intervention_ over _observation_. Potential Impact: regulated industries (FinServ, Healthcare).
- **Demo arc (3 min):** Engineer opens MR touching payment code. Agent intercepts via Duo Flow, semantic-searches for SOC 2-tagged related code, identifies missing audit log line, **blocks the merge** until added, and via `create_workitem_note` suggests the exact patch.
- **What you'd actually have to build:** Custom Flow triggered on MR creation + SOC 2 control KB (small JSON) + `semantic_code_search` + diff analysis → block-or-pass decision + auto-suggest patch via inline comment.

---

**Why this sponsor will judge favorably:** Nick Veenhof's "agents that ACT" mantra (verbatim from his hackathon launch post) is the single most actionable judging-fit signal of any partner. Build for verbs (defer, block, reassign, coach, escalate, deploy), not nouns (report, summarize, dashboard). Regnard Raquedan's specialty is GitLab + Google Cloud deployments; submissions that show clean Cloud Run deployment + Workload Identity Federation will score higher on Tech Impl. **HIDDEN-gitlab-01 (DORA coach) is the highest leverage because (a) no one in the 600-project Feb 2026 hackathon built it, (b) every engineering org tracks DORA, (c) it's explicitly "act, not chat".**

---

# 5. MongoDB

**Judge panel:** Daoud Farooqi (Partner Solutions Architect, AI & Data Platforms) — RPA + AI background, enterprise integration angle. Gaurab Aryal (Sr. PM, AI agents) — author of [mongodb.com/blog/authors/gaurab-aryal](https://www.mongodb.com/blog/authors/gaurab-aryal); his 2026 talk explicitly: "MongoDB Atlas Vector Search provides long-term and episodic memory." Both judges have shipped public content on agent memory + agentic RAG.

**Hint density:** Very high. MongoDB has been publishing the most aggressive "MongoDB IS the agent stack" content of any partner.

---

### HIDDEN-mongodb-01: Live policy enforcement via $vectorSearch on every write (forbidden-pattern firewall)

- **Sponsor capability:** Atlas Stream Processing's `validate` + external function support + `$vectorSearch` aggregation stage + auto-embed via Voyage AI.
- **What the sponsor hints at:** _"It allows performing continuous validation to check that messages are properly formed, transforming fields as documents flow through pipelines and routing them to distinct databases."_ AND _"External functions can be used for fraud detection, personalization, enrichment from third-party APIs."_ AND auto-embed lets you _"keep the embeddings in sync as your data changes"_.
- **Source:** [mongodb.com/docs/atlas/atlas-stream-processing/overview/](https://www.mongodb.com/docs/atlas/atlas-stream-processing/overview/) + [mongodb.com/company/blog/new-mongodb-atlas-stream-processing-external-function-support](https://www.mongodb.com/company/blog/new-mongodb-atlas-stream-processing-external-function-support) + [mongodb.com/company/blog/product-release-announcements/unlocking-ai-search-introducing-automated-embedding-in-mongodb-vector-search](https://www.mongodb.com/company/blog/product-release-announcements/unlocking-ai-search-introducing-automated-embedding-in-mongodb-vector-search).
- **Why nobody's built it:** Stream Processing + $vectorSearch + auto-embed are documented separately. No published implementation **on every write event, semantically compares the document to a vector index of "forbidden patterns" (PII leakage, prompt injection, abusive content, banned competitive trade-secret keywords) and rejects or quarantines before commit.** GitHub search for `mongodb stream processing vector validation` returns the docs only. Implementation barrier: requires Stream Processor to call an external function that does vectorSearch + threshold check.
- **Why it'd win the hackathon:** Real-time content moderation / DLP is a multi-billion-dollar category; nobody has built it on MongoDB primitives. Quality of Idea is genuinely fresh. Potential Impact: every social platform, every B2B SaaS, every enterprise need this. Tech Impl: 3 MongoDB surfaces (Stream Processing, $vectorSearch, Voyage auto-embed) in one pipeline.
- **Demo arc (3 min):** Live form fed by Kafka. User submits a comment containing a subtle PII pattern (e.g., a credit card number obfuscated as `4111 1111 1111 1111`). Stream Processor auto-embeds it, $vectorSearch finds similarity 0.94 to a known PII vector, external function (an ADK agent) decides "reject, surface to moderator." User sees "Your post was flagged for review." Demo also shows benign post passing in <100ms.
- **What you'd actually have to build:** Atlas Stream Processor with `validate` stage → external function = a Cloud Run-hosted ADK agent → MongoDB MCP `aggregate` with $vectorSearch → forbidden-patterns vector index (seed with ~500 examples) → kafka source → demo UI.

---

### HIDDEN-mongodb-02: Hybrid-search agent via $rankFusion (BM25 + vector + filter in one query)

- **Sponsor capability:** `$rankFusion` aggregation stage (Preview in MongoDB 8.0+).
- **What the sponsor hints at:** _"$rankFusion first executes all input pipelines independently and then de-duplicates and combines the input pipeline results into a final ranked results set … using the Reciprocal Rank Fusion algorithm."_ AND _"Hybrid search with MongoDB Atlas delivers a powerful solution for applications that require both precision and semantic understanding."_
- **Source:** [mongodb.com/docs/manual/reference/operator/aggregation/rankfusion/](https://www.mongodb.com/docs/manual/reference/operator/aggregation/rankfusion/) + [mongodb.com/company/blog/technical/harness-power-atlas-search-vector-search-with-rankfusion](https://www.mongodb.com/company/blog/technical/harness-power-atlas-search-vector-search-with-rankfusion).
- **Why nobody's built it:** $rankFusion is brand new (Preview, MongoDB 8.0+). Search of GitHub for `$rankFusion agent` returns the docs only. Most agent demos still use plain $vectorSearch. The native fusion is unbuilt in the agentic stack.
- **Why it'd win the hackathon:** Atlas Search + Vector Search judges (Daoud Farooqi specifically) reward submissions that show off the _unified_ surface (not just one or the other). Tech Impl bonus from using a Preview feature correctly. Quality of Idea: nuanced hybrid ranking beats any "I called $vectorSearch" agent.
- **Demo arc (3 min):** Real-estate concierge agent. User: "find me a quiet 3-bedroom near a Tube station in Zone 2 with good morning sun." BM25 catches "Zone 2" + "Tube station". Vector catches "quiet" + "morning sun" (semantic). $rankFusion weights and combines. Filter applies on `bedrooms >= 3`. Result reorders intelligently. Side-by-side vs. plain $vectorSearch shows materially better ranking.
- **What you'd actually have to build:** Seed a corpus (Wikipedia-scraped property docs or Zillow API exports), create both an Atlas Search index AND a Vector Search index, write the $rankFusion aggregation, ADK agent for query parsing + result rendering.

---

### HIDDEN-mongodb-03: TTL-driven agent memory garbage collection (LangGraph + MongoDB TTL pattern)

- **Sponsor capability:** MongoDB TTL indexes + LangGraph TTL integration.
- **What the sponsor hints at:** _"MongoDB's Time-to-Live (TTL) indexes are integrated with LangGraph's TTL system, allowing automatic removal of stale or outdated data, which improves retrieval performance, reduces storage costs, and ensures the system 'forgets' obsolete memories efficiently."_
- **Source:** [mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph](https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph).
- **Why nobody's built it:** The MongoDB blog mentions it as a feature; no built example demonstrates a "memory hygiene" agent that actively manages its own forgetting (selecting which memories to keep beyond TTL via promotion-by-importance, demoting others, computing aggregate summaries before TTL expiry). Combining TTL with vectorSearch-relevance ranking is unbuilt.
- **Why it'd win the hackathon:** Aryal's product surface area (agent memory) speaks to this directly. Quality of Idea: "agents that forget gracefully" is fresh. Note hackathon rule: LangGraph is not primary orchestrator-permitted; rebuild the TTL+importance pattern in ADK instead (this is a feature, not a bug — distinguishes you from the LangGraph crowd).
- **Demo arc (3 min):** Agent runs for "1 simulated month" (compressed). At any time has ~10,000 memories. Importance scoring agent runs nightly: top 100 promoted to long-term (TTL=∞), rest demoted to 7-day TTL, near-expiry memories get auto-summarized into a single "monthly digest" doc before deletion. Demo shows storage growing linearly then plateauing as TTL kicks in.
- **What you'd actually have to build:** ADK `LoopAgent` for nightly memory triage + MongoDB MCP `aggregate` for importance scoring (mix of recency × vectorSearch frequency × user feedback) + TTL index management via `create-index` + summary-write via `insert-many` + clean visualization.

---

### HIDDEN-mongodb-04: Voyage code-3 + semantic code search agent for the dev's own past projects

- **Sponsor capability:** `voyage-code-3` embedding + $vectorSearch + 32K context length + low cost ($0.06/MTok, first 200M free).
- **What the sponsor hints at:** _"Voyage-code-3 is MongoDB's next-generation embedding model optimized for code retrieval that outperforms OpenAI-v3-large and CodeSage-large by an average of 13.80%."_
- **Source:** [mongodb.com/company/blog/voyage-code-3-more-accurate-code-retrieval-lower-dimensional-quantized-embeddings](https://www.mongodb.com/company/blog/voyage-code-3-more-accurate-code-retrieval-lower-dimensional-quantized-embeddings) + [mongodb.com/docs/voyageai/models/](https://www.mongodb.com/docs/voyageai/models/).
- **Why nobody's built it:** voyage-code-3 is publicized as a benchmark winner but rarely paired in published agents (search returns the docs + a few demos that use it for generic search, not personal-codebase memory). The "personal code archaeology" use case is unbuilt on MongoDB.
- **Why it'd win the hackathon:** Solo-dev relatable. Aryal's PM focus on AI for developers maps. Tech Impl: code-specific embedder vs. generic text embedder is a deliberate design decision the judge will notice.
- **Demo arc (3 min):** Engineer drops a folder of past projects (git histories). Agent ingests commits + diffs + READMEs as voyage-code-3 embeddings. User asks "how did I handle Stripe webhook retries last year?" → agent retrieves 3 closely-matching code snippets from 3 different repos, summarizes the pattern. Cross-repo institutional knowledge.
- **What you'd actually have to build:** ADK agent + voyage-code-3 auto-embed via MongoDB Atlas + ingest pipeline for git directory + `insert-many` with auto-embed + $vectorSearch query tool + a small CLI/web UI.

---

### HIDDEN-mongodb-05: Microsoft Foundry integration via Atlas (cross-vendor agent memory)

- **Sponsor capability:** MongoDB Atlas + Microsoft Foundry / OpenAI integration — agent memory works across vendor LLMs.
- **What the sponsor hints at:** _"Building Next-gen AI agents: The MongoDB Atlas-Microsoft Foundry Integration"_ blog headline + the docs page _"Build AI Agents with MongoDB Vector Search"_ explicitly listing integrations with multiple agent frameworks.
- **Source:** [mongodb.com/company/blog/innovation/building-next-gen-ai-agents-mongodb-atlas-integration-microsoft-foundry](https://www.mongodb.com/company/blog/innovation/building-next-gen-ai-agents-mongodb-atlas-integration-microsoft-foundry).
- **Why nobody's built it (in a way that complies with this hackathon):** The hackathon prohibits Azure/AWS runtime, so a literal cross-cloud agent is disqualifiable. **The hidden version compliant with the hackathon rules: an agent whose memory store (MongoDB) is portable across LLM providers — same memory, swap from Gemini to <hypothetical second LLM provider> with zero code change.** This is the _portability_ hint — MongoDB as the agent's brain regardless of model.
- **Why it'd win the hackathon:** Speaks to Farooqi's enterprise architect taste — multi-vendor reality. Tech Impl: cleanly separates memory layer from inference layer. Note: keep Gemini as the runtime LLM to comply with hackathon rules; just demonstrate portability conceptually.
- **Demo arc (3 min):** Agent built with ADK + Gemini. Memory entirely in MongoDB Atlas. Swap a single config line — same agent now uses Vertex AI Gemini 3.5 Pro vs Flash; identical memory retrieval, no schema changes.
- **What you'd actually have to build:** Cleanly factored ADK agent where memory is a `MongoMemoryStore` class, LLM is a separate adapter; show the adapter swap on screen. Less novel than #1-4 but reads as "production-grade architecture."

---

**Why this sponsor will judge favorably:** Gaurab Aryal has been the loudest MongoDB voice on "agent memory IS the product." Daoud Farooqi's RPA background = appreciation for real-world ops. Submissions that treat MongoDB as the agent's brain (memory + retrieval + policy enforcement) — not just a JSON store — score highest. HIDDEN-mongodb-01 (write-time policy via $vectorSearch) is the keystone because it goes beyond memory into _active policy enforcement_ — a category MongoDB has never had before. Pair it with HIDDEN-mongodb-02 (rankFusion) for both the "new primitive" + "hybrid retrieval" judge boxes.

---

# 6. Dynatrace

**Judge panel:** Sean O'Dell (Principal PMM, DX — "the rise of the developer" thesis). Jeff Blankenburg (Principal Dev Advocate — published 31 daily blog posts in Jan 2026 about building production AI with Claude Code; built `collectyourcards.com` as his side project; author of "10 things I learned writing 49,000 words about vibe coding"). The panel cares MOST about: **developer-facing agents** (less about deep SRE), **AI-coding-agent observability** (Blankenburg's beat), and **real production data** (no mocks).

**Hint density:** Highest of any sponsor on AI-coding-agent monitoring (literally an entire product line).

---

### HIDDEN-dynatrace-01: AI-Coding-Agent Budget Guardrail (the keystone Dynatrace idea)

- **Sponsor capability:** Dynatrace AI Coding Agent monitoring (Claude Code, Gemini CLI, Codex CLI, OpenCode, GitHub Copilot SDK) — built-in OTel signals, token usage tracking, cost per session, runaway detection. **Plus** `create_workflow_for_notification` + `send_slack_message` + `execute_dql` MCP tools.
- **What the sponsor hints at:** _"FinOps & governance features track spend/tokens by model, detect runaway sessions, and define guardrails (budgets, thresholds, adoption controls)."_ AND _"Dashboards and alerts help teams investigate failures, spot latency spikes, and catch unusual spend or error patterns early."_
- **Source:** [dynatrace.com/news/blog/dynatrace-expands-ai-coding-agent-monitoring/](https://www.dynatrace.com/news/blog/dynatrace-expands-ai-coding-agent-monitoring/) + [github.com/dynatrace-oss/dynatrace-ai-agent-instrumentation-examples/tree/main/ai-coding-agents](https://github.com/dynatrace-oss/dynatrace-ai-agent-instrumentation-examples/tree/main/ai-coding-agents).
- **Why nobody's built it:** Dynatrace shipped the _monitoring_ primitive (passive — sees what's happening). Nobody has built the **active guardrail agent** that watches the OTel feed in real time and _intervenes_ — kills the session, downgrades to a cheaper model, demands user re-authorization when token spend exceeds budget. GitHub search `dynatrace AI coding agent guardrail budget` returns only the monitoring instructions; no community has wrapped them into a closed-loop guardrail.
- **Why it'd win the hackathon:** Sean O'Dell's "rise of the developer" thesis literally screams for this — developers now own the SDLC including the cost. Jeff Blankenburg's 31-day Claude Code project is exactly the kind of personal experiment that would have benefited. Quality of Idea: every dev with a Claude Code subscription has had a runaway session. Tech Impl: combines OTel ingestion + DQL alerting + MCP-driven workflow trigger. Potential Impact: real money saved.
- **Demo arc (3 min):** Engineer kicks off a Claude Code session via the instrumented CLI. Dashboard live-updates token count + spend. Dev makes a "build me a Next.js site" request → agent gets stuck in a loop calling itself. At spend ≥$10 the budget guardrail agent (running on Cloud Run) fires a DQL anomaly alert, autonomously calls `create_workflow_for_notification`, sends Slack: "Your Claude Code session has spent $10 in 6 minutes (normal: $1.50). Pausing." Auto-pauses by triggering a kill signal to the local CLI. Optional: agent posts a one-paragraph diagnosis from `chat_with_davis_copilot` about why the loop happened.
- **What you'd actually have to build:** Instrument Claude Code (or Gemini CLI) per the dynatrace-oss examples → DQL query for token-spend-rate anomaly → Davis Anomaly Detection → Workflow trigger → Cloud Run-hosted ADK agent that decides "alert vs pause vs kill" → local CLI kill hook (the trickiest bit — requires reading the dynatrace-ai-agent-instrumentation-examples carefully to find a programmatic pause path; if absent, fall back to "send a desktop notification + require human y/n").

---

### HIDDEN-dynatrace-02: On-call SRE agent with Davis Copilot causal chain narration

- **Sponsor capability:** `list_problems` + `execute_dql` + `chat_with_davis_copilot` + `find_entity_by_name` + `send_slack_message`.
- **What the sponsor hints at:** _"Davis AI can trigger workflow automation to automatically remediate issues using no-code workflow actions for collaboration (like Slack, Microsoft Teams, ServiceNow, PagerDuty) and remediation (like AWS, Red Hat Ansible, Kubernetes)."_
- **Source:** [dynatrace.com/news/blog/transform-your-operations-with-davis-ai-root-cause-analysis/](https://www.dynatrace.com/news/blog/transform-your-operations-with-davis-ai-root-cause-analysis/) + [dynatrace.com/news/blog/hypermodal-ai-dynatrace-expands-davis-ai-with-davis-copilot/](https://www.dynatrace.com/news/blog/hypermodal-ai-dynatrace-expands-davis-ai-with-davis-copilot/).
- **Why nobody's built it (in the differentiated form):** Our own partner-dynatrace.md called this "very on-the-nose; many submissions will pick this." Differentiate by adding **narration**: the agent doesn't just route the problem, it explains the causal chain in natural language ("checkout slowdown ← payment-svc p99 spike ← Postgres connection pool exhaustion ← deploy 4 minutes ago that lowered the pool size from 100 → 50"). The narration uses Davis Copilot + DQL combined.
- **Why it'd win the hackathon:** Blankenburg's developer-facing bias — devs want narratives, not dashboards. Sean O'Dell's "developers own production" — narration = actionable knowledge transfer. Demo arc is visually compelling.
- **Demo arc (3 min):** PagerDuty fires. ADK agent reads `list_problems`, identifies the top problem, runs `execute_dql` for context, calls `chat_with_davis_copilot` to construct the causal chain. Posts to Slack: a 6-line numbered narrative + a graph image of the dependency. On-call dev reads it in 10 seconds.
- **What you'd actually have to build:** OneAgent on a simple Cloud Run app (synthetic traffic + planted incident) → ADK orchestrator with the 5 MCP tool chain → Slack tool → image renderer for the dependency graph.

---

### HIDDEN-dynatrace-03: Two-track observability via Bindplane (Phoenix + Grail fan-out)

- **Sponsor capability:** Bindplane (acquired April 2026) — OTel-native unified telemetry pipeline; free for Google Cloud Observability subscribers.
- **What the sponsor hints at:** _"IT teams will have the option to pre-process telemetry data to reduce costs and streamline workflows … route telemetry data to multiple backend systems."_
- **Source:** [dynatrace.com/news/blog/dynatrace-to-acquire-bindplane-telemetry-pipeline/](https://www.dynatrace.com/news/blog/dynatrace-to-acquire-bindplane-telemetry-pipeline/) + [bindplane.com/google](https://bindplane.com/google).
- **Why nobody's built it:** Bindplane was acquired 6 weeks ago (April 2026). The integration story is sketched but no published agent FAN-OUTS OTel traces to BOTH a Phoenix backend AND a Dynatrace Grail backend, then _cross-references findings between them_ (e.g., Phoenix says "agent hallucination rate spiked at T1" → Bindplane routes the same OTel data to Grail → Grail's Davis says "infrastructure latency at T1 caused timeout retries, retries used a different prompt path"). The cross-platform agent is unbuilt.
- **Why it'd win the hackathon:** Tech Impl impossibility flex: dual-vendor observability stitched by an agent. Quality of Idea is fresh. Bindplane = brand new product to Dynatrace's portfolio, panel will love the early integration.
- **Demo arc (3 min):** Single Cloud Run agent. OTel from ADK → Bindplane → fan-out to both Phoenix (eval) + Dynatrace (infra). Demo: agent eval score drops in Phoenix; same trace in Dynatrace shows infra latency. Cross-platform agent reads both, concludes "eval drop was caused by infra latency, not model regression." Posts diagnosis.
- **What you'd actually have to build:** Bindplane router configured with two destinations + OneAgent → Grail + OpenInference → Phoenix Cloud + ADK agent that reads BOTH (Phoenix MCP for traces, Dynatrace MCP for DQL) and synthesizes.

---

### HIDDEN-dynatrace-04: World Cup streaming reliability agent (Devpost domain + Davis pre-emptive)

- **Sponsor capability:** Real-time DQL queries + `list_problems` + Davis Copilot + send_event back to Grail for audit.
- **What the sponsor hints at:** Our own partner-dynatrace.md Idea 3 calls this out; the Dynatrace hub explicitly lists "Vertex AI / Agent Platform" monitoring as a product.
- **Source:** [dynatrace.com/hub/detail/vertex-ai/](https://www.dynatrace.com/hub/detail/vertex-ai/).
- **Why nobody's built it:** Pre-emptive scaling for time-coupled events (matches, live streams) using AI agent + Davis is mentioned in 0 community projects on GitHub. The pre-emptive lever (scale BEFORE the goal, not after the spike) requires the agent to forecast traffic from the match clock — unbuilt.
- **Why it'd win the hackathon:** Devpost suggests World Cup domain explicitly; hits Quality of Idea high; demoable during judging window (June 22-July 6 overlaps with knockout rounds).
- **Demo arc (3 min):** Simulated streaming app deployed on Cloud Run. Match clock ticks; agent pre-scales 90 seconds before the 45-min mark (high-traffic). Davis Copilot narrates "predicting +30% traffic at T+90s based on historical match-traffic pattern." Live latency stays flat through the spike.
- **What you'd actually have to build:** Tiny Cloud Run "stream service" + load generator + OneAgent + ADK agent with DQL pre-emptive forecast + scale-up via Cloud Run revisions API.

---

### HIDDEN-dynatrace-05: Vulnerability remediation conductor (runtime-aware patching)

- **Sponsor capability:** `list_vulnerabilities` (runtime CVE detection, not just SBOM) + `execute_dql` (deployment correlation) + `create_workflow_for_notification`.
- **What the sponsor hints at:** Our own partner-dynatrace.md Idea 2 noted the runtime-vs-static-SBOM distinction; the Dynatrace docs emphasize that runtime detection knows which JARs/modules are actually loaded, not just what's in `package.json`.
- **Source:** [docs.dynatrace.com/docs/observe/application-security](https://docs.dynatrace.com/docs/observe/application-security).
- **Why nobody's built it:** Runtime vulnerability detection is a Dynatrace differentiator vs. Snyk/Dependabot (which only see manifest dependencies). No community agent leverages this to **autonomously open MRs that patch the affected service in code**. GitHub search returns the Dynatrace docs + a few Snyk integrations — no runtime-driven patcher.
- **Why it'd win the hackathon:** Crosses Dynatrace + GitLab MCP (could be entered as a Dynatrace track submission that also integrates GitLab MCP for the MR creation step — extra integration depth). Tech Impl is genuinely novel.
- **Demo arc (3 min):** Inject a known CVE into a running Cloud Run service (e.g., a vulnerable log4j-ish library). OneAgent detects runtime exposure. Agent reads `list_vulnerabilities`, cross-references the deployment, identifies the responsible repo + branch, opens a GitLab MR with the fix pre-applied. Engineer just reviews and merges.
- **What you'd actually have to build:** Vulnerable Cloud Run app (deliberately seeded) + ADK agent + Dynatrace MCP for vulnerability list + GitLab MCP (or REST) for MR creation + patch-generation prompt.

---

**Why this sponsor will judge favorably:** Sean O'Dell's "rise of the developer" thesis means he favors submissions where the AGENT enables a single developer to operate at SRE/security/ops scale — HIDDEN-dynatrace-01 (budget guardrail) and HIDDEN-dynatrace-05 (vuln remediation) both do this. Jeff Blankenburg's vibe-coding-meets-production background means he scores favorably on submissions that show a real, working deployed thing with real OTel data — every Dynatrace submission must have OneAgent reporting on a live Cloud Run service, not faked data. **The single Dynatrace submission that combines AI Coding Agent monitoring (the brand-new product) + an active intervention agent will have no competition in this bucket.**

---

# Cross-sponsor synthesis

**The shape that wins every track:** all 18 hidden use cases share a deep pattern — they all involve the agent _reading back its own (or some product's own) data_ and _acting on it_ in a loop, with the sponsor product as the data backbone. Not "agent calls tool" but "agent uses tool + tool's output to decide what tool to call next." Every panel is broadcasting "we want loops, not calls."

**Highest-leverage sponsor for our existing project (ChaosLab → Arize track):** HIDDEN-arize-01 is the closest match to our current spec. ChaosLab is fault-injection + Phoenix eval + closed-loop hardening — we're already building the right shape. The 5 Arize hidden use cases together describe a roadmap of what we could extend ChaosLab into post-hackathon.

**If we ever submit a second track:** HIDDEN-gitlab-01 (DORA coach) and HIDDEN-dynatrace-01 (budget guardrail) are tied for second-pick. Both are "act, not chat" and both speak to the judges' published positions. HIDDEN-mongodb-01 (write-time policy via vectorSearch) is the most novel single idea across all 6 sponsors but has the highest implementation risk because Stream Processing + auto-embed combined into one pipeline is an unbuilt path.

---

# Search log (verifying "nobody's built it")

For transparency: the absence claims above are based on these GitHub + DevPost + community searches conducted 2026-06-03. The standard not-built pattern: I searched the specific use-case shape (not the product alone) and confirmed only docs/blog hits, no built projects.

| Search                                                                             | Result                                                                                                                                                           |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `phoenix-mcp agent project example github`                                         | Returns `Arize-ai/phoenix` repo + `Arize-ai/gemini-hackathon` empty starter + `Arize-ai/text-to-graphql-mcp` (different product). No closed-loop agent.          |
| `"phoenix mcp" devpost hackathon project`                                          | Returns hackathon listings + Arize devpost page. No submitted projects in current galleries combining all primitives.                                            |
| `phoenix multi-judge ensemble human-in-loop github`                                | Returns research papers (Multi-Agent Debate arXiv 2510.12697) and PaperTrail. No Phoenix-built ensemble.                                                         |
| `elastic agent code review elasticsearch memory git diff ELSER`                    | Returns `elastic/agent-skills` repo (skill packages, not a code-review agent) + Search Labs blog (single-shot RAG). No persistent-memory cross-PR code reviewer. |
| `elastic inference service agent example github`                                   | Returns EIS docs + Search Labs blog only.                                                                                                                        |
| `elastic agent multi-tenant DLS memory`                                            | Returns the DLS docs + the memory blog. No multi-tenant agent.                                                                                                   |
| `a2a elasticsearch agent built example`                                            | Returns the Elastic A2A vs MCP blog + a2a-sdk repo. No combined demo.                                                                                            |
| `fivetran MCP agent data quality rules learn warehouse github`                     | Returns `fivetran/fivetran-mcp` + community toolkits + Speakeasy case study. No agent-curated quality rules.                                                     |
| `fivetran NL connector agent ADK gemini github`                                    | Returns `fivetran_csdk_tools` (skills for various IDE agents) + the Davis 30-min Cursor blog. No ADK + Gemini implementation.                                    |
| `fivetran schema drift impact predictor agent`                                     | Returns schema docs + drift detection blog. No agent that walks BQ DAG.                                                                                          |
| `gitlab agent dora coach team velocity cycle time`                                 | Returns DORA docs + 600-project hackathon winners list. None of the 600 winners is a DORA coach (verified by reading the winner names list).                     |
| `gitlab knowledge graph code archaeology agent github`                             | Returns Knowledge Graph docs + RepoWarden (specification engine, different direction). No archaeology agent.                                                     |
| `gitlab AI Catalog publish parameterized agent example`                            | Returns AI Catalog docs + Veenhof announcement blog. No third-party published agent demonstrating cross-project re-use.                                          |
| `gitlab world cup release conductor schedule-aware deploy agent`                   | Returns GitLab CI docs only. No agent.                                                                                                                           |
| `mongodb atlas stream processing $vectorSearch policy enforcement forbidden write` | Returns Stream Processing docs + Vector Search docs + external function blog. No built policy enforcement agent.                                                 |
| `mongodb $rankFusion agent hybrid github example`                                  | Returns the $rankFusion docs + the announcement blog. No built agent.                                                                                            |
| `mongodb TTL agent memory hygiene importance scoring`                              | Returns the LangGraph+MongoDB TTL blog. No built hygiene agent.                                                                                                  |
| `voyage-code-3 personal codebase agent github`                                     | Returns voyage-code-3 announcement + Voyage docs. No personal-archaeology agent.                                                                                 |
| `dynatrace AI coding agent budget guardrail kill session`                          | Returns the AI Coding Agent monitoring blog + `dynatrace-oss/dynatrace-ai-agent-instrumentation-examples`. No active guardrail agent.                            |
| `dynatrace bindplane phoenix grail two-track agent`                                | Returns the Bindplane acquisition blog + integration docs. No cross-platform agent.                                                                              |
| `dynatrace runtime vulnerability auto-patch MR github`                             | Returns vulnerability docs + Snyk integrations. No runtime-driven auto-patcher.                                                                                  |

All claims of "no one has built X" are scoped to this search method and these dates. A perfectly buried implementation in a low-star private fork would not be caught; the bar is "discoverable to a deliberate search in the agentic ecosystem."

---

# Sources (consolidated)

## Arize / Phoenix

- [arize.com/llm-as-a-judge](https://arize.com/llm-as-a-judge/)
- [arize.com/docs/phoenix/cookbook/prompt-engineering/llm-as-a-judge-prompt-optimization](https://arize.com/docs/phoenix/cookbook/prompt-engineering/llm-as-a-judge-prompt-optimization)
- [arize.com/docs/phoenix/cookbook/prompt-engineering/optimizing-coding-agent-prompts-prompt-learning](https://arize.com/docs/phoenix/cookbook/prompt-engineering/optimizing-coding-agent-prompts-prompt-learning)
- [arize.com/docs/phoenix/cookbook/annotations/using-human-annotations-for-eval-driven-development](https://arize.com/docs/phoenix/cookbook/annotations/using-human-annotations-for-eval-driven-development)
- [arize.com/docs/phoenix/tracing/how-to-tracing/feedback-and-annotations/capture-feedback](https://arize.com/docs/phoenix/tracing/how-to-tracing/feedback-and-annotations/capture-feedback)
- [arize.com/docs/phoenix/integrations/phoenix-mcp-server](https://arize.com/docs/phoenix/integrations/phoenix-mcp-server)
- [arize.com/docs/phoenix/prompt-engineering/tutorial](https://arize.com/docs/phoenix/prompt-engineering/tutorial)
- [github.com/Arize-ai/phoenix](https://github.com/Arize-ai/phoenix)
- [github.com/Arize-ai/phoenix/blob/main/js/packages/phoenix-mcp/README.md](https://github.com/Arize-ai/phoenix/blob/main/js/packages/phoenix-mcp/README.md)
- [github.com/Arize-ai/gemini-hackathon](https://github.com/Arize-ai/gemini-hackathon)
- [turingpost.com/p/arize1](https://www.turingpost.com/p/arize1) — "Building a Self-Improving Agent with Arize Phoenix and DSPy"
- [arize.com/blog/aws-bedrock-agentcore-observability-operationalizing-ai-agents-at-scale](https://arize.com/blog/aws-bedrock-agentcore-observability-operationalizing-ai-agents-at-scale/) — Richard Young authored
- [linkedin.com/in/riyoung](https://www.linkedin.com/in/riyoung/) — Richard Young profile / quote source

## Elastic

- [elastic.co/search-labs/blog/agent-builder-elastic-ga](https://www.elastic.co/search-labs/blog/agent-builder-elastic-ga)
- [elastic.co/search-labs/blog/agent-builder-mcp-reference-architecture-elasticsearch](https://www.elastic.co/search-labs/blog/agent-builder-mcp-reference-architecture-elasticsearch)
- [elastic.co/search-labs/blog/subagents-with-elastic-agent-builder](https://www.elastic.co/search-labs/blog/subagents-with-elastic-agent-builder)
- [elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch](https://www.elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch)
- [elastic.co/search-labs/blog/elastic-agent-builder-ai-agents-context-management](https://www.elastic.co/search-labs/blog/elastic-agent-builder-ai-agents-context-management)
- [elastic.co/search-labs/blog/agent-builder-one-workflow](https://www.elastic.co/search-labs/blog/agent-builder-one-workflow)
- [elastic.co/search-labs/blog/build-ai-agents-elastic-inference-service](https://www.elastic.co/search-labs/blog/build-ai-agents-elastic-inference-service)
- [elastic.co/search-labs/blog/a2a-protocol-mcp-llm-agent-newsroom-elasticsearch](https://www.elastic.co/search-labs/blog/a2a-protocol-mcp-llm-agent-newsroom-elasticsearch)
- [elastic.co/blog/elastic-workflows-technical-preview](https://www.elastic.co/blog/elastic-workflows-technical-preview)
- [elastic.co/elasticsearch/agent-builder](https://www.elastic.co/elasticsearch/agent-builder)
- [github.com/elastic/agent-skills](https://github.com/elastic/agent-skills)
- [x.com/xeraa](https://x.com/xeraa) — Philipp Krenn Twitter
- [xeraa.net](https://xeraa.net/) — Philipp Krenn personal site

## Fivetran

- [fivetran.com/blog/integrate-data-faster-using-natural-language-fivetran-and-mcp](https://www.fivetran.com/blog/integrate-data-faster-using-natural-language-fivetran-and-mcp)
- [fivetran.com/blog/how-data-access-shapes-ai-agent-performance](https://www.fivetran.com/blog/how-data-access-shapes-ai-agent-performance)
- [fivetran.com/blog/85-of-enterprises-are-running-agentic-ai-on-a-data-foundation-that-isnt-ready](https://www.fivetran.com/blog/85-of-enterprises-are-running-agentic-ai-on-a-data-foundation-that-isnt-ready)
- [fivetran.com/blog/how-fivetran-and-ai-turn-raw-data-into-operational-intelligence](https://www.fivetran.com/blog/how-fivetran-and-ai-turn-raw-data-into-operational-intelligence)
- [fivetran.com/learn/data-curation](https://www.fivetran.com/learn/data-curation)
- [github.com/fivetran/fivetran-mcp](https://github.com/fivetran/fivetran-mcp)
- [github.com/fivetran/fivetran_connector_sdk](https://github.com/fivetran/fivetran_connector_sdk)
- [github.com/fivetran/fivetran_csdk_tools](https://github.com/fivetran/fivetran_csdk_tools)
- [github.com/fivetran/api_framework](https://github.com/fivetran/api_framework)
- [speakeasy.com/customers/fivetran](https://www.speakeasy.com/customers/fivetran)
- [dbta.com — Davis 30-min connector blog](https://www.dbta.com/Editorial/Trends-and-Applications/Sponsored-Content-How-I-Built-a-Data-Connector-in-30-Minutes-with-AI-and-Why-You-Should-Try-it-at-the-AI-Accelerate-Unlocking-New-Frontiers-Hackathon-171572.aspx)
- [linkedin.com/in/andrew-madson](https://www.linkedin.com/in/andrew-madson/) — Andrew Madson profile / quote source

## GitLab

- [docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/)
- [docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/)
- [docs.gitlab.com/user/duo_agent_platform/](https://docs.gitlab.com/user/duo_agent_platform/)
- [docs.gitlab.com/user/duo_agent_platform/ai_catalog/](https://docs.gitlab.com/user/duo_agent_platform/ai_catalog/)
- [docs.gitlab.com/user/duo_agent_platform/flows/](https://docs.gitlab.com/user/duo_agent_platform/flows/)
- [docs.gitlab.com/user/duo_agent_platform/flows/custom/](https://docs.gitlab.com/user/duo_agent_platform/flows/custom/)
- [docs.gitlab.com/user/duo_agent_platform/agents/custom/](https://docs.gitlab.com/user/duo_agent_platform/agents/custom/)
- [docs.gitlab.com/user/project/repository/knowledge_graph/](https://docs.gitlab.com/user/project/repository/knowledge_graph/)
- [docs.gitlab.com/user/gitlab_duo/semantic_code_search/](https://docs.gitlab.com/user/gitlab_duo/semantic_code_search/)
- [docs.gitlab.com/user/analytics/dora_metrics/](https://docs.gitlab.com/user/analytics/dora_metrics/)
- [about.gitlab.com/blog/duo-agent-platform-with-mcp/](https://about.gitlab.com/blog/duo-agent-platform-with-mcp/)
- [about.gitlab.com/blog/ai-catalog-discover-and-share-agents/](https://about.gitlab.com/blog/ai-catalog-discover-and-share-agents/)
- [about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/](https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/)
- [about.gitlab.com/blog/gitlab-and-vertex-ai-on-google-cloud/](https://about.gitlab.com/blog/gitlab-and-vertex-ai-on-google-cloud/) — Regnard Raquedan co-authored
- [gitlab.com/nick_vh](https://gitlab.com/nick_vh) — Nick Veenhof profile

## MongoDB

- [mongodb.com/docs/mcp-server/tools/](https://www.mongodb.com/docs/mcp-server/tools/)
- [mongodb.com/docs/atlas/atlas-vector-search/ai-agents/](https://www.mongodb.com/docs/atlas/atlas-vector-search/ai-agents/)
- [mongodb.com/docs/atlas/atlas-stream-processing/overview/](https://www.mongodb.com/docs/atlas/atlas-stream-processing/overview/)
- [mongodb.com/docs/manual/reference/operator/aggregation/rankfusion/](https://www.mongodb.com/docs/manual/reference/operator/aggregation/rankfusion/)
- [mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/](https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/)
- [mongodb.com/docs/voyageai/models/](https://www.mongodb.com/docs/voyageai/models/)
- [mongodb.com/company/blog/product-release-announcements/unlocking-ai-search-introducing-automated-embedding-in-mongodb-vector-search](https://www.mongodb.com/company/blog/product-release-announcements/unlocking-ai-search-introducing-automated-embedding-in-mongodb-vector-search)
- [mongodb.com/company/blog/technical/harness-power-atlas-search-vector-search-with-rankfusion](https://www.mongodb.com/company/blog/technical/harness-power-atlas-search-vector-search-with-rankfusion)
- [mongodb.com/company/blog/voyage-code-3-more-accurate-code-retrieval-lower-dimensional-quantized-embeddings](https://www.mongodb.com/company/blog/voyage-code-3-more-accurate-code-retrieval-lower-dimensional-quantized-embeddings)
- [mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph](https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph)
- [mongodb.com/company/blog/innovation/building-next-gen-ai-agents-mongodb-atlas-integration-microsoft-foundry](https://www.mongodb.com/company/blog/innovation/building-next-gen-ai-agents-mongodb-atlas-integration-microsoft-foundry)
- [mongodb.com/company/blog/new-mongodb-atlas-stream-processing-external-function-support](https://www.mongodb.com/company/blog/new-mongodb-atlas-stream-processing-external-function-support)
- [mongodb.com/blog/authors/gaurab-aryal](https://www.mongodb.com/blog/authors/gaurab-aryal) — Gaurab Aryal author page

## Dynatrace

- [dynatrace.com/news/blog/dynatrace-expands-ai-coding-agent-monitoring/](https://www.dynatrace.com/news/blog/dynatrace-expands-ai-coding-agent-monitoring/)
- [github.com/dynatrace-oss/dynatrace-ai-agent-instrumentation-examples](https://github.com/dynatrace-oss/dynatrace-ai-agent-instrumentation-examples)
- [dynatrace.com/news/blog/transform-your-operations-with-davis-ai-root-cause-analysis/](https://www.dynatrace.com/news/blog/transform-your-operations-with-davis-ai-root-cause-analysis/)
- [dynatrace.com/news/blog/hypermodal-ai-dynatrace-expands-davis-ai-with-davis-copilot/](https://www.dynatrace.com/news/blog/hypermodal-ai-dynatrace-expands-davis-ai-with-davis-copilot/)
- [dynatrace.com/news/blog/dynatrace-to-acquire-bindplane-telemetry-pipeline/](https://www.dynatrace.com/news/blog/dynatrace-to-acquire-bindplane-telemetry-pipeline/)
- [dynatrace.com/hub/detail/vertex-ai/](https://www.dynatrace.com/hub/detail/vertex-ai/)
- [dynatrace.com/hub/detail/query-agent/](https://www.dynatrace.com/hub/detail/query-agent/)
- [docs.dynatrace.com/docs/dynatrace-intelligence/copilot/quick-analysis-copilot-dql](https://docs.dynatrace.com/docs/dynatrace-intelligence/copilot/quick-analysis-copilot-dql)
- [github.com/dynatrace-oss/dynatrace-mcp](https://github.com/dynatrace-oss/dynatrace-mcp)
- [bindplane.com/google](https://bindplane.com/google)
- [dynatrace.com/news/blog/author/sean-odell/](https://www.dynatrace.com/news/blog/author/sean-odell/) — Sean O'Dell blog
- [dynatrace.com/news/blog/author/jeff-blankenburg/](https://www.dynatrace.com/news/blog/author/jeff-blankenburg/) — Jeff Blankenburg blog
- [dynatrace.com/news/blog/10-things-i-learned-writing-49000-words-about-vibe-coding/](https://www.dynatrace.com/news/blog/10-things-i-learned-writing-49000-words-about-vibe-coding/) — Blankenburg vibe-coding post
- [jeffblankenburg.info](https://jeffblankenburg.info/) — Jeff Blankenburg personal site
- [thenewstack.io/dynatrace-perform-rise-of-the-developer/](https://thenewstack.io/dynatrace-perform-rise-of-the-developer/) — Sean O'Dell rise-of-developer interview
