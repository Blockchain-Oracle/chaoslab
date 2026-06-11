// Frameworks support table.
const ROWS: ReadonlyArray<[string, string, string, string]> = [
  ['Google ADK', 'Tier 1 · native', 'A2A protocol', 'Full root-cause clustering'],
  ['LangChain / LangGraph', 'Tier 2', 'HTTP + OpenInference', 'Full root-cause clustering'],
  ['CrewAI', 'Tier 2', 'HTTP + OpenInference', 'Full root-cause clustering'],
  ['OpenAI Agents SDK', 'Tier 2', 'HTTP + OpenInference', 'Full root-cause clustering'],
  ['Custom HTTP agent', 'Tier 3 · black-box', 'HTTP endpoint', 'Per-test findings, no clustering'],
]

export function Frameworks() {
  return (
    <section
      id="frameworks"
      style={{ borderTop: '1px solid var(--hairline)', background: 'var(--paper-2)' }}
    >
      <div className="shell" style={{ padding: '80px 40px' }}>
        <div className="kicker" style={{ marginBottom: 14 }}>
          Cross-framework
        </div>
        <h2 className="display" style={{ fontSize: 36, marginBottom: 12 }}>
          Audit any agent you run.
        </h2>
        <p className="muted" style={{ maxWidth: 560, marginBottom: 36, textWrap: 'pretty' }}>
          Voice agents, support copilots, prior-authorization agents, web-automation agents — if it
          answers over the internet, it can be audited.
        </p>
        <div className="frameworks-scroll">
          <table className="ledger" style={{ background: 'rgba(255,255,255,0.5)' }}>
            <thead>
              <tr>
                <th>Framework</th>
                <th>Support</th>
                <th>Transport</th>
                <th>Clustering</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([f, t, tr, c]) => (
                <tr key={f}>
                  <td className="serif" data-label="Framework" style={{ fontSize: 15.5 }}>
                    {f}
                  </td>
                  <td data-label="Support">
                    <span className="tag">{t}</span>
                  </td>
                  <td className="mono" data-label="Transport" style={{ fontSize: 12 }}>
                    {tr}
                  </td>
                  <td data-label="Clustering" style={{ fontSize: 13, color: 'var(--ink-2)' }}>
                    {c}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
