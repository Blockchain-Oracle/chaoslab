# Partner Track: Arize (Phoenix)

Hackathon: Google Cloud Rapid Agent Hackathon — https://rapid-agent.devpost.com/
Deadline: June 11, 2026 @ 2:00pm PDT. Judging: June 22 – July 6, 2026.
Prize per partner bucket: 1st $5,000 / 2nd $3,000 / 3rd $2,000.

---

## What the product actually is

**Arize Phoenix** is an open-source LLM observability + evaluation platform. In plain English: it's the "Datadog + Sentry + Postman" for an LLM agent. Once you instrument your agent with OpenTelemetry, every agent invocation, every Gemini call, every tool call, and every MCP round-trip gets recorded as a **span**. You see a tree of what your agent did, what it thought, what tools it picked, what tokens it burned, what it returned, and where it broke. Then you run **evals** (LLM-as-a-judge or code) over those traces to grade behavior and catch regressions. ([phoenix](https://arize.com/phoenix/), [adk docs](https://google.github.io/adk-docs/integrations/phoenix/))

For a blockchain dev, the closest analogy is a **Tenderly + Foundry trace + on-chain monitor combo**, but for a non-deterministic LLM agent instead of an EVM transaction. Tenderly shows you the call tree of a tx; Phoenix shows you the call tree of an agent run. Foundry's `forge test` + invariants becomes Phoenix **experiments + evals** — you run an agent against a dataset of inputs and grade outputs against a rubric. Tenderly alerts become Phoenix annotations + monitors. The mental model "instrument once, replay forever, grade everything" is the same.

Arize ships two products: **Phoenix** (the open-source one — Apache 2.0 on GitHub, free SaaS at app.phoenix.arize.com, or self-host via Docker/pip) and **Arize AX** (the paid enterprise tier with more eval ops + monitoring). For this hackathon, Phoenix is the relevant surface. The track is uniquely **non-data-bringing**: unlike Elastic/Fivetran where you have to wrangle a data source, with Arize the _agent's own trace data IS the data_. You generate it the second you run the agent. ([arize phoenix docs](https://arize.com/docs/phoenix/integrations/frameworks-and-platforms/model-context-protocol/phoenix-mcp-server))

## Core product surface

Phoenix is genuinely best at these 5 things:

1. **OpenTelemetry-based agent tracing.** Auto-instrumentation libraries (`openinference-instrumentation-*`) for 30+ frameworks: Google ADK, Vertex/Gemini, OpenAI, LangChain, LlamaIndex, CrewAI, LangGraph, MCP itself. One `register()` call and your spans stream to Phoenix. ([phoenix github](https://github.com/Arize-ai/phoenix))
2. **LLM-as-a-judge evaluations.** Replay traces, score them with a judge LLM against a rubric (correctness, hallucination, toxicity, tool-call accuracy, RAG groundedness), attach the score back to the span.
3. **Datasets + experiments.** Versioned golden datasets of inputs/expected outputs. Run any agent variant against a dataset, get a side-by-side diff: "v1 had 78% hallucination-free, v2 has 91%." This is the LLM equivalent of a regression test suite.
4. **Prompt management.** Versioned prompt templates with tags (`prod`, `staging`, `latest`), invocation params per version, side-by-side replay in the Playground. The prompt becomes a first-class artifact, not a string in code.
5. **Annotation + feedback loop.** Annotate spans with labels/scores (human or LLM), feed those annotations back into datasets, retrain prompts/agents. This is the "self-improvement loop" the track explicitly rewards.

## Their MCP server

**Name:** `@arizeai/phoenix-mcp` (TypeScript, runs via `npx`). There is also `openinference-instrumentation-mcp` (Python) but that one is the _tracer_ for MCP traffic, not an MCP server itself. ([phoenix mcp docs](https://arize.com/docs/phoenix/sdk-api-reference/typescript/mcp-server), [pulse mcp](https://www.pulsemcp.com/servers/arize-phoenix))

**Install (any MCP client — Gemini CLI, Claude Desktop, Cursor):**

```bash
npx -y @arizeai/phoenix-mcp@latest \
  --baseUrl https://app.phoenix.arize.com \
  --apiKey $PHOENIX_API_KEY
```

For ADK / a custom code-first runtime, you wire `@arizeai/phoenix-mcp` in as a tool source alongside whatever other MCP servers you use. The track explicitly says the MCP server "runs via npx and drops into any MCP client config — including Gemini CLI's settings.json." ([arize-resources](https://rapid-agent.devpost.com/details/arize-resources))

**Tools the MCP server exposes** (i.e. what a Gemini agent can DO via this MCP server — quoted/paraphrased from the Phoenix MCP docs):

- **Projects/Traces/Spans** — list recent traces, fetch a specific span, inspect span attributes and annotations, query spans by filter. The agent can ask "what did my last agent run look like" and read its own history.
- **Sessions** — review conversation flows and session-level annotations across multi-turn runs.
- **Annotation configs** — inspect labeling/scoring configs in Phoenix.
- **Prompts** — create, list, update, fetch prompt versions (by ID, tag, or "latest"). Manage tags. The agent can self-modify its own prompt versions.
- **Datasets** — list datasets, retrieve examples, add synthetic examples for edge cases.
- **Experiments** — list and retrieve experiment results, metadata, outputs, annotations.

The "bonus points" hint in the partner-resources page is explicit: **agents that use their own observability data to improve over time get bonus consideration.** That's the loop: agent runs → traces → eval → judge spots failure pattern → agent reads traces back via MCP → updates its own prompt or dataset → re-runs. ([arize-resources](https://rapid-agent.devpost.com/details/arize-resources))

## Free tier / trial details + gotchas

- **Phoenix Cloud (SaaS):** free tier at https://app.phoenix.arize.com — no trial clock, just signup → API key → trace. Hosted by Arize. ([phoenix](https://arize.com/phoenix/))
- **Self-host:** Apache 2.0 from https://github.com/Arize-ai/phoenix. `pip install arize-phoenix` and run locally, or Docker. Free forever, your machine, your data.
- **No trial expiry to worry about** — unlike Elastic/Fivetran, Phoenix's free tier doesn't go dark mid-hackathon. This is the single biggest scheduling advantage of the Arize track.

**Hackathon-specific gotchas (verified from arize-resources page):**

1. **Code-first runtime is MANDATORY.** Quote: _"Gemini CLI, Gemini Enterprise Agent Platform SDK, Google ADK, Agent Runtime, or Cloud Run. The visual Agent Builder alone is not supported."_ If you build entirely in the Agent Builder visual canvas with no code surface, you cannot instrument with OpenInference, and you cannot win this track. ADK + Cloud Run is the canonical shape.
2. **You must actually instrument** with OpenInference auto-instrumentors (ADK, Google GenAI, LangChain, LlamaIndex, etc.). A pretty dashboard with no live spans is auto-rejection territory (see Risks section).
3. **You must run evals.** "LLM-as-a-Judge or code evals to demonstrate quality." A trace dump is not enough — there has to be a scoring/judging step.
4. **Self-improvement loop = bonus.** Agents that read back their own traces via the MCP server and adapt rank higher.
5. **Vertex AI Agent Engine quirk:** if you deploy to remote Agent Engine, the `register()` + instrumentor setup must live _inside the remote agent module_, not in your local driver script. Local instrumentation does not propagate. ([arize ax google-adk tracing](https://arize.com/docs/ax/integrations/python-agent-frameworks/google-adk/google-adk-tracing))

## What problems this partner is set up to solve well

Three problem shapes where Arize naturally wins:

1. **Self-debugging / self-improving agents.** The agent reads its own failed traces (via Phoenix MCP), notices a pattern ("tool X returned 404 in 40% of runs because I'm passing the wrong schema"), and patches its own prompt or skips that tool. This is the strongest track-fit and the one explicitly bonused.
2. **Eval-driven multi-variant agents.** Two prompt variants, one dataset, Phoenix runs the experiment, picks the winner, ships it. Treats agent dev like A/B testing.
3. **Regulated/high-cost domains where wrongness is expensive.** Financial advice, healthcare triage, retail pricing decisions. The eval loop is the value prop: you can _prove_ an agent doesn't hallucinate at rate >X% on a 500-example golden set. Demo this clearly and judges see "this is shippable" rather than "this is a toy."

## Concrete agent ideas that fit this partner

Each idea must use Phoenix MCP + Gemini + ADK/Cloud Run. Domains: 2026 World Cup, Financial Services, Brick-and-Mortar Retail (Devpost suggestions), or any other real domain.

### Idea 1 — "RegressionGuard" for World Cup match-commentary agents

_Problem:_ A live World Cup commentary agent hallucinates player stats during high-traffic matches.
_Why Arize wins this:_ Phoenix's dataset+experiment loop lets the agent self-grade every commentary span against a ground-truth match-stats dataset, and the agent uses the Phoenix MCP `experiments` tool to compare prompt variants live.
_Tools the agent calls:_ Phoenix MCP `list_traces`, `get_span`, `add_dataset_example`, `run_experiment`, plus a stats tool (BigQuery or a stats API).
_Judging fit:_ Technological Implementation (full eval loop), Potential Impact (live broadcast use case), Quality of Idea (self-improving commentary).

### Idea 2 — "ComplianceCanary" for retail-bank chat agents

_Problem:_ A retail bank's customer-support agent occasionally gives unauthorized financial advice. Compliance can't review every transcript.
_Why Arize wins this:_ Phoenix LLM-as-a-judge runs a "regulatory-violation" eval on every trace span; the agent reads back violation patterns via MCP and self-routes risky queries to a human.
_Tools the agent calls:_ Phoenix MCP `list_spans` (filter: low judge-score), `get_annotation_configs`, `update_prompt` (escalation prompt version).
_Judging fit:_ Potential Impact (compliance is a wedge), Design (clear escalation UX), Technological Implementation (judge + self-modify loop).

### Idea 3 — "StoreOps Postmortem" for brick-and-mortar retail

_Problem:_ A store-operations agent makes wrong recommendations (over-order, under-staff). Manager can't tell why post-hoc.
_Why Arize wins this:_ The agent's traces ARE the postmortem. The manager UI queries Phoenix MCP for "what did the agent think on Tuesday at 3pm" — every reasoning step, every tool call, every input.
_Tools the agent calls:_ Phoenix MCP `list_sessions`, `get_session_spans`, `add_annotation`. Plus retail tools (sales API, inventory).
_Judging fit:_ Design (manager UX is the differentiator), Technological Implementation (annotated session replay).

### Idea 4 — "PromptOps for a financial-research agent"

_Problem:_ Financial-research agent has 12 prompt variants across analysts. Nobody knows which is best for which sector.
_Why Arize wins this:_ Phoenix's prompt management is the core surface. Agent uses Phoenix MCP to route incoming queries to the prompt variant that scored best on that sector's eval dataset.
_Tools the agent calls:_ Phoenix MCP `list_prompts`, `get_prompt_by_tag`, `list_experiments`. Plus a market-data tool.
_Judging fit:_ Quality of Idea (PromptOps is a fresh angle), Technological Implementation (data-driven prompt routing).

### Idea 5 — "Hallucination-aware World Cup ticket scalper"

_Problem:_ An agent that buys/sells secondary-market World Cup tickets hallucinates seat availability and loses money.
_Why Arize wins this:_ Every agent action wrapped in a span with a `groundedness` eval; if score <0.8, agent refuses to commit. Phoenix MCP feeds the running hallucination rate back to the agent.
_Tools the agent calls:_ Phoenix MCP `get_recent_traces`, `get_span_evals`. Plus a ticketing API and a stripe-stub for transactions.
_Judging fit:_ Technological Implementation (groundedness-gated actions), Potential Impact (real money on the line).

### Idea 6 — "Self-Healing Multi-Agent Coordinator"

_Problem:_ A multi-agent system (planner + 4 specialist agents) silently drifts when one specialist regresses.
_Why Arize wins this:_ The planner agent introspects Phoenix MCP every N runs to find which specialist's traces are scoring worst this week, then dynamically rebalances routing weights toward better specialists.
_Tools the agent calls:_ Phoenix MCP `list_spans` (filter by `agent.name`), `list_experiments`, `add_dataset_example`. Plus whatever specialist tools (search, calc, code-exec).
_Judging fit:_ Quality of Idea (genuine self-healing), Technological Implementation (closes the loop the track explicitly bonuses).

## Track-specific judging risks (things that kill a submission)

1. **Phoenix used as a dashboard only, not an eval loop.** If your video shows "look at my pretty traces" and nothing else, judges will pass. The track explicitly weighs "meaningful use of tracing AND MCP" + "self-improvement loop." No eval = no win.
2. **No actual instrumentation.** Sending fake/static traces (e.g., a JSON dump) instead of live OpenInference auto-instrumented spans is detectable from the trace shape and instantly disqualifies.
3. **Visual Agent Builder only, no code surface.** Stated risk in the partner page — visual-only builds _cannot_ be instrumented, _cannot_ generate OpenInference traces, _cannot_ satisfy the track. Use ADK or Cloud Run.
4. **No use of the Phoenix MCP server.** Tracing alone is necessary but not sufficient. The agent has to _call_ Phoenix MCP tools at runtime — that's what makes it agentic vs. just observable.
5. **Hallucinated MCP integration** (claiming the agent uses Phoenix MCP but never actually calling its tools in the demo video). Easy to spot; auto-fail.

## Verified facts table

| Fact                          | Value                                                                                                        | Source                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Phoenix open-source license   | Apache 2.0                                                                                                   | github.com/Arize-ai/phoenix                                                          |
| Phoenix Cloud free tier       | Yes, no expiry                                                                                               | arize.com/phoenix                                                                    |
| Self-host option              | Yes (`pip install arize-phoenix`, Docker)                                                                    | github.com/Arize-ai/phoenix                                                          |
| MCP server package            | `@arizeai/phoenix-mcp` (npx)                                                                                 | arize.com/docs/phoenix/sdk-api-reference/typescript/mcp-server                       |
| MCP server status             | Production (active, maintained)                                                                              | github.com/Arize-ai/phoenix                                                          |
| SDK languages                 | Python (primary), TypeScript, Java (LangChain4j, Spring AI)                                                  | github.com/Arize-ai/phoenix                                                          |
| Code orchestrator requirement | ADK / Agent Platform SDK / Agent Runtime / Cloud Run / Gemini CLI. Visual Agent Builder alone NOT supported. | rapid-agent.devpost.com/details/arize-resources                                      |
| Auto-instrumentor for ADK     | `openinference-instrumentation-google-adk`                                                                   | arize.com/docs/ax/integrations/python-agent-frameworks/google-adk/google-adk-tracing |
| Demo video                    | ≤3 minutes, English, public link required                                                                    | rapid-agent.devpost.com/rules                                                        |
| Eval requirement              | Yes — LLM-as-a-judge OR code evals                                                                           | rapid-agent.devpost.com/details/arize-resources                                      |
| Self-improvement loop         | Bonus consideration (explicit)                                                                               | rapid-agent.devpost.com/details/arize-resources                                      |
| Judging period                | June 22 – July 6, 2026                                                                                       | rapid-agent.devpost.com/rules                                                        |

## Opinion: Arize is the easiest of the three for a blockchain-native solo dev

Three reasons:

1. **No trial clock.** Phoenix Cloud is free forever. You can build June 1, demo June 30, redo it July 5 — no email-swap workaround needed. Compare to Elastic and Fivetran where the 14-day trial determines your entire timeline.
2. **No external data to wrangle.** Elastic needs documents indexed; Fivetran needs SaaS sources connected. Arize's data is the agent's own traces — generated for free the moment the agent runs.
3. **Closest analog to what a Solidity dev already does.** Spans = transaction call trees. Datasets = invariant tests. Judge LLM = differential fuzzer. The mental model maps cleanly.

The catch: the track's "meaningful use of tracing AND MCP AND eval loop" bar is genuinely high. A blockchain dev not used to LLM eval loops will need to spend day 1-2 internalizing what makes a good eval rubric. But the infra is the easy part, and demoability is high.

## Sources

- Hackathon overview: https://rapid-agent.devpost.com/
- Hackathon rules: https://rapid-agent.devpost.com/rules
- Hackathon resources: https://rapid-agent.devpost.com/resources
- Arize partner page: https://rapid-agent.devpost.com/details/arize-resources
- Phoenix landing: https://arize.com/phoenix/
- Phoenix GitHub: https://github.com/Arize-ai/phoenix
- Phoenix MCP server reference: https://arize.com/docs/phoenix/sdk-api-reference/typescript/mcp-server
- Phoenix MCP server overview: https://arize.com/docs/phoenix/integrations/phoenix-mcp-server
- Phoenix MCP for Google ADK tracing: https://arize.com/docs/ax/integrations/python-agent-frameworks/google-adk/google-adk-tracing
- ADK Phoenix integration doc: https://google.github.io/adk-docs/integrations/phoenix/
- MCP tracing reference: https://arize.com/docs/ax/integrations/python-agent-frameworks/model-context-protocol/mcp-tracing
- Phoenix MCP on Pulse MCP: https://www.pulsemcp.com/servers/arize-phoenix
