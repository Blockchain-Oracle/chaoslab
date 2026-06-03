# 01 — Prizes, Tracks, and Judging

Everything money-and-evaluation related, all in one place. Source: official Devpost rules at rapid-agent.devpost.com (verified 2026-06-02).

---

## The bucket system

Six **identical, parallel** prize buckets — one per partner. You compete only against entrants who chose the same partner track. This is the most important structural feature of the hackathon, because it means:

- A weak field in one bucket → easier win
- A crowded bucket → much harder, even with a strong submission
- Total prize pool = $60,000 across 6 buckets ($10K per bucket)

Each submission enters **exactly one** track. You may submit multiple projects to multiple tracks if each is "unique and substantially different" (Section 7). Each submission can win **at most one** prize.

---

## Prize tiers (identical across all 6 buckets)

| Place                | Cash (USD)  | Other                                  |
| -------------------- | ----------- | -------------------------------------- |
| 🥇 1st Place         | **$5,000**  | Opportunity for social-media promotion |
| 🥈 2nd Place         | **$3,000**  | —                                      |
| 🥉 3rd Place         | **$2,000**  | —                                      |
| **Per-bucket total** | **$10,000** | —                                      |

**Across all 6 buckets:** $60,000 total prize pool, 18 winners.

---

## The 6 tracks

| #   | Track         | Partner technology focus                                             |
| --- | ------------- | -------------------------------------------------------------------- |
| 1   | **Arize**     | LLM observability via Phoenix MCP (eval, tracing, prompt versioning) |
| 2   | **Elastic**   | Hybrid search + vector store via Elastic MCP                         |
| 3   | **Fivetran**  | Managed data ingestion (ELT pipelines) via Fivetran MCP              |
| 4   | **GitLab**    | DevOps automation via official GitLab MCP server                     |
| 5   | **MongoDB**   | Document DB + vector search via MongoDB MCP                          |
| 6   | **Dynatrace** | APM / observability via Dynatrace MCP                                |

For each: see the corresponding `partner-*.md` file in this folder.

---

## What you must submit

Per Section 7B of the rules:

| Required                     | Detail                                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------- |
| **Hosted Project URL**       | Judges access it without your help. No-login sandbox with sample data is acceptable.            |
| **Public GitHub repo**       | Open-source license file detectable + visible in About section. New code only, May 5 – June 11. |
| **3-minute demo video**      | YouTube or Vimeo, public, English or English subs, shows agent functioning                      |
| **Devpost text description** | Features, technologies used, data sources, learnings                                            |
| **Track selection**          | Exactly one partner per submission                                                              |
| **Devpost form**             | Standard submission fields completed                                                            |

**Deadline:** 2026-06-11, 2:00 PM Pacific Time.

---

## Submission constraints (Section 7B)

1. **New work only.** No reusing existing codebases. A new iteration of an old idea is fine; reusing code is not.
2. **Team size:** max 4 individuals. One person designated "Representative" for prize allocation.
3. **Required AI tools (in the SUBMITTED code):** Only Google Cloud AI tools (Gemini models on Agent Platform, BigQuery ML, etc.) + the chosen partner's built-in AI features. Banned in submission: Claude, Cursor, GitHub Copilot, and any other competing AI services as runtime dependencies.
4. **Required orchestrator:** Google Cloud Agent Builder ecosystem (visual Studio OR ADK / Agent Runtime / Cloud Run). LangChain / LangGraph / LlamaIndex shouldn't be your _primary_ orchestrator.
5. **Required infrastructure:** Google Cloud. No competing cloud platforms (AWS, Azure, etc.) for the agent runtime.
6. **Required platform:** Web, Android, or iOS.

**Important clarification (from peer agent research):** the Section 7B ban applies to **runtime dependencies in the submitted code**, not your dev tooling. You can still use Claude Code, Cursor, Copilot, etc. as IDE assistants during development. See `02a-google-cloud-stack.md` §11 for sourced detail.

---

## Judging mechanics (Section 8)

### Stage 1: Viability screen (pass/fail)

A submission passes Stage 1 if it:

- Includes all required submission elements (URL, repo, video, description, track)
- Reasonably addresses the chosen partner's challenge
- Reasonably applies both the required partner data/products and Google Cloud products

Stage 1 may use **automated AI-driven analysis** (e.g., automated repo scans). Anything that smells like a banned AI dependency (Claude/Cursor/Copilot in `package.json`, `requirements.txt`, etc.) is the highest-confidence Stage-1 fail risk. Scrub your repo before submission.

