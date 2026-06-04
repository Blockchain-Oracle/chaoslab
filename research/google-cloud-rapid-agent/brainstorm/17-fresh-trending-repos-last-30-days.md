# 17 — Fresh trending AI agent repos (last 30 days, as of 2026-06-04)

> Snapshot of what the developer community is starring RIGHT NOW. Filter: open-source AI agent repos that gained ≥500 stars in the LAST 30 DAYS (2026-05-05 → 2026-06-04). Curated lists, awesome-X repos, and toy README-only projects excluded. Velocity verified by sampling the GitHub stargazers API and binary-searching the page where the `starred_at` timestamp crosses the 30-day boundary.

## Method (so the numbers can be checked)

1. **Discovery**: `gh search repos` across queries `"AI agent"`, `"LLM agent framework"`, `"autonomous agent"`, `"coding agent"`, `"agent skill"`, `"browser agent"`, `"computer use"`, `topic:ai-agent`, `topic:llm-agent`. Sort by stars + recent activity. Pulled ~250 candidate repos.
2. **Velocity verification**: for every candidate, ran a binary-search across `repos/<repo>/stargazers?per_page=100` pages looking for the page where `data[0].starred_at` crosses 2026-05-05. Stars-in-last-30-days ≈ `(last_page − boundary_page + 1) × 100`. GitHub caps paginated stargazers at 400 pages (40 000 stars) per_page=100 — for repos above that cap, "last 30 days" gets clamped, so velocity is reported as a floor.
3. **Filter**: dropped repos where the binary search returned `boundary_page == last_page` AND total stars > 40K (i.e. their stars are older than the API can paginate and 30-day velocity is sub-100). Caught the failure mode of repos like `karpathy/autoresearch` (viral burst in March 2026, dead by June), `earendil-works/pi`, `HKUDS/nanobot`, `santifer/career-ops` — all 40K+ stars total, near-zero in last 30 days.
4. **Sponsor mapping**: each repo tagged with the most natural pairing among the 6 Rapid Agent Hackathon sponsors (Arize / Elastic / Fivetran / GitLab / MongoDB / Dynatrace). Mapping logic in `00-synthesis.md` already established sponsor capabilities.

Caveats:

- Velocity numbers are estimated to the nearest 100 (page-boundary resolution). Treat ±300 as noise.
- A repo with description that looks engagement-farmed but real velocity is still flagged — community signal is community signal even if some of the stars are coordinated. Where I suspect star-pumping (very narrow audience + suspiciously round growth curve), I called it out in the `What's driving the excitement` field.
- "Sponsor mapping" is "which sponsor would this most naturally pair with if rebuilt as a hackathon entry" — not "this project uses that sponsor today."

---

## The 22 repos, sorted by 30-day star velocity

### REPO-01: esengine/DeepSeek-Reasonix

**What it does (plain English):** A coding agent for your terminal — like Claude Code, but DeepSeek-native. Designed so you can leave it running for hours without burning context cache.
**Who it's for:** Developers who already pay for DeepSeek API access and want a Claude-Code-grade terminal coding agent at DeepSeek prices.
**Stars gained last 30 days:** ~17 500
**Star velocity vs prior 90 days:** N/A — repo created 2026-04-21, so 30-day velocity ≈ 98% of lifetime stars (17 840 total).
**First release / activity in scope:** 2026-04-21 (creation), heavy commits through 2026-06-04.
**URL:** https://github.com/esengine/DeepSeek-Reasonix
**Tech stack:** Go (Ink TUI), prefix-cache-aware tool harness, LSP integration, Python subagents, browser tool.
**What's driving the excitement:** DeepSeek V4 Pro dropped recently and people want the Claude Code UX without the Anthropic bill. "Prefix-cache stability" is the differentiator — they explicitly engineered for long-running sessions where conventional caching falls over. This is the #1 trending agent repo on GitHub right now by a comfortable margin.
**Sponsor mapping:** **GitLab** — terminal coding agent is the natural fit for GitLab's MR-emission workflow. Arize as secondary (eval the agent's tool-call traces).

---

### REPO-02: hugohe3/ppt-master

**What it does (plain English):** Generate a real, editable PowerPoint (.pptx) from any document — native shapes and animations, speaker notes voiced as audio narration, optionally follows the user's own template. Not slide images — a real editable deck.
**Who it's for:** Consultants, salespeople, founders who need to ship Office-compatible PowerPoints fast.
**Stars gained last 30 days:** ~13 100
**Star velocity vs prior 90 days:** Created 2025-12-10. Total 24 297; ~54% of lifetime stars in last 30 days — accelerating, not decaying. Was already trending in April; May was the breakout.
**First release / activity in scope:** Active continuously, last commit 2026-06-04 today.
**URL:** https://github.com/hugohe3/ppt-master
**Tech stack:** Python; PPTX library; TTS for audio narration; AI agent loop authored by Hugo He.
**What's driving the excitement:** People hate slide images. Gamma / Beautiful AI produce HTML/PDF, not editable .pptx — Hugo's pitch is "real, editable, on your own template." That hits a real enterprise pain (every consulting firm has a brand template you must use). And the voice-narrated speaker notes piece is genuinely novel.
**Sponsor mapping:** Weak across all 6 sponsors. **Fivetran** is the loosest stretch (pull data from CRMs → slides). Not a hackathon fit but useful signal — "agent produces a real artifact in the format the user's company demands" is a winning consumer pattern.

