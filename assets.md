# Phoenix Audit — Designer Asset Requests (Submission Pack)

Everything we need from the designer for the Devpost submission + repo. No UML, no
prescribed layouts — each entry says **what the asset must communicate** and the
designer owns the visual answer. Brand language lives in the prototype
(`Phoenix Audit.html` + `styles.css`); stay consistent with it.

## Shared brand rules (apply to every asset)

- **Brand colors** (from the prototype stylesheet): paper `#faf7f0`, ink `#1c1712`,
  ember accent `oklch(0.60 0.165 48)` (≈ `#C2611E`), ember-deep `oklch(0.47 0.14 42)`.
  Dark "chamber" surfaces use the near-black ink with ember glow accents.
- **Typefaces:** Newsreader (display serif), Instrument Sans (body), IBM Plex Mono (data).
- **Logo:** the rising-spark glyph (diamond + two spark diamonds rising off the top
  vertex) + "Phoenix Audit" wordmark, exactly as in the prototype `Glyph`/`Wordmark`.
- **Utility-format rule (Abu's standard format):** logo sits in the **top-right
  corner**, background is the **brand color** (same family as the landing page),
  every file **named exactly as specified below**.

---

## 1. `banner-utility.png` — the standard utility banner

- **Shape:** wide rectangle, **short vertical height** (landscape strip; think
  ~1500×500 or similar ratio — designer's call on exact px, but clearly wider than tall).
- **Background:** brand color (ember/paper family, same feel as the landing page).
- **Logo:** top-right corner.
- **Content:** wordmark + one line: "The AI agent that audits your other AI agents."
- **Used for:** Devpost header, README top, social posts. This is the reusable
  "normal format" Abu described — once this exists we can stamp variants from it.

## 2. `architecture-diagram.png` — the system, drawn the designer's way

Not a UML diagram. Plain-language description of what must be on it — the designer
draws it however reads best (same paper/ink/ember language, IBM Plex Mono labels
fit well). Logo top-right per the utility rule.

**What the picture has to say:**

1. A compliance officer points Phoenix Audit at a **production AI agent**
   (examples: prior-authorization bot, support copilot, voice agent).
2. Phoenix Audit itself is a **pipeline of three agents** that run in order:
   - **Injector** — fires a 6-test adversarial battery at the target agent
     (prompt injection, poisoned context, malformed tool output…), drawn from
     HarmBench / OWASP LLM Top 10 / MITRE ATLAS / CARES.
   - **Judge** — Gemini (gemini-3.5-flash) reads the target's traces in
     **Arize Phoenix** (the observability store every arrow flows through) and
     stamps each test pass/fail, then clusters the failures into root causes
     ("3 failures → 1 cause" is the hero moment).
   - **Patcher** — generates a hardening recipe (prompt patches + tool
     validation code diffs + regression tests).
3. Three artifacts come out the right side:
   - **Signed PDF audit report** (Cloud KMS Ed25519 signature — the seal),
   - **Hardening recipe**,
   - **GitLab merge request** opened on the target agent's repo.
4. Everything runs on **Google Cloud Run** (3 services: web, audit agent, target
   agent); the live audit streams to the browser over SSE in ~90 seconds.
5. Small badge row: Arize Phoenix · Google ADK · Gemini · Cloud Run · Cloud KMS · GitLab.

**One-sentence story the diagram must land:** _production agent goes in →
adversarial battery + judge + patcher run on Google Cloud with every step traced
in Phoenix → a cryptographically signed, regulator-ready audit comes out._

## 3. `og-image.png` — link-preview card (1200×630)

The prototype already ships one (`og/og-image.png`). Confirm it carries: wordmark,
the tagline, the seal, and the "Three failures. One root cause. Patch in four
seconds." line. If re-exported, keep the name `og-image.png`.

## 4. Devpost gallery shots — `gallery-01..05.png`

Five stills (Devpost gallery is the judges' first impression; each needs to be
readable at thumbnail size). Suggested set, all from the real app / prototype:

1. `gallery-01-chamber.png` — the live audit chamber mid-judge phase (verdict
   stamps landing, SSE feed ticking).
2. `gallery-02-cascade.png` — the cascade-flip moment: 3 fail dots flying into
   the single root-cause cluster.
3. `gallery-03-report.png` — signed report cover with the spinning-seal "Signed"
   state and the Cloud KMS fingerprint line.
4. `gallery-04-history.png` — audit registry with the three stat blocks
   (47 audits / 12 with findings / 11 hardened & re-passed).
5. `gallery-05-monitoring.png` — continuous monitoring schedule (the EU AI Act
   Article 72 post-market-monitoring story).

## 5. `seal.svg` — the signing seal as a standalone asset

The concentric-ring seal with rotating ring text ("PHOENIX AUDIT ·
CRYPTOGRAPHICALLY SIGNED · CLOUD KMS ·") already exists in prototype code —
export it as standalone SVG (static) + optionally a small animated variant
(GIF/WebM) for the README. Used on: PDF cover, submission page, demo video end card.

## 6. `video-endcard.png` — demo video closing frame (1920×1080)

Brand background, logo top-right, seal center, one line: product name + "Built on
Arize Phoenix & Google Cloud" + repo URL. Gives the demo video a clean last 3 seconds.

---

## Notes for Abu

- Items 3 and 5 may just be exports from what the designer already built — ask
  him to deliver them as files rather than redrawing.
- Gallery shots can be captured from the running app once the remaining surfaces
  are wired; the designer only needs to art-direct/crop them.
- If the designer wants one more expressive piece: a small **"how the audit
  flows" strip** (Injector → Judge → Patcher as three stations, same as the
  chamber pipeline) reusable in both the README and the video.
