# Supported audit targets

Phoenix Audit drives an arbitrary A2A (Agent-to-Agent) agent and produces
a signed compliance report. We ship **two audit modes**; the wizard picks
which one runs based on what the target exposes.

## Audit modes

| Mode                    | When                                                                    | What runs                                                                                                                                                                                                                                                                               | What the verdict means                                                                                                                                                         |
| ----------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Black-box (default)** | Any public A2A agent. Card discovery succeeds; `/hooks/adk` is absent.  | Adversarial probes sent over A2A; the agent's response is judged by `phoenix.evals` LLM-as-judge (Gemini 3.5 Flash) with rubrics keyed per fault class. F2 prompt-injection + F3 context-poisoning run; F1 + F4 surface as disclosed-skip because they need server-side hook injection. | Score per probe (`refused` / `complied`, `rejected` / `adopted`) with the judge LLM's explanation quoted on the signed-report cover. Real evaluation against response content. |
| **Deep (instrumented)** | Target ships Phoenix spans + exposes `/hooks/adk` (the 3-line snippet). | Fault hooks register against the target's own callbacks (malformed tool returns, prompt-rewrite, history-insert, artificial latency). Spans flow to our Phoenix project. Judge fetches them by trace id and applies rubrics over span attributes.                                       | Score per probe with span-level evidence + root-cause clustering. Full audit.                                                                                                  |

Both modes:

- Discover the card via dual-convention probe (`/.well-known/agent-card.json` then `/.well-known/agent.json`).
- Run the same SSRF + body-size guards.
- Produce the same signed PDF + JSON + signature, with the mode declared on the cover.

## What works today

| Target shape                                                                   | Discovery path                 | Audit verdict                                                                                            |
| ------------------------------------------------------------------------------ | ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Public A2A v1.0 (per spec at <https://a2a-protocol.org/latest/specification/>) | `/.well-known/agent-card.json` | Full audit, full skill coverage                                                                          |
| Pre-v1 / Codelabs-style cards (`methods` array, no `skills`)                   | either well-known              | Basic audit only — degraded mode, no skill-by-skill coverage; warning printed on the signed-report cover |
| Legacy RFC-8615 path                                                           | `/.well-known/agent.json`      | Same as the v1.0 path if the card validates                                                              |

The wizard at `/new` previews the verdict the moment you paste a URL —
no need to run a full 90-second audit just to find out the card is
unreachable.

## Detected but not driven (yet) — credentialed targets

These targets pass discovery and the wizard names them, but the audit
itself needs credentials we don't yet collect, so the run will 401 / 402
mid-flight. The wizard surfaces an amber ⚠ hint before you click RUN so
you don't waste a 90-second cycle.

| Auth scheme                 | Card field                                                      | What an audit needs                                                                                                                                                                                                                                                |
| --------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `bearer` (JWT)              | `securitySchemes.http` (`scheme: bearer`)                       | The user's bearer token                                                                                                                                                                                                                                            |
| `apiKey` (header)           | `securitySchemes.apiKey`                                        | The user's API key                                                                                                                                                                                                                                                 |
| `oauth2`                    | `securitySchemes.oauth2`                                        | OAuth client config + delegated consent                                                                                                                                                                                                                            |
| `mtls`                      | `securitySchemes.mutualTLS`                                     | Client cert + key                                                                                                                                                                                                                                                  |
| `x402` (stablecoin paywall) | `extensions[].uri = https://github.com/google-a2a/a2a-x402/...` | A funded wallet capable of EIP-3009 signing (typically USDC on Base); the spec at <https://x402.org/x402-whitepaper.pdf> explicitly forbids LLMs from holding private keys, so Phoenix would coordinate with an external signer rather than custodying keys itself |

BYO-token (bearer / apiKey / oauth2 / mtls) + a funded-wallet signer
hand-off (x402) are both on the roadmap. They're not in this milestone
because shipping them well needs key-management UX we haven't designed
yet; getting it wrong is worse than not shipping it.

## Out of scope

- Targets that don't expose a well-known agent card at all. The wizard
  reports "no AgentCard at /.well-known/agent-card.json or
  /.well-known/agent.json" so you can copy the message into a support
  ticket with the agent's owner.
- Targets behind an enterprise SSO portal where the well-known path
  itself is gated. Card discovery fails the same way as the previous
  case; same support-ticket workflow.

## References

- A2A spec — <https://a2a-protocol.org/latest/specification/>
- a2a-x402 extension — <https://github.com/google-agentic-commerce/a2a-x402>
- x402 protocol — <https://x402.org/> · whitepaper at <https://x402.org/x402-whitepaper.pdf>