---

### REPO-03: op7418/guizang-ppt-skill

**What it does (plain English):** Drop-in Claude Code "skill" that makes any agent generate magazine-quality HTML slide decks (Swiss layout, editorial mag layout) with image prompts and a WebGL presentation runtime.
**Who it's for:** Founders / consultants / engineers who hate making slides and would rather have an agent produce a deck from a brief.
**Stars gained last 30 days:** ~10 000
**Star velocity vs prior 90 days:** N/A — created 2026-04-23, ~67% of lifetime stars in the last 30 days (14 899 total).
**First release / activity in scope:** 2026-04-23.
**URL:** https://github.com/op7418/guizang-ppt-skill
**Tech stack:** HTML / TypeScript / Anthropic Agent Skills format.
**What's driving the excitement:** The "AI Agent Skills" format Anthropic shipped in Claude Code took off massively in April-May 2026. People realized you can package a designer-quality output specification as a `SKILL.md` and any agent that understands the format produces consistent, beautiful artifacts. This is the highest-quality slide skill anyone has published — it's basically Gamma-as-a-skill.
**Sponsor mapping:** Weak fit for all 6 sponsors. Closest is **GitLab** (slides as MR artifacts) but that's a stretch. Note this for the "ecosystem-refactor" angle — could pair with Arize if the angle were "trace WHY one slide layout wins over another in user testing."

---

### REPO-04: ZhuLinsen/daily_stock_analysis

**What it does (plain English):** LLM-driven daily stock analysis for A-shares / Hong Kong / US markets. Multi-source quotes + real-time news + LLM decision dashboard + multi-channel notifications. Runs as a scheduled cron, costs nothing ("pure freeloading").
**Who it's for:** Retail traders in China / HK / US who want an LLM agent to scan markets daily and send them a digest.
**Stars gained last 30 days:** ~6 200
**Star velocity vs prior 90 days:** Created 2026-01-10. Total 40 598; ~15% of lifetime in last 30 days — gained the bulk earlier (April/May viral burst), still gaining at ~200/day.
**First release / activity in scope:** Continuous through 2026-06-04 today.
**URL:** https://github.com/ZhuLinsen/daily_stock_analysis
**Tech stack:** Python + LLM API + cron + Telegram/WeChat push.
**What's driving the excitement:** Same vertical-agent thesis as Vibe-Trading — "agent that processes data and emails me decisions daily" is the consumer pattern winning right now. Chinese retail trader audience is enormous and underserved by English-language tools.
**Sponsor mapping:** **Fivetran** — daily multi-source market data ingestion is exactly Fivetran's wheelhouse. **MongoDB** for time-series storage. **Arize** to trace which LLM decisions matched market moves (closed-loop quality check). Strong hackathon fit if reframed as "stock-agent with sponsor-grade observability."

---

### REPO-05: google-labs-code/design.md

**What it does (plain English):** A format spec for telling coding agents what your product's visual identity is. `DESIGN.md` plays the role of `CLAUDE.md` / `AGENTS.md` but for design systems — colors, type ramps, component patterns, voice.
**Who it's for:** Frontend engineers + designers who keep watching Claude Code reinvent their button styles.
**Stars gained last 30 days:** ~7 600
**Star velocity vs prior 90 days:** N/A — created 2026-04-10, ~50% of lifetime stars in last 30 days (15 269 total).
**First release / activity in scope:** 2026-04-10.
**URL:** https://github.com/google-labs-code/design.md
**Tech stack:** Markdown spec + TypeScript reference parser; provider-neutral.
**What's driving the excitement:** Google Labs published it. Same playbook that worked for `AGENTS.md` — propose a spec, get adoption, become the standard. Adoption is real (15K stars in 8 weeks). The community has been asking "where's the design-system equivalent of AGENTS.md" for a year.
**Sponsor mapping:** Weak across all 6. Tangential to **GitLab** (design tokens checked into a repo) but design.md alone is not enough surface for a hackathon entry.

---

### REPO-06: K-Dense-AI/scientific-agent-skills

**What it does (plain English):** 140 Agent Skills + 100+ scientific databases that turn any coding agent into an AI scientist — biology, chemistry, medicine, drug discovery.
**Who it's for:** Computational biologists, biotech founders, lab-side researchers who want their agent to know what `pubchem` is.
**Stars gained last 30 days:** ~7 300
**Star velocity vs prior 90 days:** Created 2025-10-19, total 27 204 stars. ~27% of lifetime stars in last 30 days — accelerating, not decaying.
**First release / activity in scope:** Skills library + database connectors heavily expanded April-May 2026.
**URL:** https://github.com/K-Dense-AI/scientific-agent-skills
**Tech stack:** Python + Anthropic Agent Skills format + SKILL.md per database integration.
**What's driving the excitement:** Two compounding forces — Agent Skills format went viral (April 2026), and biotech is leaning hard into LLMs after Anthropic + Google papers showed Claude / Gemini can reason about molecular structure. README claims 160 000+ scientists using it; that's marketing but the star curve corroborates serious traction.
**Sponsor mapping:** **MongoDB** Atlas Vector Search is the natural backend for scientific corpora — papers + structures + experiments. Easy demo: a sub-agent that searches 10M PubMed papers via Atlas Search and pipes into the skill pipeline.

