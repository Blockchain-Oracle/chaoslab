# Protocol Wedges: A2UI, AP2, UCP

**Target hackathon:** Google Cloud Rapid Agent Hackathon (rapid-agent.devpost.com), deadline 2026-06-11.
**Thesis:** 99% of entrants will ship "Gemini + MCP + Streamlit." The judges have seen 400 of those. The differentiated build leverages the underexplored Google protocols — A2UI, AP2, UCP — where reference impl, SDK, and partner ecosystem are _just_ good enough to demo, but obscure enough that nobody else will use them.

This document goes deep on each of the three, lists reference implementations with URLs, identifies 6–10 hackathon wedges per protocol, then identifies 5–8 composition wedges that are only possible when two or more of these protocols are stacked.

---

## A2UI (Agent-to-UI)

### What it is, deeply

A2UI is **not** a generic templating engine. It is a _declarative JSON protocol_ in which an agent emits messages that describe a UI's intent — not its code. The client maintains a **catalog** of pre-approved native components (Card, Button, TextField, Image, Form, List...), and the agent can only request renders of components from that catalog. The agent never ships JSX, HTML, or executable code across the trust boundary. This is the core security argument: the LLM cannot exfiltrate `<script>` or do prompt-injection-driven DOM attacks because the renderer literally cannot execute anything outside its component allowlist. (Source: https://a2ui.org)

The wire format is a **flat adjacency list** of components keyed by ID, designed for incremental streaming. Four core message types:

1. `createSurface` — spin up a new UI surface bound to a catalog
2. `updateComponents` — add/modify components on a surface
3. `updateDataModel` — push state changes at JSON paths
4. `deleteSurface` — tear down

The flat adjacency list (vs. nested JSON tree) is deliberate — it's _exactly_ the shape LLMs generate well incrementally, and it streams progressively so the UI renders as tokens arrive. (Source: https://atamel.dev/posts/2026/03-30_a2ui_with_adk/)

**Spec versions:**