### Stage 2: Scored evaluation (equal-weighted)

Surviving submissions are evaluated on **4 criteria, equally weighted**:

| Criterion                        | Plain-English question                                                                              |
| -------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Technological Implementation** | Does the interaction with Google Cloud + partner services demonstrate quality software development? |
| **Design**                       | Is the UX and design well thought out?                                                              |
| **Potential Impact**             | How big of an impact could this have on the target community?                                       |
| **Quality of the Idea**          | How creative and unique is the project?                                                             |

Ties broken by comparing scores in the order above, then judge vote.

Highest-scoring submission per track wins 1st, next wins 2nd, etc.

### Judging window

- **Judging period:** 2026-06-22 → 2026-07-06
- **Potential winner notification:** ~2026-07-07
- **Winner has 2 business days** to respond to notification — miss this and you're disqualified and the next-highest-scoring submission gets your slot.

---

## The judges

Per the official Devpost page, judges include:

- **Arize:** Richard Young (Dir. Partner Solutions), Clay Miner (Head of Solutions Strategy)
- **Elastic:** Anish Mathur (Dir. Product Mgmt.), Philipp Krenn (Dir. DevRel)
- **Fivetran:** Elijah Davis (Lead Solution Architect), Andrew Madson (Principal DevRel)
- **GitLab:** Regnard Raquedan (Sr. Solutions Architect), Nick Veenhof (Dir. Contributor Success)
- **MongoDB:** Daoud Farooqi (Partner Solutions Architect), Gaurab Aryal (Sr. PM)
- **Dynatrace:** Sean O'Dell (Principal PMM, DX), Jeff Blankenburg (Principal Dev Advocate)
- **Google:** Khushan Adatiya (SWE), Rich Deken, Jess Ambriz, Jon Pawlowski, Saurabh Kumar, George Keller, Merlin Yamssi (all Cloud Partner Engineers / ISV Partner Engineers)

**Insight:** Heavy partner-engineering and DevRel presence on the panel = judges who will respect _real_ integration depth over flashy UI. A bunch of these people have personally written the SDK docs you'll be using. Show them you understood the SDK, don't just call one method.

---

## Special winner-verification requirements

Per Section 8:

- The award is subject to **identity, qualifications, and role verification**.
- "No Submission or individual shall be deemed a winning Submission or winner until their post-competition prize affidavits have been completed and verified, even if prospective winners have been announced verbally or on the competition website."
- **W-9 (US) or W-8BEN (non-US)** required.
- Cash mailed to winner address or wired to bank account; **prize takes up to 60 days** after Required Forms are received.

For Abu (international, blockchain-native): W-8BEN form will be required, and the cash will come via wire. Verify your bank can receive international USD wires; some Nigerian banks gate this behind specific account types.

---

## Eligibility cliff-notes

- **Age:** age of majority in your jurisdiction (20+ in Taiwan)
- **Excluded countries:** Italy, Brazil, Quebec, Crimea, Cuba, Iran, Syria, North Korea, Sudan, Belarus, Russia, the Crimea/Donetsk/Luhansk regions of Ukraine, Afghanistan, Antarctica, China, Djibouti, Iraq, Kazakhstan, Somalia, Venezuela, Vietnam, Western Sahara
- **Excluded persons:** OFAC Specially Designated Nationals, Commerce Denied Persons; employees/contractors of any sponsor, partner, or Devpost
- **Internet access:** required as of 2025-09-16

For Abu: no eligibility issue (Nigeria not on the list).

---

## What this means strategically

1. **Treat tracks as separate competitions.** A "good" project in a crowded track loses to a "less good" project in an empty track.
2. **Submit multiple times only if each project is genuinely distinct.** Don't try to game multi-track entry with a re-skinned same agent — Devpost reviewers flag this.
3. **The video is judging-window insurance.** Trials expire (Elastic 14d, Fivetran 14d, Dynatrace 15d) during judging. Devpost FAQ explicitly says: _"Judges evaluate your submission based on what you've submitted (project URL, demo video, repo, etc.). As long as your video and other submitted assets clearly show [partner] working end-to-end in your project, the trial expiring before July 6 won't affect your judging eligibility."_ So the 3-min video is non-negotiable quality work.
4. **Stage-1 automated scans likely look for banned dep names.** Scrub your `package.json` / `requirements.txt` / `Pipfile` for any reference to `anthropic`, `claude`, `cursor`, `copilot`, `openai`, `langchain` (as primary), `langgraph`, `llamaindex` before submit.