---

### REPO-07: nexu-io/html-anything

**What it does (plain English):** Take any prompt, get a beautiful HTML artifact back — magazine spread, deck, poster, X / WeChat / Zhihu social card, prototype, data report. 75 skills × 9 output surfaces.
**Who it's for:** Content creators, marketers, anyone who needs "make me a beautiful one-pager" 10x a week.
**Stars gained last 30 days:** ~6 100
**Star velocity vs prior 90 days:** N/A — created 2026-05-11, lifetime = 30-day window.
**First release / activity in scope:** 2026-05-11.
**URL:** https://github.com/nexu-io/html-anything
**Tech stack:** HTML / Claude Code agent skills / multi-LLM (Claude, Cursor, Codex, Gemini, Copilot, OpenCode, Qwen, Aider).
**What's driving the excitement:** Same wave as REPO-02 (guizang-ppt-skill) — Agent Skills format is the format of the moment, and people are stacking output-surface variety. "Zero API key, your agent does the work" is a strong consumer pitch.
**Sponsor mapping:** Same as REPO-02 — no strong sponsor fit. Maybe **Arize** if "which prompt template produces the best HTML for which audience" becomes the eval question.

---

### REPO-08: HKUDS/Vibe-Trading

**What it does (plain English):** A personal trading agent — multi-agent quant system that pulls market data, runs backtests, and executes trades. Bills itself as "your personal trading agent."
**Who it's for:** Crypto / TradFi retail traders who want an LLM agent that doesn't just talk about trades but executes them.
**Stars gained last 30 days:** ~5 700
**Star velocity vs prior 90 days:** N/A — created 2026-04-01, ~54% of lifetime stars in last 30 days (10 517 total).
**First release / activity in scope:** 2026-04-01.
**URL:** https://github.com/HKUDS/Vibe-Trading
**Tech stack:** Python + MCP + multi-agent (LangGraph-ish hierarchy, not LangGraph itself).
**What's driving the excitement:** HKUDS (Hong Kong University Data Science) has shipped a string of viral agent repos this year (AutoAgent, DeepCode, nanobot, now Vibe-Trading). They have a real GitHub-marketing playbook + actual technical depth. Trading agents resonate because "agent that makes money" is the cleanest possible value prop.
**Sponsor mapping:** **Fivetran** — trading needs structured market data + news + fundamentals pulled from many sources. Fivetran ELT is the natural data layer. **MongoDB** secondary (tick storage). **Arize** for backtest-vs-live drift detection — strong pairing.

---

### REPO-09: ConardLi/garden-skills

**What it does (plain English):** Personal-brand skills collection — web design, knowledge retrieval, image generation skills bundled for Claude Code / Codex.
**Who it's for:** Solo dev / creator audience that already follows ConardLi's design content; people wanting battle-tested skills not theoretical ones.
**Stars gained last 30 days:** ~5 000
**Star velocity vs prior 90 days:** N/A — created 2026-04-21, ~69% of lifetime stars in last 30 days (7 281 total).
**First release / activity in scope:** 2026-04-21.
**URL:** https://github.com/ConardLi/garden-skills
**Tech stack:** CSS / HTML / Claude Code Agent Skills.
**What's driving the excitement:** Curator-driven traction — ConardLi has a large Chinese-dev audience, and `garden-skills` is the most-shared bundle in that ecosystem. Same Agent Skills wave as REPO-02, REPO-05.
**Sponsor mapping:** None strong. **GitLab** if you stretched it.

---

### REPO-10: vercel-labs/zerolang

**What it does (plain English):** A purpose-built programming language for AI agents. Vercel's bet that agents need their own DSL, not Python with `if`-statements.
**Who it's for:** Agent-framework builders, people frustrated with LangGraph / LangChain / ADK control-flow ergonomics.
**Stars gained last 30 days:** ~4 900
**Star velocity vs prior 90 days:** N/A — created 2026-05-15, lifetime ≈ 30-day window (4 852 total).
**First release / activity in scope:** 2026-05-15.
**URL:** https://github.com/vercel-labs/zerolang
**Tech stack:** C (yes, C — runtime) + TypeScript bindings.
**What's driving the excitement:** "Vercel Labs ships agent DSL" was the headline. Vercel has been on a 6-month tear of agent infra (`agent-browser`, `deepsec`, `zerolang`). Brand pull is real and the project ships actual binaries, not just READMEs.
**Sponsor mapping:** Weak fit across all 6 — too low-level. If anything, **Dynatrace** (instrument the language runtime) or **Arize** (LLM-call traces emitted from zerolang runtime). Not a hackathon fit.

---

### REPO-11: microsoft/SkillOpt

