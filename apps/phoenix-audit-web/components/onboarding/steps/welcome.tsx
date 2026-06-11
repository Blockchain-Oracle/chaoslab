// Step 1 — Welcome / what this is. The kicker establishes the genre (audit
// product, not framework), the h1 carries the verb, the body explains the
// 90-second loop and the artifacts the user will end up with. No fake
// promises — only what the product actually delivers today.

export function StepWelcome({ email }: { email: string | null }) {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        Welcome
      </div>
      <h1 className="display" style={{ fontSize: 38, marginBottom: 16 }}>
        Phoenix Audit, the AI agent that audits other AI agents.
      </h1>
      <p style={{ fontSize: 14.5, lineHeight: 1.75, color: 'var(--ink-2)', marginBottom: 18 }}>
        You point Phoenix Audit at one of your production agents. It runs a 90-second adversarial
        battery, scores every probe with an LLM-as-judge over the target&apos;s Phoenix traces,
        clusters failures into root causes, and emits a signed audit report you can file with a
        regulator.
      </p>
      <p
        className="mono"
        style={{
          fontSize: 12,
          lineHeight: 1.7,
          color: 'var(--ink-3)',
          padding: '14px 18px',
          background: 'var(--paper-2)',
          border: '1px solid var(--hairline)',
          borderRadius: 'var(--r-lg)',
          marginBottom: 20,
        }}
      >
        Signed in as <strong style={{ color: 'var(--ink)' }}>{email ?? '…'}</strong> · Four short
        questions then you&apos;re looking at your first signed report. Each step is skippable —
        anything left blank keeps the default.
      </p>
    </div>
  )
}
