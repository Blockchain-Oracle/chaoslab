// Step 4 — GitLab pointer. Honest "coming next" surface (the real OAuth
// connect ships with story-9.17 / Wave C). Tells the user what the feature
// will do, doesn't pretend it exists yet, and the Next button advances —
// the wizard never blocks on a feature that isn't live.

export function StepGitlab() {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        GitLab connection · coming with Wave C
      </div>
      <h2 className="display" style={{ fontSize: 32, marginBottom: 14 }}>
        File hardening recipes straight into your repo.
      </h2>
      <p style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.7, marginBottom: 20 }}>
        When you finish an audit, the patcher generates a hardening recipe — prompt patches, tool
        validation diffs, regression test cases. In the next wave you&apos;ll be able to file that
        recipe as a GitLab merge request to your repo with one click.
      </p>
      <div
        className="card"
        style={{
          padding: '18px 22px',
          marginBottom: 20,
          borderLeft: '3px solid var(--ember-deep)',
          borderRadius: '0 var(--r-lg) var(--r-lg) 0',
        }}
      >
        <div
          className="mono"
          style={{
            fontSize: 10.5,
            letterSpacing: '0.12em',
            color: 'var(--ember-deep)',
            marginBottom: 10,
          }}
        >
          HOW IT&apos;LL WORK
        </div>
        <ul
          style={{
            margin: 0,
            paddingLeft: 18,
            fontSize: 13,
            lineHeight: 1.75,
            color: 'var(--ink-2)',
          }}
        >
          <li>
            Connect via OAuth from <em>Settings</em> · per-account, no shared service token.
          </li>
          <li>
            <strong>Review first</strong>, file second — the MR button lives on the report&apos;s
            recipe page, not in the audit pipeline. No surprise merges.
          </li>
          <li>
            The MR only <em>adds</em> files under <code>phoenix-audit/</code> in your repo. We never
            read or modify your code.
          </li>
        </ul>
      </div>
      <p className="mono muted" style={{ fontSize: 11.5, lineHeight: 1.7 }}>
        Skip this step for now — when GitLab connect ships, you&apos;ll see a banner pointing you at
        Settings.
      </p>
    </div>
  )
}