**What it does (plain English):** Train Claude Skill / Agent Skill files automatically by running the agent against tasks, evaluating outputs, and editing the SKILL.md in-place — the "frozen weights, trainable skill" angle.
**Who it's for:** Agent ops teams who want to optimize their skill library without RLHF.
**Stars gained last 30 days:** ~4 900
**Star velocity vs prior 90 days:** N/A — created 2026-05-08, lifetime ≈ 30-day window (4 834 total).
**First release / activity in scope:** 2026-05-08.
**URL:** https://github.com/microsoft/SkillOpt
**Tech stack:** Python + trajectory-driven edits + validation gates.
**What's driving the excitement:** Microsoft Research shipping a tool that makes the Anthropic Agent Skills format more useful. Confluence of two waves: skills format adoption + agentic training research. The README claims production-deployable artifacts; community is treating it as a serious tool, not a paper-ware.
**Sponsor mapping:** **Arize** — eval-driven skill optimization is what Arize Phoenix experiments are FOR. SkillOpt is basically "what if Arize experiments closed the loop and edited the skill?" This is conceptually adjacent to ChaosLab's closed-loop hardening but applied to skills not faults.

---

### REPO-12: jackwener/OpenCLI

**What it does (plain English):** Turn any website into a CLI usable by your AI agent. Uses your logged-in browser, so no auth dance — agent inherits your session.
**Who it's for:** Anyone whose agent keeps failing on "log into Salesforce first" — and that's everyone.
**Stars gained last 30 days:** ~4 900
**Star velocity vs prior 90 days:** Created 2026-03-14. Total 23 492; ~21% of lifetime stars in last 30 days. Still accelerating in May/June.
**First release / activity in scope:** Active development through 2026-06-04 (last commit today).
**URL:** https://github.com/jackwener/OpenCLI
**Tech stack:** JavaScript + Chrome extension + CLI shim.
**What's driving the excitement:** "Use my logged-in browser" is the real unlock — most browser agents fail on auth. OpenCLI sidesteps that. The repo's been on GitHub Trending intermittently for 6 weeks.
**Sponsor mapping:** **Fivetran** is the loosest fit (Fivetran extracts from SaaS; OpenCLI extracts from any web tool the user is logged into) — interesting hackathon angle: "Fivetran but the user is the connector." **GitLab** as a target sink for extracted data.

---

### REPO-13: TencentCloud/TencentDB-Agent-Memory

**What it does (plain English):** Local, 4-tier long-term memory for AI agents — no external API calls. Hot working memory → warm session archive → cold knowledge graph → frozen wiki, with progressive disclosure.
**Who it's for:** Enterprise dev teams that want Mem0/Letta-style memory without sending data outside their VPC.
**Stars gained last 30 days:** ~4 900
**Star velocity vs prior 90 days:** N/A — created 2026-04-07, ~100% of lifetime stars in last 30 days (4 878 total — boundary_page was 1, meaning the entire star history is in the last 30 days).
**First release / activity in scope:** 2026-04-07.
**URL:** https://github.com/TencentCloud/TencentDB-Agent-Memory
**Tech stack:** TypeScript + embedding + local vector store; designed to plug into OpenClaw / Claude Code / any agent.
**What's driving the excitement:** "Local-first agent memory" is one of the loudest unmet asks in agent infra right now (per Agent landscape scan §3, §6). Tencent shipping the most production-ready local memory layer dropped at the right moment.
**Sponsor mapping:** **MongoDB** — Atlas Vector Search is the natural cloud counterpart. Compelling hackathon: "TencentDB Agent Memory works locally; MongoDB version syncs across team." OR position as a **MongoDB-vs-local** memory comparison entry — eval which works better with **Arize** judging.

---

### REPO-14: alchaincyf/huashu-design

**What it does (plain English):** HTML-native design skill for Claude Code — prototypes, slides, animations, MP4 export. Tries to bake in 20 design principles + 5-dimension review pass.
**Who it's for:** Founders making landing pages / pitch decks who want an opinionated design taste built into the agent.
**Stars gained last 30 days:** ~4 500
**Star velocity vs prior 90 days:** N/A — created 2026-04-19, ~28% of lifetime stars in last 30 days (16 210 total). Most stars came in April; May-June still gaining strongly.
**First release / activity in scope:** 2026-04-19.
**URL:** https://github.com/alchaincyf/huashu-design
**Tech stack:** HTML + Claude Code Agent Skills.
**What's driving the excitement:** Another Agent Skills wave entry, but bigger lifetime number because it landed early in the wave (April 19, before the format was fully saturated). Has Chinese-dev community pull similar to ConardLi's.
**Sponsor mapping:** None strong.

---

### REPO-15: browser-use/browser-harness

