# Reading Order — For Any Downstream Agent

> If you are an agent picking up this research folder (`sahil-spec-writer`, a coding agent, `sahil-hackathon-orchestrator`, or any fresh-context worker), **read in this order**. Each step builds on the previous.

---

## Phase 0 — Orient yourself (5 minutes)

1. **`CONTEXT.md`** — master entrypoint. What this hackathon is, what's locked (W1 ChaosLab, Arize track), what dates matter, what files exist. This is your "you are here" map.
2. **`00-overview.md`** — human-readable one-pager. Skim only.

After Phase 0 you should know: the hackathon, the locked wedge (ChaosLab for Agents), the deadline (2026-06-11), and the folder structure.

---

## Phase 1 — The wedge: what we're building (10 minutes)

3. **`brainstorm/06-idea-rankings.md` §W1** — the full ChaosLab pitch with multiplicative-floor scoring rationale, 3-min demo arc draft, RAT
4. **`brainstorm/07-novelty-gate.md`** — why this isn't a duplicate (0.062 top match in 17,000+ project corpus); the 4-source convergence signal

After Phase 1 you should be able to state the wedge in one sentence and explain WHY it scored 80th percentile.

---

## Phase 2 — The domain knowledge (deep — 1-2 hours of agent time)

The `context/` folder is where you spend most of your reading time. **Pure factual corpus with no opinions** — designed for you to make architectural decisions yourself.

5. **`context/00-README.md`** — table of contents and cross-cutting threads
6. **`context/01-agent-shapes-taxonomy.md`** — the universe of agents ChaosLab might target
7. **`context/04-cross-framework-instrumentation.md`** — how to instrument each framework
8. **`context/05-agent-interfaces-fingerprinting.md`** — how ChaosLab accepts an unknown agent
9. **`context/03-redteam-products-deep.md`** — competitive landscape + market gaps
10. **`context/02-production-failures.md`** — ground the fault-class catalog in reality
11. **`context/06-open-standards.md`** — spec-level reference for MCP/A2A/OpenInference/OWASP/MITRE

