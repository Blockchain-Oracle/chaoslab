// The four-step procedure.
const STEPS: ReadonlyArray<[string, string, string]> = [
  [
    '01',
    'Paste the target agent address',
    'Any AI agent reachable over the internet — Google ADK via A2A, LangChain, CrewAI, OpenAI Agents SDK, or any HTTP endpoint. Pick a regulatory framework: EU AI Act, NIST AI RMF, HIPAA, or SOC 2 + AI.',
  ],
  [
    '02',
    'The test battery fires',
    'Six adversarial tests, each citing its industry-standard source — HarmBench, OWASP LLM01, MITRE ATLAS, CARES — so a regulator sees provenance, not invention. Audit-mode headers keep side effects dry-run.',
  ],
  [
    '03',
    'Failures collapse into root causes',
    "Phoenix traces the agent's internal execution per test. The Judge clusters independent failures into root cause clusters — each with the exact trace spans that prove it.",
  ],
  [
    '04',
    'Sign and file',
    'A hardening recipe lands as a markdown patch and an optional GitLab merge request with regression tests. The audit report is signed against your Cloud KMS key and filed in your audit registry.',
  ],
]

export function Procedure() {
  return (
    <section className="shell" style={{ padding: '88px 40px' }}>
      <div className="kicker" style={{ marginBottom: 14 }}>
        The procedure
      </div>
      <h2 className="display" style={{ fontSize: 36, marginBottom: 46 }}>
        From address to signed instrument.
      </h2>
      <div
        className="procedure-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 0,
          borderTop: '1px solid var(--ink)',
        }}
      >
        {STEPS.map(([no, t, b], i) => (
          <div
            key={no}
            style={{
              padding: '22px 22px 8px 0',
              borderRight: i < 3 ? '1px solid var(--hairline)' : 'none',
              paddingLeft: i > 0 ? 22 : 0,
            }}
          >
            <div
              className="mono"
              style={{
                fontSize: 11,
                color: 'var(--ember-deep)',
                letterSpacing: '0.12em',
                marginBottom: 12,
              }}
            >
              {no}
            </div>
            <h3 className="serif" style={{ fontSize: 19, marginBottom: 10, lineHeight: 1.3 }}>
              {t}
            </h3>
            <p
              style={{
                fontSize: 13.5,
                color: 'var(--ink-2)',
                lineHeight: 1.6,
                textWrap: 'pretty',
              }}
            >
              {b}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