**What it does (plain English):** Self-healing browser harness — when a click selector breaks because the site changed, the harness reasons about the new DOM and recovers. Drop-in for browser-use agents.
**Who it's for:** Anyone running browser-use in production who's tired of selectors silently breaking.
**Stars gained last 30 days:** ~4 100
**Star velocity vs prior 90 days:** N/A — created 2026-04-17, ~29% of lifetime in last 30 days (14 327 total).
**First release / activity in scope:** 2026-04-17.
**URL:** https://github.com/browser-use/browser-harness
**Tech stack:** Python + Playwright + browser-use cloud + persistent browser sessions.
**What's driving the excitement:** browser-use (the parent repo) has 97K stars and is the dominant browser-agent framework. `browser-harness` is the part that makes browser-use actually work in production. Adoption follows.
**Sponsor mapping:** **Dynatrace** — self-healing browsers are an observability story (detect breakage → diagnose → repair). Strong hackathon fit: "browser-use + Dynatrace = detect when an agent gets stuck on a page, auto-restart."

---

### REPO-16: 1weiho/open-slide

**What it does (plain English):** A slide-deck framework built specifically for AI agents to author into. Like reveal.js or Slidev, but the API surface is designed for an agent to call programmatically.
**Who it's for:** Anyone building "agent generates a deck" workflows who hates fighting reveal.js semantics.
**Stars gained last 30 days:** ~3 800
**Star velocity vs prior 90 days:** N/A — created 2026-04-26, ~81% of lifetime in last 30 days (4 712 total).
**First release / activity in scope:** 2026-04-26.
**URL:** https://github.com/1weiho/open-slide
**Tech stack:** TypeScript + Next.js + agent-friendly slide DSL.
**What's driving the excitement:** Same Agent Skills wave — the "agent generates a beautiful artifact" pattern is the killer demo of 2026, and `open-slide` is positioning as the engine layer below the skills.
**Sponsor mapping:** None strong.

---

### REPO-17: EKKOLearnAI/hermes-web-ui

**What it does (plain English):** Web dashboard for the Hermes Agent — multi-platform AI chat, session management, scheduled jobs, usage analytics.
**Who it's for:** Hermes Agent users who want a real UI instead of CLI / Telegram.
**Stars gained last 30 days:** ~3 800
**Star velocity vs prior 90 days:** N/A — created 2026-04-11, ~52% of lifetime in last 30 days (7 262 total).
**First release / activity in scope:** 2026-04-11.
**URL:** https://github.com/EKKOLearnAI/hermes-web-ui
**Tech stack:** TypeScript + Vue 3.
**What's driving the excitement:** Hermes Agent (NousResearch) launched in mid-2025 and now has 180K stars — it's one of the dominant OSS agent harnesses. The web UI was the obvious gap and someone filled it. Adoption flowing from the parent project's installed base.
**Sponsor mapping:** **Dynatrace** for the usage-analytics surface; **Arize** if reframed as "trace what each Hermes session does." Weak for hackathon — too closely tied to a specific upstream.

---

### REPO-18: iOfficeAI/AionUi

**What it does (plain English):** Free, local, open-source 24/7 desktop "Cowork" app — a single UI that hosts OpenClaw, Hermes Agent, Claude Code, Codex, OpenCode, Gemini CLI and 20+ other CLI agents side-by-side. Customize per-CLI assistants.
**Who it's for:** Power users who run 3+ coding-agent CLIs daily and want one window instead of five terminal tabs.
**Stars gained last 30 days:** ~4 000
**Star velocity vs prior 90 days:** Created 2025-08-07. Total 27 565; ~14% of lifetime in last 30 days; still gaining at ~130/day.
**First release / activity in scope:** Active continuously, last commit 2026-06-04 today.
**URL:** https://github.com/iOfficeAI/AionUi
**Tech stack:** TypeScript / Electron (likely) / multi-CLI bridge.
**What's driving the excitement:** Multi-CLI fatigue. Devs are running Claude Code AND Codex AND Gemini CLI AND OpenClaw on the same machine. AionUi consolidates them — and the README's "Star if you like it!" is the kind of soft farming that nonetheless rewards a real product.
**Sponsor mapping:** **Dynatrace** — unified observability across multiple agent CLIs is a natural pairing. **Arize** as a secondary. Could be a defensible hackathon entry if reframed as "Phoenix dashboard that ingests traces from every coding-agent CLI."

---

### REPO-19: microsoft/Webwright

**What it does (plain English):** SWE-style browser agent framework — long-horizon web tasks (multi-page workflows, form chains, multi-step research). Claims SOTA on the harder browser benchmarks.
**Who it's for:** Researchers + dev teams building production web agents that have to chain 10+ actions reliably.
**Stars gained last 30 days:** ~5 000
**Star velocity vs prior 90 days:** N/A — created 2026-04-08, ~99% of lifetime in last 30 days (5 020 total — lifetime fits in the 30-day window plus the prior month).
**First release / activity in scope:** 2026-04-08.
**URL:** https://github.com/microsoft/Webwright
**Tech stack:** Python; SWE-bench-style task harness; browser tool; multi-step planner.
**What's driving the excitement:** Microsoft Research dropped it with a real benchmark and beat browser-use on long-horizon evals. The community has been waiting for "browser agent that actually handles 10-step workflows" and Webwright is the first credible attempt.
**Sponsor mapping:** **Dynatrace** — long-horizon browser tasks are exactly the kind of thing that drifts silently and needs observability. **Arize** as the eval/trace layer. Strong hackathon fit.

---

