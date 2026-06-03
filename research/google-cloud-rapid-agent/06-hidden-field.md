# 06 — Hidden Field: Track Saturation Verdict

**Question this file answers:** Which of the 6 partner-bucket prize pools is least crowded, given the same $10K payout per bucket?

**Same money, different odds.** Pick the bucket with the worst-funded competition.

---

## Raw data from the gallery scrape (2026-06-02)

Per `03-project-gallery.md`:

- **Devpost project gallery:** not publicly visible until after the deadline (2026-06-11). Standard Devpost behavior.
- **Participants registered:** ~12,582 (as of scrape).
- **Predicted final submission count:** ~500-1,000, based on the ADK Hackathon's 4.6% participation-to-submission ratio.
- **No live per-track count available.**

This means saturation is **inferred from priors and friction signals**, not directly observed.

---

## Inferred per-track saturation

### How to read this

- **GREEN** = predicted low submission volume, friction or specialization deters lazy entries
- **YELLOW** = mid-volume, some friction
- **RED** = predicted high submission volume, lazy-default entry point

| Track         | Verdict       | Why                                                                                                                                                                          |
| ------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Arize**     | 🟢 **GREEN**  | Requires code-first ADK (not visual). Phoenix is observability — not the first thing most builders think of for "agent that does X". Cerebral angle deters template-rippers. |
| **Elastic**   | 🟡 **YELLOW** | 14-day trial squeeze deters builders who start late. Kibana/ES                                                                                                               | QL learning curve. But search is a recognizable, achievable angle. |
| **Fivetran**  | 🟡 **YELLOW** | 14-day trial squeeze. Concept (ELT data pipelines) is less obvious to AI-agent newcomers. Likely smaller submission count than MongoDB.                                      |
| **GitLab**    | 🔴 **RED**    | DevOps automation is the highest-recognition agent use case ("agent that triages MRs!"). Official MCP server is well-documented. Many builders will pick this default.       |
| **MongoDB**   | 🔴 **RED**    | Free Atlas tier + 40+ MCP tools + Gemini CLI extension = lowest-friction track. Will be the most-popular default for solo devs and AI-newcomer teams.                        |
| **Dynatrace** | 🟢 **GREEN**  | Highest concept ladder (true production observability). Requires real telemetry data (not just mock JSON). Smallest predicted submission volume.                             |

---

## What this implies (track-EV math)

**Assumption:** ~600 total submissions across 6 tracks (mid-range estimate).

If submissions distributed by saturation prediction:

| Track         | Predicted % of submissions | Est. submissions in track | 1st-place probability (1/N for a contender-quality entry) |
| ------------- | -------------------------- | ------------------------- | --------------------------------------------------------- |
| MongoDB       | 28%                        | 168                       | ~0.6%                                                     |
| GitLab        | 24%                        | 144                       | ~0.7%                                                     |
| Elastic       | 16%                        | 96                        | ~1.0%                                                     |
| Fivetran      | 14%                        | 84                        | ~1.2%                                                     |
| **Arize**     | **10%**                    | **60**                    | **~1.7%**                                                 |
| **Dynatrace** | **8%**                     | **48**                    | **~2.1%**                                                 |

(These are rough — actual distribution will skew further from uniform once we see the gallery post-deadline.)

**Verdict:** Picking Dynatrace or Arize over MongoDB roughly **3× your odds** at the same $10K bucket. That's a huge structural edge.

---

## Caveats to the EV math

1. **Probabilities aren't uniform.** Judges score 4 criteria with weight. A 1.7% raw probability assumes "if you build a contender-quality entry." For a solo dev shipping in 9 days, building a contender-quality entry is the hard part, not the bucket selection.
2. **Quality ≠ track-fit.** Arize and Dynatrace reward sophistication (genuine eval loops, real telemetry). A great MongoDB-as-a-K/V demo loses to a _credible_ Phoenix-eval-loop demo even if the MongoDB demo has more LOC.
3. **The "predicted least crowded" tracks have higher floor difficulty.** That's why they're predicted least crowded. Don't pick Dynatrace if you can't get OneAgent collecting real data in the first 48 hours.

---

## Final ranking for "lane you should pick"

For Abu specifically — blockchain-native solo dev, 9 days, needs to learn the stack while building:

1. **🟢 Arize** — best lane-EV math + naturally aligned with Abu's "I already use AI coding tools" mental model (recursive: build an agent that observes other agents). Phoenix Cloud is free; no trial clock. Code-first ADK adds learning, but it's also the more transferable skill.

2. **🟢 Dynatrace** — better lane-EV math than Arize, but **higher operational floor**. Need real OneAgent telemetry collected before recording demo video. Only pick if you have a genuine observability angle and can install OneAgent on day 1.

3. **🟡 Fivetran** — best mental-model match for blockchain devs (Fivetran connectors ~ multi-chain indexers). Trial squeeze is the killer — activate trial close to June 11 deadline and accept that judging will rely on the demo video.

4. **🔴 MongoDB** — friction-low but saturation-RED. Only if you have a strong differentiated wedge (e.g., a vector-search-driven angle that competitors will miss). Don't pick this just because it's easy.

5. **🔴 GitLab** — DevOps natives will out-execute on quality of idea. Skip unless you have specific DevOps domain experience.

6. **🟡 Elastic** — high ceiling, high learning curve. 14-day trial + Kibana + ES|QL = too much new surface area in 9 days for someone who hasn't touched Elastic before.

---

## Open questions for re-research after submission deadline

After 2026-06-11, the gallery becomes visible. Re-scrape and re-rank:

- Actual per-track submission count
- Top 10 submissions per track (gauge competition depth)
- Whether the "Arize is least crowded" prediction held