After Phase 2 you should know: the variety of agents that exist, how to instrument them, what existing red-team products do (and don't), what real failures look like, and the standards landscape.

---

## Phase 3 — The technical specifics (45 minutes)

These files cover the Google Cloud + Phoenix-specific implementation surface. Now you have enough domain context to absorb them properly.

12. **`02a-google-cloud-stack.md`** — ADK + Cloud Run + Agent Runtime + Gemini code patterns
13. **`02b-gemini-enterprise-agent-platform.md`** — Agent Platform component map (Build/Scale/Govern/Optimize)
14. **`partner-arize.md`** — Phoenix MCP partner integration details
15. **`mcp-primer.md`** — MCP protocol overview (lighter than `context/06`)

After Phase 3 you know the Google + Arize implementation primitives.

**Phase 3 addenda (added 2026-06-03 — Devpost-completeness audit):**

15a. **`refs/devpost-content-verbatim-2026-06-03.md`** — canonical Devpost content (sponsor sections + rules summary) Abu pasted in full. Anchor for every URL/resource our research should cover.
15b. **`refs/official-rules-verbatim.md`** — full 24-section rules text + per-section ChaosLab compliance checklist + 4 disqualification risks (AI-usage limitation is highest).
15c. **`refs/arize-gemini-hackathon-quickstart.md`** — deep dive on `github.com/Arize-ai/gemini-hackathon` (the official Arize-track quickstart). Quickstart proves trace pipeline only — ChaosLab's 4 fault classes + self-improvement loop + cross-framework targets are genuinely differentiated. Lists 3 pattern conflicts (model ID, ADK pin, mock target) where we hold our spec firm.
15d. **`refs/openinference-google-matrix.md`** — full 3-instrumentor matrix (`adk` 0.1.15 / `vertexai` 0.1.16 / `google-genai` 1.0.2 — PyPI-verified). Decision tree per target framework. Audit findings A6/A7 reverified (`openinference.span.kind` + `tool_call.function.name` canonical).
15e. **`refs/partner-resource-completeness-audit.md`** — cross-track audit of every Devpost-listed resource against our `partner-*.md` files. Each partner file received an appended "Devpost-listed resources (audit 2026-06-03)" section.

---

## Phase 3.5 — Best practices (factual reference — 30 minutes)

The `best-practices/` folder is **pure factual reference** for the implementation surface: how production teams set up Python projects, CI/CD, code quality, Next.js, BDD stories, and tests in 2026. Read in this order:

13a. **`best-practices/00-README.md`** — folder reading guide + cross-cutting decisions surfaced
13b. **`best-practices/01-python-project-layout.md`** — uv + ruff + ty (Astral monoculture), agent-starter-pack canonical layout, `pyproject.toml` template
13c. **`best-practices/02-cicd-github-actions.md`** — 4 paste-ready workflows, Workload Identity Federation, "build once promote everywhere"
13d. **`best-practices/03-code-quality-enforcement.md`** — 400-line enforcement script, ruff/ty/ESLint configs, pre-commit hooks
13e. **`best-practices/04-nextjs-production.md`** — Next.js 15 + Tailwind 4 + visx + Framer Motion patterns
13f. **`best-practices/05-bdd-bmad-stories.md`** — Gherkin format, BMad story template, trace-as-assertion pattern, GitHub issue mapping
13g. **`best-practices/06-test-strategy.md`** — pytest patterns, LLM-as-judge cost control, Playwright + sahil-visual-loop

After Phase 3.5 you know the implementation patterns. The spec you write applies these to ChaosLab specifically.

---

## Phase 4 — Exploratory architecture research (skim, NOT decisions — 30 minutes)

The `architecture/` folder is **EARLIER, EXPLORATORY RESEARCH** that was done before the broader-target reframing in `context/`. The synthesis file has a banner saying its conclusions are NOT locked. Treat as data, not decisions.

16. **`architecture/00-synthesis.md`** — read the banner. The 12 "locked decisions" are PRELIMINARY. The data behind each is useful; the conclusions should be re-evaluated.
17. **`architecture/02-phoenix-deep-dive.md`** — the Phoenix-MCP-partial-surface discovery (genuinely informative — code-heavy)
18. **`architecture/04-fault-injection-eval.md`** — OWASP/MITRE fault taxonomy + 12-fault catalog (informative, not prescriptive)
19. **`architecture/05-ux-and-demo.md`** — UX option mockups (informative; cross-reference with `context/03 §12` for current red-team UX patterns)
20. **`architecture/03-multi-agent-patterns.md`** — ADK sub-agents vs A2A vs AgentTool (informative — your architectural decision)
21. **`architecture/06-deployment-ops.md`** — 3-service Cloud Run deployment proposal (informative; re-evaluate given the multi-agent-A2A market-gap finding in `context/03`)
22. **`architecture/01-reference-implementations.md`** — `deepankarm/agent-chaos` Apache-2.0 vendoring opportunity (informative; verify license before commit)

After Phase 4 you've seen one possible architecture; you can either adopt parts, evolve it, or design differently using the corpus.

---

## Phase 5 — Tactical inputs (15 minutes)

Final reads before you write your output:

23. **`01-prizes-tracks.md`** — the judging criteria (4 equal weight: Tech Implementation / Design / Potential Impact / Quality of Idea)
24. **`05-prior-winners.md`** — what shapes won prior Google AI hackathons (hyper-specific domain + multi-step + multi-Google-service + tangible artifact + social impact)
25. **`06-hidden-field.md`** — track saturation (Arize predicted GREEN; ChaosLab is in the least-crowded lane)
26. **`RAT-runbook.md`** — Day-1 validation (already patched for Phoenix MCP partial surface)
27. **`brainstorm/05-ecosystem-refactor.md` §Appendix C** — sample 9-day cadence (was based on solo human dev — adjust for AI-coding speed where reasonable)

After Phase 5 you have the judging context + the practical timing.

---

## What you produce

Depends on your role:

- **`sahil-spec-writer`** → `docs/PRD.md`, `docs/architecture.md`, `docs/ux-spec.md`, `docs/epics.md`, `docs/stories/story-<slug>.md` (one per story)
- **Coding agent** → working code in a feature branch, tested, PR-ready
- **`sahil-hackathon-orchestrator`** → repo + GitHub issues + dispatched coding agents per ticket + review-loop
- **Demo / UX agent** → frontend implementation per the design spec (informed by `context/03 §12` and `architecture/05`)

---

## What you DON'T need to do

- **Don't research outside the folder unless something is marked [UNVERIFIED] AND you actually need it.** The 24,000 lines here cover the domain end-to-end. Spending time on web searches when the answer is in `context/04` wastes context.
- **Don't inherit `architecture/00-synthesis.md`'s "locked decisions" without re-evaluating.** Banner explains why.
- **Don't ask the user "single target or multi-target?" or similar binary architectural questions.** The corpus has the data; you decide.
- **Don't add "MVP vs stretch" framing.** This team uses AI coding agents. Speed isn't constrained the way it would be with solo human dev. Ship everything.

---

## Open observations (data, not directives)

When you make architectural decisions, these factual observations from the corpus may matter:

1. **No red-team product targets multi-agent A2A meshes as first-class** (`context/03 §13`). Open category.
2. **Phoenix MCP server is partial** (`architecture/02`, `context/03 §9`). Read tools exist; experiment + annotation writes require custom Python SDK wraps. Code patterns are in `architecture/02 §9.5-9.6`.
3. **OpenInference is the unifying instrumentation substrate** (`context/04`, `context/06 §3`) across most major agent frameworks.
4. **A2A's `.well-known/agent-card.json` is the de facto agent discovery standard** (`context/05 §1`). Universal first probe.
5. **Vertex Agent Engine requires `register(batch=False, set_global_tracer_provider=False)` for Phoenix traces** (`context/04`). Without both, traces vanish silently.
6. **OWASP Agentic Top 10 (ASI 2026)** is the new judging vocabulary (`context/06 §9`). Map fault classes accordingly.
7. **Inter-token timing fingerprinting** (arXiv 2502.20589) identifies model family without privileged access — relevant if ChaosLab fingerprints black-box agents (`context/05 §12`).
8. **`deepankarm/agent-chaos` is Apache-2.0** and ships fault primitives ChaosLab can vendor (`architecture/01`). Verify license + attribution requirements before commit.
9. **The 4-week judging window (2026-06-22 → 2026-07-06) requires `min-instances=1`** on demo-facing Cloud Run services (`architecture/06 §6`). Idle warm-pool cost > token cost during judging.
10. **Set `JUDGE_LLM = "gemini-3.5-flash"` (not Pro)** — 17× cost difference (`architecture/04`).