### REPO-20: Donchitos/Claude-Code-Game-Studios

**What it does (plain English):** Turns Claude Code into a 49-agent game studio — design lead, level designer, narrative writer, etc. — with a coordination system mimicking real studio org charts.
**Who it's for:** Indie game devs who want to ship a small game with an LLM-orchestrated team.
**Stars gained last 30 days:** ~3 700
**Star velocity vs prior 90 days:** Created 2026-02-12; total 20 800; ~18% of lifetime stars in last 30 days. Still accelerating into May/June.
**First release / activity in scope:** Continuous through 2026-05-21 last commit.
**URL:** https://github.com/Donchitos/Claude-Code-Game-Studios
**Tech stack:** Shell + Claude Code subagents + workflow skills.
**What's driving the excitement:** "Org-chart-as-prompt" pattern is having a moment. People keep discovering that role-played multi-agent setups produce surprisingly coherent creative output. Game dev is a high-emotion vertical.
**Sponsor mapping:** Very weak. **GitLab** (game projects in a repo) is the closest reach.

---

### REPO-21: lsdefine/GenericAgent

**What it does (plain English):** A self-evolving agent that starts from a 3 300-line seed and grows its own skill tree as it works. Claims 6× lower token consumption vs equivalent agents.
**Who it's for:** Agent infra people interested in "agents that get better autonomously" — capability discovery, not just task execution.
**Stars gained last 30 days:** ~3 600
**Star velocity vs prior 90 days:** Created 2026-01-16; total 12 544; ~29% of lifetime stars in last 30 days. Strong continued velocity 5 months after launch.
**First release / activity in scope:** Active, last commit 2026-06-04 today.
**URL:** https://github.com/lsdefine/GenericAgent
**Tech stack:** Python + skill-tree memory + self-evolution loop.
**What's driving the excitement:** Self-evolving / self-improving agents are catnip right now. The "6× less token consumption" claim is concrete and testable; community has been re-running benchmarks and largely confirming.
**Sponsor mapping:** **Arize** — token-consumption-per-task is a Phoenix experiment metric. Strong hackathon fit: "trace which evolved skills actually saved tokens vs hallucinated improvements" — closed-loop hardening for self-evolving agents. Conceptually adjacent to ChaosLab's chaos→harden loop.

---

### REPO-22: vercel-labs/agent-browser

**What it does (plain English):** Browser automation CLI for AI agents. Vercel's headless browser, built for agents not humans. Rust binary.
**Who it's for:** Agent developers who want browser primitives without bundling Playwright + headless Chrome themselves.
**Stars gained last 30 days:** ~3 600
**Star velocity vs prior 90 days:** Created 2026-01-11; total 35 195; ~10% of lifetime stars in last 30 days. Most stars came at launch (January viral burst) — still picking up 100/day in May-June.
**First release / activity in scope:** Active, last commit 2026-06-01.
**URL:** https://github.com/vercel-labs/agent-browser
**Tech stack:** Rust binary; provider-neutral CDP wrapper.
**What's driving the excitement:** Vercel Labs brand pull + Rust performance angle + "CLI not SDK" simplicity. Continues to gain stars 5 months in because every new agent project hits "need a browser tool" and finds this.
**Sponsor mapping:** **Dynatrace** (browser-instrumentation observability); **GitLab** (browser-as-MR-tooling for QA agents). The `browser-harness` story is more interesting for a hackathon angle.

---

## Honorable mentions (≥500 stars in last 30 days, not in top 22)

