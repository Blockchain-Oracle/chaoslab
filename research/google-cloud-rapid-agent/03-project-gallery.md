# Devpost Project Gallery Scrape — Google Cloud Rapid Agent Hackathon

**Hackathon:** Google Cloud Rapid Agent Hackathon (rapid-agent.devpost.com)
**Deadline:** 2026-06-11 @ 2:00pm PDT
**Scrape date:** 2026-06-02 (~9 days pre-deadline)
**Total participants registered:** **12,582**
**Total prize pool:** $60,000 ($10K per track × 6 tracks)

---

## TL;DR — Gallery state

**The project gallery is unpublished as of 2026-06-02.**

Verbatim from `rapid-agent.devpost.com/submissions` and `rapid-agent.devpost.com/project-gallery`:

> "The hackathon managers haven't published this gallery yet, but hang tight!"

This is expected pre-deadline behavior on Devpost — most hackathon hosts gate the gallery until after submissions close (here that's 2026-06-11 14:00 PDT) and finalist judging completes. The participants page requires login and is not publicly scrapable.

**0 projects visible. 12,582 participants registered. Gallery may be sparse or empty until after 2026-06-11.**

---

## URLs attempted

| URL                                                                                       | Status                                             |
| ----------------------------------------------------------------------------------------- | -------------------------------------------------- |
| https://rapid-agent.devpost.com/submissions                                               | Loads → gallery message: not yet published         |
| https://rapid-agent.devpost.com/project-gallery                                           | Loads → gallery message: not yet published         |
| https://rapid-agent.devpost.com/                                                          | Loads → overview, no gallery embed                 |
| https://rapid-agent.devpost.com/participants                                              | Loads → login required ("Please log in to browse") |
| https://devpost.com/submit-to/29711-google-cloud-rapid-agent-hackathon/manage/submissions | Submitter-only management UI (auth-gated)          |

---

## Hackathon overview (confirmed from the landing page)

- **Brief:** "Build an agent that solves a real-world challenge" using Google Cloud Agent Builder + Gemini 3, with integration to partner MCP servers.
- **Tracks (6):** Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace
- **Per-track prize structure:** 1st $5,000 / 2nd $3,000 / 3rd $2,000
- **Total prize pool:** $60,000
- **Judging criteria:** Technological Implementation, Design, Potential Impact, Quality of the Idea
- **Submission requirements:** hosted project URL + public open-source repo (with license) + ~3 min demo video + track selection + completed Devpost form
- **Deadline:** June 11, 2026 @ 2:00pm PDT

---

## Projects table (gallery template — empty)

| Name                           | Track | Description | GitHub | Website |
| ------------------------------ | ----- | ----------- | ------ | ------- |
| _(no submissions visible yet)_ | —     | —           | —      | —       |

---

## Per-track submission counts

| Track     | Visible submissions | Notes               |
| --------- | ------------------- | ------------------- |
| Arize     | 0 [UNVERIFIED]      | Gallery unpublished |
| Elastic   | 0 [UNVERIFIED]      | Gallery unpublished |
| Fivetran  | 0 [UNVERIFIED]      | Gallery unpublished |
| GitLab    | 0 [UNVERIFIED]      | Gallery unpublished |
| MongoDB   | 0 [UNVERIFIED]      | Gallery unpublished |
| Dynatrace | 0 [UNVERIFIED]      | Gallery unpublished |

---

## Top 10 by interest signal

Not available. No likes/comments/projects exposed pre-publication.

---

## Top 3 most relevant projects (deep dive)

Not available. Gallery unpublished.

---

## Track saturation verdict

**All six tracks visibly GREEN — but this is a measurement artifact, not real signal.**

| Track     | Verdict          | Reasoning                 |
| --------- | ---------------- | ------------------------- |
| Arize     | GREEN [artifact] | 0 visible, gallery hidden |
| Elastic   | GREEN [artifact] | 0 visible, gallery hidden |
| Fivetran  | GREEN [artifact] | 0 visible, gallery hidden |
| GitLab    | GREEN [artifact] | 0 visible, gallery hidden |
| MongoDB   | GREEN [artifact] | 0 visible, gallery hidden |
| Dynatrace | GREEN [artifact] | 0 visible, gallery hidden |

### Real saturation prediction (priors-based, since gallery is dark)

With 12,582 registered participants and a typical Devpost completion rate of 4–8% for short hackathons (see ADK Hackathon: 10,400 participants → 477 submissions = 4.6%; Vertex AI: 3,637 → 180+ = 5%), **expect roughly 500–1,000 total submissions** by 2026-06-11.

Assuming track selection skews toward well-known brands, predicted per-track distribution:

| Track     | Predicted submissions | Predicted saturation | Reasoning                                                                          |
| --------- | --------------------- | -------------------- | ---------------------------------------------------------------------------------- |
| MongoDB   | 150–300               | RED (predicted)      | Largest dev mindshare among the six; documented common use case (RAG, agent state) |
| GitLab    | 100–200               | RED (predicted)      | Familiar, plus active GitLab AI Hackathon community already on Devpost             |
| Elastic   | 80–150                | YELLOW (predicted)   | Mid-tier name recognition; search/RAG angle is well-trodden                        |
| Dynatrace | 50–100                | YELLOW (predicted)   | Observability is niche but trending in agent ops                                   |
| Fivetran  | 40–80                 | YELLOW (predicted)   | Data-pipeline angle is narrow; fewer hackers will know it                          |
| Arize     | 30–70                 | GREEN (predicted)    | Smallest dev mindshare of the six; specialist tool (LLM observability/evals)       |

### Least-crowded recommendation

**Arize** is the least-crowded predicted lane.

Why it's interesting for Abu specifically:

- Arize = LLM observability + eval tooling. Their MCP server likely exposes trace inspection, eval result querying, and root-cause analysis tools.
- "Agent that uses Arize to debug agents" is a natural recursive wedge (agent meta-tooling) — judges love this kind of conceptual cleanness.
- Smaller crowd means lower bar to top-3 ($5K/$3K/$2K still gives the same per-track payout as MongoDB).

**Second-best:** Fivetran. Data-pipeline orchestration agent is a real-world enterprise use case judges can defend.

**Avoid (predicted):** MongoDB — it'll be the default lazy choice for every "agent + RAG" submission. Hard to stand out without strong domain wedge.

---

## What to do next

1. **Re-check the gallery starting 2026-06-12** (day after deadline) and weekly thereafter. Devpost typically publishes within 1–2 weeks of close.
2. **Don't wait** to pick the track — gallery saturation data won't arrive until after submission. Use the predicted-saturation table above + Abu's domain fit.
3. **Track competing builders via X/Twitter** — the `sahil-x` skill can scan for `#RapidAgentHackathon` or `@arizeai @mongodb` posts mentioning the hackathon. Real-time signal beats the dark gallery.

---

## Sources

- [Hackathon landing page](https://rapid-agent.devpost.com/)
- [Submissions page (empty)](https://rapid-agent.devpost.com/submissions)
- [Project gallery (empty)](https://rapid-agent.devpost.com/project-gallery)
- [Participants page (login required)](https://rapid-agent.devpost.com/participants)
- Prior-hackathon participation→submission ratio basis: [ADK Hackathon results](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/), [Vertex AI Agent Builder Hackathon](https://googlevertexai.devpost.com/)
