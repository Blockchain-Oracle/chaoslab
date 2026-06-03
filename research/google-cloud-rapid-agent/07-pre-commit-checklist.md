# 07 — Pre-Commit Checklist

**The questions Abu must answer on paper before writing a single line of agent code.** If any question doesn't have a sharp answer, stop and re-research — do not start building.

This is the gate that prevents the "I built it but realized too late it doesn't fit the track / doesn't satisfy a judging criterion / can't be demoed in 3 minutes" failure mode.

---

## Q1: Which track am I entering, and why this one?

**The answer must include:**

- The track name
- The lane-EV reason (from `06-hidden-field.md`)
- The personal-fit reason (skills, time budget, what you actually find interesting)
- One sentence on what the partner's MCP server uniquely enables for your wedge

**For Abu (recommendation):** Arize.

Why:

- Lane-EV: predicted GREEN (least crowded), ~3× the structural win-odds of MongoDB/GitLab at the same $10K bucket payout (`06-hidden-field.md`).
- Personal fit: Abu already uses AI agent coding tools daily. The recursive "agent that observes/grades agents" angle is genuine, not contrived. Phoenix MCP lets the _built_ agent read back its own traces, run evals on past runs, and propose its own improvements.
- No trial clock: Phoenix Cloud is free and stays free past judging.
- Unique enable: Phoenix MCP exposes traces, prompts, datasets, experiments. No other partner gives the agent the ability to introspect its _own_ execution.

Backup if Arize feels too cerebral after deep-reading `partner-arize.md`: **Fivetran**. Best mental-model match to multi-chain indexers; cleanest "before/after" demo arc. Pay the trial-squeeze tax.

---

## Q2: What's the ONE concrete problem the agent solves?

Not "an agent for finance" — that's a domain. The problem must fit this format:

> A **[specific user role]** doing **[specific task]** today wastes time on **[specific bottleneck]** because **[specific reason]**. My agent eliminates that bottleneck by **[specific autonomous action]**.

**Why this matters:** Winning patterns from `05-prior-winners.md` are universally **hyper-specific domain × multi-step autonomous workflow**. Generic chat-with-data loses. "An agent that emails me a daily summary of new BUIDLs at ETHGlobal that match my technical interests" wins. Specificity is the moat.

**Abu must write the answer in his own words** before building. Examples for an Arize-track agent:

- _"A solo hackathon dev shipping under deadline pressure wastes 4+ hours debugging why their LLM agent went off the rails. My agent ingests Phoenix traces from a target agent, identifies prompt or tool-call failures, proposes a fix as a diff, and runs an A/B eval comparing old vs new prompt on a regression set — all autonomously."_
- _"An ML platform team debugging a customer-facing chatbot can't tell whether degradation is from prompt drift or context-window pollution. My agent ingests Phoenix traces, runs a structured eval, hypothesizes the root cause class, and writes a Slack-postable incident report with a recommended action."_

---

## Q3: What does the agent DO that's not just retrieval?

The Devpost rules text says explicitly: _"Move Beyond Chat: Your agent shouldn't just answer questions. It should use tools and capabilities to accomplish tasks."_

The agent must take **at least one consequential action** that touches a real system. Acceptable:

- Writes a row to a real database
- Creates a real GitHub issue or MR
- Sends a real email/Slack message
- Runs a real Phoenix evaluation experiment
- Updates a real Fivetran connector schema
- Posts a real GitLab MR comment

Not enough on its own: search → respond. Q&A. Show-me-results.

**For an Arize-track build:** the agent runs a real Phoenix experiment, writes a real evaluation dataset, or pushes a real prompt diff into a versioned prompt store.

---

## Q4: What partner MCP tools will the agent call, by name?

Pull the actual MCP tool list from the partner file (`partner-arize.md`, etc.) and write down which tools your agent will invoke.

Why: judges scoring "Technological Implementation" want to see _which_ tools you used and _why_. A submission that calls 1 MCP tool out of the 15-100+ available is a "Stage 2 mediocre" signal.

**Aim for 3-5 distinct MCP tools** used in a single agent run. That's enough to demonstrate "real integration" and not so much that it gets messy.

**For Arize/Phoenix MCP**, plausible 4-tool set:

1. `phoenix_get_traces` (read recent traces from a target project)
2. `phoenix_get_prompts` (read versioned prompts)
3. `phoenix_create_dataset` (assemble an eval dataset)
4. `phoenix_run_experiment` (kick off a real eval)

---

## Q5: What's the demo URL, and what does a judge SEE in the first 30 seconds?

Judges land on your hosted URL with no context. The first 30 seconds determine whether they keep scrolling or scoring you a 5/10 and moving on.

**The demo URL must:**

- Load without a login wall
- Have one obvious "start the agent" action
- Pre-load sample data so the agent has something to act on
- Complete a full multi-step run in under 90 seconds (otherwise the judge times out)

**For Abu:** the hosted URL likely lives on **Cloud Run** (a tiny static frontend + the ADK agent on Agent Runtime). See `02a-google-cloud-stack.md` §10 for deployment paths. Default plan: Streamlit-on-Cloud-Run for fastest demo-grade UI; switch to a real React frontend only if time permits.

---

## Q6: What's the 3-minute video story?

The video is the **judging insurance** when trials expire mid-judging window (Section 8). It MUST exist and MUST clearly show the agent acting end-to-end. From `05-prior-winners.md`, winning videos universally:

1. Open with the problem in 15 seconds (the user role, the pain)
2. Show the agent ACTING (not the founder narrating)
3. Show the partner's unique value (what makes this an Arize agent and not a generic one)
4. Close with a measured outcome ("agent reduced root-cause-time from 4 hours to 90 seconds")

**Script the video before you build.** If you can't write a 3-minute script of what the agent does, the agent isn't well-defined yet — go back to Q2.

---

## Q7: What's the most likely thing that kills this submission?

Honest answer required. From the prior-winner and per-track gotcha analysis, the top risks per track:

| Track         | Most likely killer                                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Arize**     | Using Phoenix only as a dashboard (no real eval loop). Auto-fail.                                                |
| **Elastic**   | Cluster expires before judges hit your demo URL (video saves you only if it's good).                             |
| **Fivetran**  | Static demo; ingestion isn't actually live during the agent run.                                                 |
| **GitLab**    | Using a community MCP server instead of official `gitlab.com/api/v4/mcp`.                                        |
| **MongoDB**   | Using Atlas as a dumb K/V store; no `$vectorSearch` query in the agent.                                          |
| **Dynatrace** | Mock telemetry instead of real OneAgent collection.                                                              |
| **All**       | Banned dependency (`anthropic`, `openai`, `langchain` as primary, etc.) detected by Stage-1 automated repo scan. |

**For an Arize build, the killer is "Phoenix-as-dashboard."** Mitigation: the agent must do AT LEAST one round of: read trace → form hypothesis → write eval dataset → run experiment → write report. Not just "look at traces."

---

## The completed Q1-Q7 set for Abu (draft — fill in his actual choices)

| #   | Question             | Abu's answer (DRAFT — Abu must confirm/edit)                                                    |
| --- | -------------------- | ----------------------------------------------------------------------------------------------- |
| Q1  | Track                | **Arize** — predicted GREEN saturation, recursive angle, no trial clock                         |
| Q2  | Concrete problem     | _(TBD — Abu must write)_                                                                        |
| Q3  | Consequential action | Run a real Phoenix experiment with new prompt vs baseline                                       |
| Q4  | MCP tools            | `phoenix_get_traces`, `phoenix_get_prompts`, `phoenix_create_dataset`, `phoenix_run_experiment` |
| Q5  | Demo URL plan        | Streamlit + ADK on Cloud Run, no-login sandbox with pre-loaded sample traces                    |
| Q6  | Video story          | Pain (15s) → agent acts (90s) → measured outcome (45s) → call to action (30s)                   |
| Q7  | Most likely killer   | "Phoenix as dashboard" — mitigate by enforcing real eval-loop in the agent path                 |

Abu fills in Q2 with his wedge sentence, confirms Q1, and gates the rest on that.

---

## Hard rule

**Do not start writing code until Q1-Q7 each have a sharp answer.** If Q2 isn't sharp, the rest cascade. The 9-day deadline does NOT excuse skipping this — every hour spent here saves 5 hours of rebuild later.