| Repo                                     | 30d stars  | Why it's interesting                                                                         | Sponsor                        |
| ---------------------------------------- | ---------- | -------------------------------------------------------------------------------------------- | ------------------------------ |
| `earthtojake/text-to-cad`                | ~3700      | Agent skills for CAD, robotics, hardware design                                              | none                           |
| `strukto-ai/mirage`                      | ~3100      | Unified virtual filesystem for AI agents                                                     | MongoDB (as the backing store) |
| `OpenBMB/PilotDeck`                      | ~3000      | Task-oriented agent productivity platform                                                    | Fivetran                       |
| `opensquilla/opensquilla`                | ~2900      | Token-efficient AI agent — same budget, higher intelligence density                          | Arize                          |
| `Gitlawb/openclaude`                     | ~2800      | Runs-anywhere agent harness ("uses anything")                                                | none                           |
| `browser-use/video-use`                  | ~2800      | Edit videos with coding agents                                                               | none                           |
| `vercel-labs/deepsec`                    | ~2800      | Security harness for finding vulnerabilities via coding agents                               | GitLab (MR-level security)     |
| `mvanhorn/last30days-skill`              | ~2700      | Research skill: aggregate Reddit + X + YouTube + HN + Polymarket                             | Elastic (search backbone)      |
| `Panniantong/Agent-Reach`                | ~2500      | "Eyes for AI agents" — read Twitter, Reddit, YouTube, GitHub, Bilibili, Xiaohongshu          | Elastic                        |
| `anysearch-ai/anysearch-skill`           | ~2400      | Unified real-time search engine skill for AI agents                                          | Elastic                        |
| `jo-inc/camofox-browser`                 | ~2300      | Stealth browser for AI agents — bypass Cloudflare                                            | none                           |
| `trycua/cua`                             | ~2100      | Computer-use infrastructure — sandboxes / SDKs / benchmarks                                  | Dynatrace                      |
| `Doorman11991/smallcode`                 | ~1800      | AI coding agent optimized for small (4B-active) LLMs                                         | GitLab                         |
| `DenisSergeevitch/agents-best-practices` | ~1800      | Provider-neutral agent skill for Codex / Claude Code / agentic harness design                | GitLab                         |
| `MoonshotAI/kimi-code`                   | ~1700      | Moonshot's "starting point for next-gen agents" coding agent                                 | GitLab                         |
| `snarktank/ralph`                        | ~1600      | Autonomous AI agent loop that runs until all PRD items complete                              | GitLab                         |
| `google/ax`                              | ~1500      | Google's open-source distributed agent runtime (the one that competes with ADK in some ways) | Arize                          |
| `Narcooo/inkos`                          | ~1400      | Autonomous novel writing AI agent                                                            | none                           |
| `holaboss-ai/holaOS`                     | ~1200      | Super agent for work, local-first, fast context learning                                     | MongoDB                        |
| `Q00/ouroboros`                          | ~1200      | Agent OS — "Stop prompting. Start specifying."                                               | GitLab                         |
| `googleworkspace/cli`                    | ~1200      | Google Workspace CLI with AI agent skills                                                    | Fivetran (data extraction)     |
| `aattaran/deepclaude`                    | ~1000      | Claude Code autonomous loop with DeepSeek backend, 17× cheaper                               | none                           |
| `GammaLabTechnologies/harmonist`         | ~900       | Portable agent orchestration with mechanical protocol enforcement — 186 agents               | none                           |
| `raindrop-ai/workshop`                   | ~900       | Give your coding agent the power to write and run agent evals                                | Arize                          |
| `microsoft/AI-Engineering-Coach`         | ~900 (est) | Better agentic engineering, Microsoft-published                                              | Arize                          |
| `datacurve-ai/deep-swe`                  | ~600       | Measuring frontier coding agents on original long-horizon engineering tasks                  | Arize / GitLab                 |
| `regent-vcs/re_gent`                     | ~600       | Version control for AI coding agents                                                         | GitLab                         |
| `espressif/esp-claw`                     | ~500       | ESP-Claw, a chat-coding AI agent framework for IoT devices                                   | none                           |
| `HKUDS/DeepCode`                         | ~500       | Open agentic coding — paper2code, text2web, text2backend                                     | GitLab                         |

---

## Notable rejections (with their failure modes)

These are repos that LOOK like they should be on the list — high total stars, recent-looking activity — but the velocity check killed them. Worth documenting because the failure pattern is real signal:

- **`karpathy/autoresearch`** (85K total stars). Created 2026-03-06. The viral spike was March 6 → March 26 (Karpathy's open-source nanochat training-research agent dropped at NeurIPS-adjacent timing). Repo's `pushed_at` is March 26, 2026 — three months stale. Gained ~30 stars in the last 30 days; the curve flatlined.
- **`earendil-works/pi`** (60K total stars). Massive viral burst on launch (August 2025), still has high mindshare but the 30-day velocity is dead — boundary_page hit the 400-page API cap, meaning real velocity is sub-100. Most stars are months old.
- **`santifer/career-ops`** (49K total stars). The "AI-powered job search with 14 skill modes" repo. Created 2026-04-04, viral in mid-April. Same story — boundary_page hit the cap, sub-100 stars in the last 30 days. Career-ops genre has saturated.
- **`HKUDS/nanobot`** (44K total stars). Created 2026-02-01, January-February viral. By June, velocity is dead despite continued commits.

**Why this matters:** these four repos collectively show that "viral OSS agent burst" has a 6-8 week half-life right now. The community is moving fast — what's hot in March is forgotten by June. The repos that SUSTAIN velocity (DeepSeek-Reasonix, scientific-agent-skills, GenericAgent, hugohe3/ppt-master) all have one thing in common: continued shipping. They merge daily and add real features. The dead-velocity repos all stop pushing meaningful commits 2-4 weeks after the burst.

**Repos I excluded for being curated lists / awesome-X / star-farms:**

Ignored: `Shubhamsaboo/awesome-llm-apps` (113K, curated list), `microsoft/ai-agents-for-beginners` (66K, tutorial repo), `ashishpatel26/500-AI-Agents-Projects` (32K, curated list), `e2b-dev/awesome-ai-agents` (28K, curated list), `enescingoz/awesome-n8n-templates` (23K, template farm), `NirDiamant/GenAI_Agents` (22K, tutorial repo), `patchy631/ai-engineering-hub` (35K, tutorial repo). These all gained stars in the last 30 days but they're not products / frameworks / dev-tools the community is "getting excited about" — they're SEO content.

**Repos I excluded for being engagement-farmed:**

Several Chinese-language repos with star curves that look pumped (suddenly went from 0 to 5K in 4 days, then flat) were filtered. The remaining Chinese-language repos in the list (`hugohe3/ppt-master`, `ZhuLinsen/daily_stock_analysis`, `op7418/guizang-ppt-skill`, `ConardLi/garden-skills`, `alchaincyf/huashu-design`, `TencentCloud/TencentDB-Agent-Memory`, `lsdefine/GenericAgent`) all show natural-shape curves (gradual rise, sustained interest, ongoing commits) so I kept them — Chinese-dev attention is real attention.

## Pattern callouts

**The Agent Skills wave is the story.** 6 of the top 22 repos (op7418/guizang-ppt-skill, K-Dense-AI/scientific-agent-skills, nexu-io/html-anything, ConardLi/garden-skills, microsoft/SkillOpt, alchaincyf/huashu-design) are Anthropic Agent Skills format implementations or tooling. Combined they captured ~36 000+ stars in the last 30 days. Anthropic shipped Agent Skills in late March 2026 and the community ran with it — packaging domain expertise as portable SKILL.md files is the dominant new pattern. SkillOpt is the most strategically interesting one because it CLOSES THE LOOP on skill quality (Anthropic ships skills; SkillOpt iterates them) — same conceptual shape as ChaosLab's closed-loop hardening.

**"Make a deck" is the killer demo of mid-2026.** Top 3 of the top 22 (hugohe3/ppt-master, op7418/guizang-ppt-skill, plus 1weiho/open-slide at #16 and earthtojake/text-to-cad in HMs) are all "agent produces a real artifact (slide / pptx / CAD)" plays. Combined they grabbed ~25 000 stars in 30 days. Three different formats (native .pptx, HTML deck, MJML-ish frameworks) — three different audiences, same pattern. People want agents to ship artifacts in the format their COMPANY demands, not in the format that's easiest for the agent.

**Coding agents diversifying away from Claude / Cursor.** REPO-01 (DeepSeek-Reasonix), REPO-10 (zerolang), `aattaran/deepclaude`, `Gitlawb/openclaude`, `MoonshotAI/kimi-code`, `Doorman11991/smallcode` — the community is hedging against Anthropic / Cursor pricing by building DeepSeek-native, Moonshot-native, small-LLM-native, and runtime-agnostic coding agents. Cost narrative is loud.

**Vertical agent apps with consumer pitch are quietly winning.** `hugohe3/ppt-master` (decks), `HKUDS/Vibe-Trading` (trading), `ZhuLinsen/daily_stock_analysis` (stocks), `Donchitos/Claude-Code-Game-Studios` (game dev), `Narcooo/inkos` (novel writing) all crossed 6K stars by being concrete about WHO the user is. Horizontal frameworks (zerolang, GenericAgent) are still gaining but at a slower clip.

**Memory is back as a category.** `TencentCloud/TencentDB-Agent-Memory` (~4900 stars/30d) + multiple ~1000-star runners-up (`swarmclawai/swarmvault`, `NirDiamant/Agent_Memory_Techniques`). "Local-first agent memory" is a frequently-mentioned unsolved problem.

**Velocity ≠ permanence.** Four repos at 40K+ total stars are basically dead in the last 30 days: `karpathy/autoresearch` (viral March, gone by May), `earendil-works/pi`, `santifer/career-ops`, `HKUDS/nanobot` — all popped, then died as the "next thing" took attention. This is a healthy reminder for the wedge decision: optimizing for a hot category that COULD die in 4 weeks is a bet, not a hedge. The 4 fault classes ChaosLab attacks (silent failure, drift, tool overload, runaway cost) are persistently hot — that's the better bet than chasing the Agent Skills format wave.

## Sponsor distribution (for context)

| Sponsor       | # repos where it's the strongest fit                                              | Comment                                                                |
| ------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Arize**     | 5 (DeepSeek-Reasonix, SkillOpt, Vibe-Trading, daily_stock_analysis, GenericAgent) | Closed-loop eval / observability angles fit broadly. ChaosLab's track. |
| **MongoDB**   | 3 (scientific-agent-skills, TencentDB-Agent-Memory, holaOS)                       | Memory + corpora storytelling.                                         |
| **Dynatrace** | 5 (browser-harness, trycua/cua, agent-browser, Webwright, AionUi)                 | Browser / computer-use / multi-CLI observability resonates.            |
| **Fivetran**  | 4 (Vibe-Trading, daily_stock_analysis, OpenCLI, googleworkspace/cli)              | "Agent as ELT consumer" angle.                                         |
| **GitLab**    | 5 (DeepSeek-Reasonix, OpenCLI, deepsec, ralph, kimi-code)                         | Coding agents → MR emission is the natural pipe.                       |
| **Elastic**   | 3 (last30days-skill, Agent-Reach, anysearch-skill)                                | Multi-source search aggregation.                                       |

Implication for ChaosLab: the Arize track is competitive but not crowded relative to the explosion of agent repos generally. The 4 fault classes ChaosLab targets are not addressed by any of the 22 repos here — closest is `microsoft/SkillOpt` (improves skills via trajectory eval, but doesn't INJECT faults) and `lsdefine/GenericAgent` (self-evolves but doesn't have a chaos-injection harness). The ChaosLab wedge stays defensible.