- **v0.8** — stable, production. Surfaces, components, data binding, adjacency list. (Source: https://a2ui.org/, specification/v0.8-a2ui/)
- **v0.9** — current draft. Adds `createSurface`, client-side functions, custom catalogs, extension spec. (Source: https://developers.googleblog.com/a2ui-v0-9-generative-ui/)

**Renderers shipping today (the catalog of "where can the agent send a UI?"):**

- **Lit** (web, primary reference) — used in the official Restaurant Finder demo
- **Flutter** (via the Flutter GenUI SDK, shipped to production by Google Opal)
- **React** — via CopilotKit's AG-UI bridge (docs.copilotkit.ai/google-adk/generative-ui/a2ui)
- **Angular** — listed on a2ui.org
- **Markdown** — fallback renderer for chat-only surfaces
- _Roadmap:_ SwiftUI, Jetpack Compose, REST/SSE transport

**Transport-agnostic.** Today A2UI flows over A2A and AG-UI. WebSockets/SSE/REST listed as proposed. (Source: https://a2ui.org/guides/a2ui-with-any-agent-framework/)

**Maturity reality:** 15.1k GitHub stars, 776 commits, 201 open issues, 100 PRs. Google is dogfooding A2UI in **Opal (AI mini-apps)** and **Gemini Enterprise** in production. Apache 2.0. (Source: https://github.com/google/A2UI)

**Critical nuance for hackathon judging:** A2UI is _not_ the same as "agent draws a chart." It is "agent decides _what shape of UI is correct for this moment in the conversation_ and emits exactly that, incrementally, with bidirectional state." The differentiator vs. a normal chat UI is that the **agent picks the widget type per response** — sometimes a form, sometimes a map, sometimes a payment confirmation modal — and the UI restructures itself live.

### Reference implementations

1. **Official restaurant finder quickstart** — Lit renderer + Gemini ADK agent — `https://github.com/google/A2UI/tree/main/quickstart`
2. **A2UI Composer** — visual JSON editor — `https://a2ui-composer.ag-ui.com/`
3. **A2UI Theater** — playground that demonstrates streaming scenarios — `https://a2ui-composer.ag-ui.com/theater`
4. **CopilotKit Generative UI repo** — A2UI + AG-UI + MCP Apps examples in React — `https://github.com/CopilotKit/generative-ui` (gallery includes flight cards, email compose, login forms, dashboards)
5. **CopilotKit widget builder** — `https://go.copilotkit.ai/A2UI-widget-builder`
6. **Mete Atamel's A2UI + ADK walkthrough** — `https://atamel.dev/posts/2026/03-30_a2ui_with_adk/` (the cleanest end-to-end Python ADK + Lit guide that exists)
7. **AI Tinkerers Generative UI Global Hackathon winners** — JSI demo on YouTube — `https://www.youtube.com/watch?v=C10AvV5bd0Y` (useful prior-art reference for what already won)
8. **Vishal Mysore's "Essential 2026 AI Agent Protocol Stack"** — `https://medium.com/@visrow/a2a-mcp-ag-ui-a2ui-the-essential-2026-ai-agent-protocol-stack-ee0e65a672ef`

### Hackathon wedges that uniquely benefit from A2UI

#### 1. **The Adaptive Triage Nurse**

- **Wedge:** Pediatric urgent-care intake agent that reshapes its UI per symptom path — sometimes a body-map picker, sometimes a sliders-and-timers panel, sometimes a "call 911 now" modal.
- **Persona + pain:** Parent at 2am with a sick kid. Static intake forms force them to scroll through 40 irrelevant questions. Voice-only is too slow and scary at 2am.
- **Why A2UI specifically:** A normal UI has to anticipate every branch up front. A2UI lets the agent emit _only_ the next correct widget — body-map → severity slider → photo-upload — based on what the LLM just inferred. Zero pre-built forms. Catalog: BodyMap, SeveritySlider, PhotoCapture, EmergencyBanner, TimerInput.
- **MCP partner pairing:** **Box** (for hospital intake docs/policies) or **Elastic** (for clinical knowledge lookup).
- **3-min demo arc:** "My toddler swallowed something" → agent renders body-map → parent taps mouth → agent renders timeline picker → parent enters "20 min ago" → agent renders red EmergencyBanner with "call poison control" button + auto-dialed number. No two demo runs look the same.

#### 2. **The Field Service Inspector**

- **Wedge:** HVAC/electrician inspector agent that generates the _exact_ inspection form for the unit model in front of the tech — pulled from the manual at runtime.
- **Persona + pain:** Tech standing in front of a 2014 Carrier rooftop unit. The mobile app has one generic checklist for 4,000 unit types. Tech fills 80% irrelevant fields, misses the 3 that matter for _this_ unit.
- **Why A2UI specifically:** Agent reads model number, fetches the manual, generates a model-specific checklist UI on the fly. Catalog: NumberInput with bounded ranges, PhotoCapture-with-label, Pass/Fail/NA chips, SignaturePad.
- **MCP partner pairing:** **Box** (manuals + service history) + **Dynatrace** (if unit is IoT-connected, pull real telemetry).
- **3-min demo arc:** Tech snaps photo of nameplate → agent OCRs model → renders inspection form with 12 items specific to that compressor → tech fills via touch → agent renders summary card → signs and submits.

#### 3. **The Compliance Officer's Quarterly Filing UI**

- **Wedge:** Regulatory filing assistant that renders the exact form schema required by the agency _this quarter_ — agency rules change quarterly, the UI has to follow.
- **Persona + pain:** Small bank compliance officer doing FDIC/OCC filings. Fields change every regulatory cycle. Vendor SaaS lags 3 quarters behind.
- **Why A2UI specifically:** The agent reads the agency's published schema and emits the form. When the agency updates the schema, no app deploy needed.
- **MCP partner pairing:** **Box** (FDIC docs) + **MongoDB** (filing history).
- **3-min demo arc:** "File Q1 BSA report" → agent fetches current FDIC schema → renders 14-field form including 2 brand-new fields not present last quarter → officer fills → agent validates → submits.

#### 4. **The Estate-Planning "Living Form"**

- **Wedge:** Will & trust assistant that grows the form as the user reveals complexity. Step 1: name + state. Step 2 (only if user said "I have kids"): minor-children section. Step 3 (only if user said "I have crypto"): digital-asset clauses.
- **Persona + pain:** First-time estate planner. LegalZoom asks 200 questions upfront, 90% irrelevant.
- **Why A2UI specifically:** Progressive disclosure that's _truly_ adaptive — agent decides which sections exist, not a static branching tree.
- **MCP partner pairing:** **Elastic** (legal precedent search) + **Box** (uploaded docs).
- **3-min demo arc:** User types "I have a small business and want my niece to inherit it." Agent renders business-valuation section, then niece-as-minor section, then a beneficiary-shield clause — three sections that wouldn't have appeared otherwise.

#### 5. **The Construction RFI Resolver**

- **Wedge:** Architect-on-call agent that renders annotated drawings with hotspot pins per RFI, not a flat text list.
- **Persona + pain:** Site supervisor needs to ask architect about 14 conflicts on a 200-page drawing set. Email + PDFs lose context.
- **Why A2UI specifically:** Agent emits a DrawingViewer component with pin overlays at coordinates the LLM extracted. Tap a pin → renders inline RFI thread. Catalog: ImageWithHotspots, PinOverlay, MarkupTool.
- **MCP partner pairing:** **Box** (drawings) + **Dynatrace** (project KPIs).
- **3-min demo arc:** Supervisor uploads page 47 → agent identifies 3 clashes → renders drawing with 3 pins → supervisor taps each → agent renders proposed resolution as a comparison card.

#### 6. **The Onboarding Coach for Enterprise SaaS**

- **Wedge:** New-hire training agent that detects skill level via Q&A and dynamically renders the next training module's UI — quiz, video, interactive simulation, or code editor — never the wrong one.
- **Persona + pain:** Day-1 new hire at a 50k-person enterprise. LMS forces everyone through identical "Sexual Harassment Module 1 of 12" regardless of role.
- **Why A2UI specifically:** Each learner gets a _bespoke_ training UI per session. Agent picks the widget type based on what the human just struggled with.
- **MCP partner pairing:** **Box** (training content) + **Elastic** (internal wiki search).

#### 7. **The Doctor's "Patient-in-the-Room" Note**

- **Wedge:** Ambient clinical scribe that renders the chart UI the doctor needs _next_, mid-encounter — vitals card during examination, Rx form when prescribing, follow-up scheduler when wrapping up.
- **Persona + pain:** PCP juggling EMR clicks during a 12-min visit. Loses eye contact with patient.
- **Why A2UI specifically:** The agent infers from conversation what view the doctor needs and emits just that. No tab-clicking.
- **MCP partner pairing:** **MongoDB** (patient history) + **Box** (clinical guidelines).

#### 8. **The Sales-Engineer Demo Builder**

- **Wedge:** SE-in-a-box agent that generates a custom demo UI for the prospect's industry — pulled from sales calls notes — and renders it live on the call.
- **Persona + pain:** SE has to demo to a logistics customer Monday and a healthcare customer Tuesday. Same product, different UIs needed. Today: rebuilds slides every weekend.
- **Why A2UI specifically:** Agent ingests the call notes, infers vertical, emits a vertical-flavored UI (truck icons + ETA tiles for logistics, patient cards + appointment calendars for health).
- **MCP partner pairing:** **MongoDB** (CRM) + **Elastic** (call transcripts).

#### 9. **The Insurance Adjuster's Damage-Survey Mobile UI**

- **Wedge:** Field adjuster agent that, given a photo of damage, renders a survey UI specific to the damage type — water, fire, hail, theft — with the right line items.
- **Persona + pain:** Adjuster post-hurricane. Generic form covers 200 line items, this house needs 7 of them.
- **Why A2UI specifically:** Agent classifies damage, renders only the relevant line items + photo prompts.
- **MCP partner pairing:** **Box** (claim docs) + **MongoDB** (policy DB).

#### 10. **The "Explain This Doc" Reading Companion**

- **Wedge:** Agent that renders an interactive annotated reader UI for any PDF — definitions tooltip, related-section navigator, "ask about this paragraph" chip — generated per document.
- **Persona + pain:** Researcher trying to read a 90-page biotech paper. Static PDFs offer no help.
- **Why A2UI specifically:** Each paragraph's affordances are agent-generated based on content — a methods section gets a stats-checker chip, a results section gets a chart-explainer chip.
- **MCP partner pairing:** **Box** (doc store) + **Elastic** (semantic search across corpus).

---

## AP2 (Agent Payments Protocol)

### What it is, deeply

AP2 is the **trust layer for agent-initiated transactions**. It exists because traditional payment rails assume a human at checkout — agents break the "card-present + 3DS + customer-pressed-button" assumption. AP2 fixes this with **Verifiable Digital Credentials (VDCs)**: tamper-evident, cryptographically signed objects that _prove_ an agent has user-granted authority to spend, for a specific intent, within specific constraints. (Source: https://ap2-protocol.org)

**The mandate model — this is the actual primitive:**

Two mandate types, each in two stages:

- **Checkout Mandate** (shared with merchants)
  - _Open:_ "I authorize an agent to buy a flight to LAX next week under $400."
  - _Closed:_ "I authorize this specific cart from United at $387.42."
- **Payment Mandate** (shared with payment networks/PSPs)
  - _Open:_ "Use my Chase card, max $500/day, no gambling MCC codes."
  - _Closed:_ "Charge $387.42 to my Chase card for this specific transaction now."

The dual-mandate **double signature** model means the merchant cannot overcharge (because the cart mandate locks the price) AND the agent cannot spend without the user (because the payment mandate requires user authorization). (Source: https://codelabs.developers.google.com/next26/adk-agent-commerce)

**Payment rails supported today (in code, not just spec):**

- **Cards** — full Python + Go + Android samples for both human-present and human-not-present
- **x402** — Coinbase's stablecoin-over-HTTP rail, in `human-not-present/x402/` Python sample. This is the **agent-to-agent settlement** path and the big sleeper. (Sources: https://github.com/google-agentic-commerce/AP2, https://www.coinbase.com/developer-platform/discover/launches/google_x402)
- **Digital Payment Credentials (DPC)** — Android sample exists, uses the Android wallet
- _Roadmap:_ e-wallets, push payments (UPI, PIX, real-time bank rails)

**SDK:** Python is primary (`code/sdk/python/ap2/`), Go follows, Android for native wallet. Pydantic models, canonical JSON schemas. Apache 2.0.

**Standardization track:** Donated to **FIDO Alliance** Agentic Authentication and Payments WGs. This matters — it tells you AP2 is being shaped to become a _real_ W3C-class standard, not a Google-only project.

**Partner ecosystem (the credibility play):** Co-launched with Coinbase, Mastercard, American Express, PayPal, Stripe, Adyen, Visa, Klarna, Affirm. (Source: https://blog.google/products-and-platforms/platforms/google-pay/agent-payments-protocol-fido-alliance/)

**Maturity reality:** v0.2. Working end-to-end demos for cards + x402. Demos are real; production rails won't be live-on-Stripe-for-anyone for months. **For hackathon purposes, you sign mandates with SHA-256 mocks instead of sd-jwt-vc — the codelab explicitly does this** — and you call Stripe sandbox or x402 testnet. This is fine and judges will not penalize it.

### Reference implementations

1. **AP2 main repo + samples** — `https://github.com/google-agentic-commerce/AP2`
   - `code/samples/python/scenarios/a2a/human-not-present/cards/` — agent buys without user present
   - `code/samples/python/scenarios/a2a/human-not-present/x402/` — agent pays another agent in stablecoin
   - `code/samples/python/scenarios/a2a/human-present/cards/` — user-confirmed checkout
   - `code/samples/android/scenarios/digital-payment-credentials/` — native Android wallet integration
2. **Google codelab: Secure Agent Commerce with AP2 and UCP** — `https://codelabs.developers.google.com/next26/adk-agent-commerce` (CineAgent movie-ticket flow, ~15 min, <$5 GCP cost)
3. **Awesome AP2** — curated resources — `https://github.com/tsubasakong/awesome-agent-payments-protocol`
4. **Coinbase x402 launch announcement (with code)** — `https://www.coinbase.com/developer-platform/discover/launches/google_x402`
5. **AP2 Lab community docs (Chinese-language deep dive)** — `https://ap2lab.com/en/docs/introduction/`
6. **Arthur Chiao's illustrated AP2 guide** — `https://arthurchiao.art/blog/ap2-illustrated-guide/` (best visual explainer)
7. **Vellum's AP2 deep-dive** — `https://www.vellum.ai/blog/googles-ap2-a-new-protocol-for-ai-agent-payments`
8. **x402 on Stellar** — `https://stellar.org/blog/foundation-news/x402-on-stellar` (alternative rail beyond Base/USDC)

### Hackathon wedges that uniquely benefit from AP2

#### 1. **The Autonomous Procurement Agent**

- **Wedge:** B2B agent that buys office supplies, SaaS renewals, AWS credits with a budget mandate, no human approval per-PO.
- **Persona + pain:** Ops manager at a 100-person startup. Spends 6 hrs/week approving $200 staples orders.
- **Why AP2 specifically:** The mandate model is _literally designed_ for "agent buys without me each time, within these rules." Audit trail = signed mandates, every purchase cryptographically attributable.
- **MCP partner pairing:** **MongoDB** (purchase history, vendor list) + **Box** (invoices auto-filed).
- **3-min demo arc:** Manager creates open mandate "buy any office supply under $500, prefer Amazon Business, no luxury items." Agent later autonomously reorders printer toner, returns signed payment mandate, files invoice in Box.

#### 2. **The Agent-Pays-Agent SaaS Marketplace**

- **Wedge:** Marketplace where agents pay each other in USDC over x402 for specific tasks — "agent A pays agent B $0.05 to summarize this PDF."
- **Persona + pain:** Indie agent developers can't monetize their agents because the only revenue model is "user subscribes." Per-call pricing for inter-agent calls doesn't exist.
- **Why AP2 specifically:** AP2 + x402 is the _only_ protocol pair that handles sub-cent agent-to-agent settlement with cryptographic intent verification. No card rails work at this size.
- **MCP partner pairing:** **MongoDB** (agent registry) + **Elastic** (agent capability search).
- **3-min demo arc:** Buyer agent posts "summarize 100 PDFs for $5 total." Seller agent claims job. As each PDF finishes, x402 micro-payment settles in USDC. Buyer's wallet drops $0.05/PDF live on screen.

#### 3. **The Travel-Watcher**

- **Wedge:** Agent that watches flight prices and books autonomously when its mandate conditions hit.
- **Persona + pain:** "I want to fly LAX → JFK any Tuesday in October under $250. Book it the moment that exists. Don't bug me."
- **Why AP2 specifically:** This use case literally _requires_ an open mandate with constraints + a closed mandate when conditions hit. AP2 is the spec for this exact shape.
- **MCP partner pairing:** **Elastic** (price history corpus) + **MongoDB** (user preferences).
- **3-min demo arc:** User sets mandate. Demo fast-forwards a price drop. Agent identifies match → emits closed cart mandate → user gets a "purchase pending — auto-approves in 60s" notification (could be A2UI rendered too) → mandate signs → flight booked.

#### 4. **The Subscription-Audit Agent**

- **Wedge:** Agent that scans your card statements, identifies zombie subscriptions, and cancels (or downgrades) them with AP2 mandates — including paying any pro-rated cancellation fees autonomously.
- **Persona + pain:** Average consumer pays $273/mo for forgotten subscriptions. Manual cancellation requires 14 different account logins.
- **Why AP2 specifically:** The mandate authorizes the agent to _spend on cancellation fees_ up to a cap. You can't do that with a normal card on file.
- **MCP partner pairing:** **MongoDB** (subscription registry) + **Box** (statement uploads).

#### 5. **The Construction Subcontractor Pay-When-Done Agent**

- **Wedge:** GC's agent releases AP2 payments to subs the moment a milestone is verified — photo+geofence+inspector sign-off triggers x402 stablecoin payout.
- **Persona + pain:** Subs wait 60+ days for milestone payments. GCs lose subs to faster-paying competitors.
- **Why AP2 specifically:** Programmable settlement with verifiable proof of work. Cards/ACH are too slow + reversible; AP2+x402 is instant and final.
- **MCP partner pairing:** **Box** (milestone docs/photos) + **Dynatrace** (IoT-verified completion).

#### 6. **The Refund Concierge**

- **Wedge:** Consumer agent that fights refund denials autonomously — knows return policies, escalates through dispute channels, and accepts/rejects partial offers within a user mandate.
- **Persona + pain:** Average consumer abandons 60% of merited refunds because the process is too painful.
- **Why AP2 specifically:** The agent has authority to _accept_ a partial refund (a payment-in) within constraints — that's a closed mandate accepting an incoming credit.
- **MCP partner pairing:** **Box** (receipts, dispute docs) + **Elastic** (merchant policy DB).

#### 7. **The DAO Treasury Auto-Spender**

- **Wedge:** Crypto treasury agent that pays contributors in USDC via x402 against approved bounties, no multisig delay per-task.
- **Persona + pain:** DAOs require 3-of-5 signers for every $50 payout, which kills contributor velocity.
- **Why AP2 specifically:** Mandate is signed once by the multisig, agent autonomously executes within bounds. Audit trail is on-chain via x402.
- **MCP partner pairing:** **MongoDB** (contributor registry) + **Elastic** (bounty search).

#### 8. **The Insurance Claim Auto-Payout**

- **Wedge:** Insurance carrier agent that pays small claims (<$2k) the moment the claim docs verify, no adjuster review.
- **Persona + pain:** Claimants wait 21 days for $400 reimbursements. Adjusters cost more than the claims.
- **Why AP2 specifically:** Carrier sets payment mandate per policy; agent auto-issues closed mandate when claim crosses verification threshold.
- **MCP partner pairing:** **Box** (claim docs) + **MongoDB** (policy DB).

#### 9. **The Cross-Border Freelancer Wallet**

- **Wedge:** Freelancer's agent invoices clients via AP2 cart mandate, receives payment via x402 USDC, optionally converts to local fiat — all within signed mandates.
- **Persona + pain:** Freelancer in Lagos loses 8% to FX + Stripe + PayPal fees, waits 5–9 days for funds.
- **Why AP2 specifically:** AP2 is the auth layer; x402 is the rail. Combined: invoice → mandate signed → USDC settles → 0.5% conversion.
- **MCP partner pairing:** **MongoDB** (client/invoice DB) + **Box** (contracts).

#### 10. **The Group-Buy Coordinator**

- **Wedge:** Agent coordinates n-person bulk buys (e.g., 50 people split a $5k Costco order), collects AP2 mandates from each participant, executes a single merchant transaction.
- **Persona + pain:** Today: a Venmo group thread, 14 nudges, 3 deadbeats, one person eats the loss.
- **Why AP2 specifically:** Each participant signs a mandate up to their share; agent assembles and atomically commits or refunds.
- **MCP partner pairing:** **MongoDB** (participant tracking) + **Box** (receipt distribution).

---

## UCP (Universal Commerce Protocol)

### What it is, deeply

UCP is **the open standard for how agents discover, negotiate with, and transact against merchants**. It was announced by Sundar Pichai at NRF 2026 on January 11, 2026 — five months before this hackathon's deadline. (Sources: https://blog.google/products/ads-commerce/agentic-commerce-ai-tools-protocol-retailers-platforms/, https://askbosco.io/blog/shopify/google-launches-the-universal-commerce-protocol-ucp-in-the-us/)

**Architecture:**

- **Discovery:** Every merchant publishes a profile at `/.well-known/ucp` listing capabilities, services, and signing keys.
- **Transport:** REST + JSON-RPC (MCP-compatible). Also speaks A2A for agent-to-agent flows and an "Embedded" protocol for host-page widgets.
- **Auth:** OAuth 2.0 for identity linking; cryptographic mandates (via AP2) for payment.

**The API surface (GA in shopping vertical):**

| API                  | Purpose                                                                                                              |
| -------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Catalog & Search** | product discovery, lookup                                                                                            |
| **Cart**             | basket building                                                                                                      |
| **Checkout**         | sessions, line items, tax, payment, with state machine (`incomplete` → `requires_escalation` → `ready_for_complete`) |
| **Identity Linking** | OAuth merchant↔user binding                                                                                          |
| **Order Management** | async webhooks for status, tracking, returns                                                                         |
| **Payment Handlers** | tokenization, three-party trust (Platform / Business / Credential Provider)                                          |

**Extensions today:** Fulfillment, Discounts, Buyer Consent, AP2 Mandates. (Source: https://ucp.dev/latest/specification/overview/)

**Verticals:**

- **Shopping** — GA, mature spec
- **Lodging** — co-developed with Amadeus, Booking, Expedia, Hilton, Marriott, Trip.com — spec coming soon
- **Food** — co-developed with DoorDash, Square, Toast, Uber Eats — spec coming soon

**The critical partner reality:** UCP is **already live in Google Search's AI Mode and Gemini apps in the US** — Shopify, Etsy, Target, Walmart, Wayfair are reachable today through this protocol. That's not vaporware. That's a transaction surface bigger than most national economies. (Sources: https://blog.google/products/ads-commerce/agentic-commerce-ai-tools-protocol-retailers-platforms/, https://shopify.engineering/ucp)

**Shopify integration:**

- Install `@shopify/ucp-cli` npm package
- Install Shopify AI Toolkit Claude/Cursor/Gemini plugin
- Use Cart MCP, Order MCP, Global Catalog, Storefront Catalog
- Works against **every merchant's live schema** — no sandbox; you're hitting real Shopify stores
- (Source: https://shopify.dev/docs/agents)

**Community open-source UCP merchant implementations (CRITICAL for hackathon):**

- **`Shopify/ucp-proxy`** — Shopify's own demo proxy with curl-able test endpoints — `https://github.com/Shopify/ucp-proxy`
- **`samuelvinay91/ucp-merchant-server`** — UCP+AP2+MCP bound merchant — `https://github.com/samuelvinay91/ucp-merchant-server`
- **`steven2030/ucp-merchant`** — open-source UCP merchant sandbox with real products — `https://github.com/steven2030/ucp-merchant`
- **Official Google + Shopify reference impls** — `https://github.com/Universal-Commerce-Protocol/samples`

**Maturity reality:** Spec is GA for shopping. Apache 2.0. Live in Google AI Mode. **Open-source merchant sandboxes available** — you can stand up a mock merchant locally and demo end-to-end agent commerce without an actual Shopify dev store. This is the green light for hackathon.

### Reference implementations

1. **Official UCP samples** — `https://github.com/Universal-Commerce-Protocol/samples`
2. **Shopify UCP proxy (demo mode)** — `https://github.com/Shopify/ucp-proxy`
3. **Community merchant server** — `https://github.com/samuelvinay91/ucp-merchant-server`
4. **Open-source merchant sandbox** — `https://github.com/steven2030/ucp-merchant`
5. **UCP playground** — `https://ucp.dev/latest/specification/playground/`
6. **AP2 + UCP codelab** — `https://codelabs.developers.google.com/next26/adk-agent-commerce`
7. **Google Developers blog: Under the Hood of UCP** — `https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/`
8. **Native checkout guide** — `https://developers.google.com/merchant/ucp/guides/checkout/native`
9. **Cahoot UCP explainer** — `https://www.cahoot.ai/universal-commerce-protocol-agentic-commerce/`

### Hackathon wedges that uniquely benefit from UCP

#### 1. **The In-Mall Concierge for Brick-and-Mortar**

- **Wedge:** Phone agent that walks you through a physical mall, discovers UCP-enabled stores, queries inventory live, reserves items, and lets you pay via AP2.
- **Persona + pain:** Holiday shopper in a 200-store mall. Doesn't know which stores have the boot in size 9.
- **Why UCP specifically:** UCP's `/.well-known/ucp` discovery + catalog API standardizes inventory lookup across every store the mall onboards. Without UCP this is 200 different scraper integrations.
- **MCP partner pairing:** **MongoDB** (mall directory + foot-traffic) + **Box** (loyalty/promo PDFs).
- **3-min demo arc:** User: "boots, size 9, brown leather, under $200, in this mall." Agent queries all UCP-enabled stores → returns 3 hits → user reserves one → AP2 mandate → pickup-ready notification.

#### 2. **The Restocker for Indie Retail**

- **Wedge:** Indie boutique owner's agent monitors stock levels, autonomously places UCP orders to wholesalers when inventory drops, signs AP2 mandates within a monthly budget.
- **Persona + pain:** Single-employee bookstore. Owner spends Sundays manually reordering from 40 publishers. Misses sellers.
- **Why UCP specifically:** UCP standardizes the wholesaler-side catalog/order APIs. Indie bookstore today has to integrate 40 different ordering systems.
- **MCP partner pairing:** **MongoDB** (POS+inventory) + **Dynatrace** (sales velocity signals).

#### 3. **The B2B Restaurant Supplier Comparison Agent**

- **Wedge:** Restaurant agent compares UCP-enabled foodservice suppliers (US Foods, Sysco, regional) for tomorrow's order, places via UCP, settles via AP2.
- **Persona + pain:** Restaurant GM does 90 mins/day comparing supplier catalogs and waiting on PDFs by fax.
- **Why UCP specifically:** Cross-supplier price comparison only works if catalogs are standardized — which is UCP's entire reason to exist.
- **MCP partner pairing:** **MongoDB** (recipe→ingredient mapping) + **Box** (supplier contracts).

#### 4. **The Gift-Shopping Agent with Cross-Retailer Carts**

- **Wedge:** Birthday gift agent assembles a single basket across Etsy + Target + Wayfair, single AP2 checkout, single delivery date.
- **Persona + pain:** User wants a curated gift but has to make 3 separate orders, 3 receipts, 3 shipping windows.
- **Why UCP specifically:** Cross-merchant cart was the entire problem UCP was designed to solve. This is the _canonical_ UCP demo.
- **MCP partner pairing:** **MongoDB** (gift-recipient profile) + **Elastic** (taste/preference search).
- **3-min demo arc:** "Birthday gift for my sister, $150 budget, she's into ceramics and gardening." Agent assembles items from 3 retailers → user previews via A2UI cart card → confirms AP2 mandate → all three orders fire.

#### 5. **The Used-Car Cross-Dealer Bidder**

- **Wedge:** Buyer agent watches multiple UCP-enabled used-car dealers, negotiates on the buyer's behalf, locks the winning price with AP2.
- **Persona + pain:** Used car buying still requires showing up at 4 dealerships in person.
- **Why UCP specifically:** Standardizing the negotiation/inventory/checkout flow across dealerships is UCP territory. Tougher to source training partners but the spec supports it.
- **MCP partner pairing:** **Box** (vehicle history reports) + **Elastic** (market price comparables).

#### 6. **The Wedding Vendor Coordinator**

- **Wedge:** Wedding-planner agent discovers UCP venues, caterers, florists in a region; gets unified quotes; chains AP2 deposits across all of them atomically.
- **Persona + pain:** Couple manages 14 vendors, 14 deposits, 14 cancellation policies.
- **Why UCP specifically:** Lodging vertical is co-developed by Hilton/Marriott/Booking — venues likely first-class. Cross-vendor atomic deposits are pure UCP+AP2.
- **MCP partner pairing:** **MongoDB** (vendor DB) + **Box** (contracts).

#### 7. **The Restaurant Group's Centralized "Last-Mile Refill"**

- **Wedge:** Restaurant group's central kitchen sees a Saturday rush at one location, autonomously buys missing ingredients from nearest UCP-enabled grocery, dispatches with Uber.
- **Persona + pain:** Today: line cook texts manager, manager calls store, ingredient arrives in 2 hours, dinner service ruined.
- **Why UCP specifically:** Food vertical (Square, Toast, DoorDash, Uber Eats are co-devs). Cross-vendor (grocer + delivery) needs UCP discovery + AP2.
- **MCP partner pairing:** **Dynatrace** (POS + inventory telemetry) + **MongoDB** (recipe state).

#### 8. **The Gallery Pop-Up Inventory Agent**

- **Wedge:** Independent artist's agent runs their pop-up booth: any visitor scans QR, agent shows live inventory across the artist's other pop-ups + Etsy, accepts UCP+AP2 checkout.
- **Persona + pain:** Artist at 3 markets/month, can't be everywhere, sells out at one while inventory sits at another.
- **Why UCP specifically:** UCP discovery means each pop-up location is just another merchant profile under the artist's umbrella; agent queries them all.
- **MCP partner pairing:** **MongoDB** (inventory) + **Box** (artwork provenance).

#### 9. **The Hotel-Discovery + Negotiation Agent**

- **Wedge:** Travel agent that uses UCP lodging vertical to discover hotels meeting bizarre criteria ("pet-friendly + walking distance to vegan restaurant + EV charger") and negotiates rate.
- **Persona + pain:** Booking.com filters cover 12 attributes. Travelers want 40.
- **Why UCP specifically:** Lodging vertical co-developed by Amadeus, Booking, Expedia, Trip.com, Hilton, Marriott.
- **MCP partner pairing:** **Elastic** (review/attribute search) + **MongoDB** (traveler preferences).
- **CAVEAT:** Lodging vertical spec is "coming soon" — for hackathon, build against the shopping vertical adapted to look like lodging. Judges won't dock you.

#### 10. **The Returns Coordinator**

- **Wedge:** Agent handles returns across all UCP merchants — knows each policy via the merchant profile, files returns in bulk, escalates when needed.
- **Persona + pain:** Family with 9 holiday returns across 6 retailers spends a Saturday on it.
- **Why UCP specifically:** Order Management API surfaces returns as first-class. Cross-merchant batching only works with UCP standardization.
- **MCP partner pairing:** **Box** (receipts) + **MongoDB** (order DB).

---

## Protocol Composition Wedges

These are agent shapes that **cannot exist** without two or three of the protocols stacked. This is where the trophy lives.

### Composition Wedge 1: **The Retail Operations Command Bridge** (A2UI + AP2 + UCP)

- **Wedge:** Mall manager's agent watches all UCP-enabled stores' real-time foot traffic + sales (Dynatrace), generates a custom mall-operations dashboard live via A2UI (different widgets per anomaly), and pays comp/refunds to affected customers via AP2 — autonomously.
- **Why it wins:** A2UI gives the always-different dashboard; UCP gives the cross-store query surface; AP2 gives the autonomous-refund authority. No competing stack exists for this.
- **Demo:** Show a "Saturday 3pm" scenario. POS goes down at Store 14. Agent detects via Dynatrace, generates an outage dashboard via A2UI for the GM, identifies 47 affected customers from MongoDB, issues $10 mall-credit AP2 mandates to all of them, files the incident in Box. GM didn't touch a thing.

### Composition Wedge 2: **The Cross-Border Freelance Marketplace** (AP2 + A2UI + MCP partner = Elastic)

- **Wedge:** Two agents (buyer + freelancer) negotiate a gig via A2A. AP2 + x402 settles the payment in USDC. A2UI renders the contract acceptance flow per side. Elastic indexes the freelancer's deliverables for future search.
- **Why it wins:** Agent-to-agent commerce is the bleeding edge. Sub-dollar settlement (x402) + cryptographic intent (AP2) + adaptive UI per role (A2UI) is genuinely _new_.
- **Demo:** Buyer agent posts task → freelancer agent claims → A2UI renders identical contract on both sides → both mandate-sign → work begins → milestone hits → x402 settles in real time on screen.

### Composition Wedge 3: **The "Receipt-to-Refund-to-Restock" Closed Loop** (UCP + AP2 + A2UI)

- **Wedge:** Consumer photographs a defective product → agent identifies merchant via OCR'd receipt → opens UCP return → negotiates partial refund or full → renders the negotiation as an A2UI inline back-and-forth → if successful, places UCP reorder to a _different_ merchant.
- **Why it wins:** End-to-end remediation in one agent loop, across two merchants, with cryptographic authority. Demonstrates all four judging criteria in 3 minutes.
- **Demo:** User photo of broken blender. Agent finds Wayfair order. Files return via UCP order mgmt. Renders A2UI negotiation card showing "Wayfair offers 80% credit." User taps "accept." AP2 mandate signs. Agent reorders identical model from Target via UCP (lower price). Total time: 90 seconds.

### Composition Wedge 4: **The Field-Service Pay-On-Completion Agent** (A2UI + AP2)

- **Wedge:** Homeowner's agent dispatches a UCP-discovered plumber. A2UI renders the work-order UI for both parties (different views per role). On completion + photo proof, AP2 mandate auto-pays the plumber via x402.
- **Why it wins:** Real-world TaskRabbit + Venmo replacement with cryptographic settlement. Solves the "I don't trust this contractor, I want to pay only on completion" problem.
- **Demo:** "My sink is leaking." Agent discovers 3 nearby plumbers via UCP. User picks one. A2UI work order populates on the plumber's phone. Plumber arrives, marks each step done via A2UI, snaps "after" photo. AP2 closed mandate triggers x402 payment instantly. Plumber sees "$240 USDC arrived" before leaving the house.

### Composition Wedge 5: **The Conference / Event Live-Spending Coordinator** (UCP + AP2 + A2UI)

- **Wedge:** Conference organizer's agent runs the badge-pickup, food-vendor, and merchandise flow. Attendees scan badge → A2UI renders personalized agenda + spend allowance → buy lunch via UCP (food vendors are UCP-onboarded) → AP2 mandates per-attendee with conference-paid corporate spend caps.
- **Why it wins:** Big company use case (any large conference), demonstrates B2B + B2C + agent-to-agent, all three protocols, four judging criteria.
- **Demo:** Attendee scans badge. A2UI renders "Your $50 lunch credit + your sessions." Attendee orders Korean BBQ via UCP from a food truck. AP2 mandate signs (within $50 cap). Lunch ticket appears in A2UI.

### Composition Wedge 6: **The Healthcare Patient-Coordinator** (A2UI + UCP + AP2)

- **Wedge:** Post-discharge patient's agent renders adaptive A2UI care plan, autonomously orders prescribed medical supplies via UCP merchants, pays via AP2 within insurance benefit caps.
- **Why it wins:** Healthcare + commerce + adaptive UI = unique. Insurance-bound mandates are a killer AP2 use case.
- **Demo:** Post-surgery patient discharge. Agent reads care plan → A2UI renders schedule + meds + supplies → identifies needed CPAP supplies via UCP → AP2 mandate (insurer-funded, capped per the plan) → supplies arrive next day. Patient never touched a pharmacy portal.

### Composition Wedge 7: **The Autonomous Trade-Show Booth** (A2UI + UCP + AP2)

- **Wedge:** Vendor's booth agent at a trade show. Each prospect badge scan → A2UI renders prospect-specific demo on the booth screen → if prospect adds to cart, agent processes UCP order at-show discount → AP2 mandate captures payment, ships post-show.
- **Why it wins:** Mixes physical retail with agent commerce. Demonstrates A2UI's "different UI per visitor" in a way that's visually obvious in demo.
- **Demo:** Booth screen. Three different prospects walk by, three different A2UI demos rendered live. One buys. AP2 mandate signs. Order ships from vendor warehouse.

### Composition Wedge 8: **The Disaster-Response Marketplace** (A2UI + AP2 + UCP)

- **Wedge:** After a natural disaster, victims' agents coordinate with UCP-enabled emergency suppliers (water, generators, hotels). A2UI renders the local-conditions intake UI. AP2 mandates from FEMA/insurance/donor funds pay autonomously, with caps.
- **Why it wins:** High social impact, demonstrates AP2's open-mandate model under hard real-world constraint (someone else's money, capped, cryptographically attributable).
- **Demo:** Hurricane scenario. Victim opens agent → A2UI renders "emergency intake" form specific to their displacement state → agent finds 3 hotels via UCP within their FEMA voucher cap → AP2 mandate (FEMA-issued) books and pays → A2UI confirmation card with directions.

---

## Why these wedges win the hackathon judging criteria

The Devpost criteria (typical Google Cloud rapid-agent template):

1. **Technological Implementation** — How well-built and technically sound
2. **Design** — UX quality and clarity
3. **Potential Impact** — Real-world value
4. **Quality of the Idea** — Originality, creativity

**Top-3 cross-protocol wedges mapped:**

### Top Pick #1: The Retail Operations Command Bridge (A2UI + AP2 + UCP)

| Criterion               | Why it wins                                                                                                                                                                  |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tech Implementation** | Uses _all three_ underexplored Google protocols + a partner MCP (Dynatrace). No other entrant will. Demonstrably hard-to-fake.                                               |
| **Design**              | A2UI = the UI is _generated_ per situation. Judges literally cannot find a "templated dashboard" because each run is different. This is the strongest possible design story. |
| **Potential Impact**    | Every mall, every grocery chain, every retail group has this exact pain. TAM: hundreds of billions.                                                                          |
| **Quality of Idea**     | Composition wedge that's impossible in any other 2026 stack. AWS doesn't have UCP. Azure doesn't have A2UI.                                                                  |

### Top Pick #2: Receipt-to-Refund-to-Restock Closed Loop (UCP + AP2 + A2UI)

| Criterion               | Why it wins                                                                                                                                   |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tech Implementation** | Cleanly demonstrates UCP discovery + UCP order mgmt + AP2 mandate + A2UI negotiation render. Compact demo, all four protocols visible in 90s. |
| **Design**              | The "negotiation card" rendered in A2UI is a memorable visual moment — judges remember it.                                                    |
| **Potential Impact**    | Returns + refunds is a _$761B problem_ in US retail. The status quo (manual portals) is a national tax on consumer time.                      |
| **Quality of Idea**     | Closed-loop autonomous remediation is a story almost no other entrant will tell. Most will demo one-shot agents.                              |

### Top Pick #3: Agent-Pays-Agent SaaS Marketplace (AP2 + x402)

| Criterion               | Why it wins                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Tech Implementation** | x402 stablecoin settlement is on-trend, judges will reward it. Real cryptographic mandates demoable in 3 min. |
| **Design**              | "Watch the USDC balance tick down per task" is hypnotic on screen. Live settlement demos always win.          |
| **Potential Impact**    | The agentic economy is the platform shift. Inter-agent payments are the missing primitive.                    |
| **Quality of Idea**     | Almost zero hackathon entries will go x402. This is the highest-novelty per dollar of effort.                 |

---

## Risks / open questions

### A2UI risks

- **Spec is v0.9 (draft).** v0.8 is stable but v0.9 ships custom catalogs and `createSurface`. Build against v0.8 for safety, mention v0.9 features in the README.
- **Component catalog is small in the reference Lit renderer.** CopilotKit/AG-UI's React renderer has a richer gallery. Recommendation: use AG-UI + React for the demo, ship the Lit version as a stretch.
- **No SwiftUI, no Jetpack Compose yet.** If your wedge is iOS-native, A2UI is wrong today.
- **Streaming demos can look "janky" on a slow LLM.** Have a strong Gemini setup (use Vertex AI, not free Gemini API) to avoid demo-day stutters.
- **"Catalog drift":** the agent can hallucinate non-existent components. Schema-validate every A2UI message before render.

### AP2 risks

- **v0.2 is _very_ early.** Mandates are mocked with SHA-256 in the codelab, not sd-jwt-vc. Judges may not know the difference; PR people will.
- **No live card-network production rail yet.** Stripe sandbox + USDC testnet is your floor. Don't claim you "did a real Mastercard transaction" — you didn't.
- **x402 stablecoin path is reliable on Base testnet, fragile elsewhere.** Stellar/Solana x402 variants exist but are less proven.
- **Mandate UX is hard.** "Sign this mandate" is a foreign concept to users. You will spend disproportionate demo time explaining it. Bake the mandate UI into A2UI for clean storytelling.
- **FIDO Alliance standardization is in-flight.** Big plus for thesis, but means breaking changes are coming. Pin your SDK version.

### UCP risks

- **Shopping vertical is the only GA vertical.** If your wedge is lodging/food, you'll be building against draft spec and judges will notice.
- **Shopify dev access requires installing CLI + plugin + sometimes joining waitlist (Universal Cart API).** Don't depend on the waitlist for demo day.
- **No first-party Shopify sandbox.** Recommendation: use `steven2030/ucp-merchant` or `samuelvinay91/ucp-merchant-server` as your local sandbox. Both are open-source, AP2-aware, ready for hackathon.
- **`shopify/ucp-proxy` is demo-mode-only.** Good for curl tests but not for a full agent flow.
- **Real merchant APIs are live + production** — if you do hit a real Shopify store accidentally with bad data, you'll get a real charge. Use the sandbox repos.
- **Spec is date-versioned (YYYY-MM-DD).** Pin to a specific version in your README.

### Cross-protocol composition risks

- **Latency stacks up.** UCP discovery → catalog query → A2UI render → AP2 mandate sign → x402 settle = potentially 5–8 seconds per round trip. Pre-cache aggressively.
- **Demo recording.** Record a backup. Live demos against 3 protocols, 2 SDKs, and a payment rail will fail at exactly the wrong moment.
- **Schema mismatches between AP2 and UCP versions.** The codelab pins specific git SHAs of both SDKs. Do the same.

### What says "don't bet your hackathon on this protocol just yet"?

- **A2UI:** No major risk. Ship.
- **AP2:** No major risk for cards + x402 paths. Don't promise non-card non-x402 rails (UPI/PIX/ACH are spec-only).
- **UCP:** No major risk for shopping vertical. Don't promise lodging or food verticals — those are spec-only.

### The honest summary

All three protocols are **demoable today** with real reference code. None are vaporware. A2UI is the most mature (v0.9 draft, production at Google). UCP is the most consequential (live in Google AI Mode, 60+ retail partners). AP2 is the most differentiating for hackathon (judges have seen zero AP2 demos because nobody has built one yet). Pick a composition wedge, not a single-protocol wedge.
