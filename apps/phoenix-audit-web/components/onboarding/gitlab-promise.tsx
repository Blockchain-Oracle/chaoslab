// Story-9.14 redesign — GitlabPromise (O-5). Step 3 isn't an
// integration prompt today — there's nothing to connect. The screen
// instead pins the discipline (your OAuth not ours; review-first;
// additive only) and shows a specimen MR card so the operator knows
// exactly what the eventual integration will look like.

const COMMITMENTS: { n: string; t: string; d: string }[] = [
  { n: '01', t: 'Your OAuth, not ours', d: 'per-account · revocable by you' },
  { n: '02', t: 'Review-first, always', d: 'a button on the recipe page · never automatic' },
  { n: '03', t: 'Additive only', d: 'new files under phoenix-audit/ · nothing touched' },
]

export function GitlabPromise() {
  return (
    <div>
      <div style={{ marginBottom: 22 }}>
        {COMMITMENTS.map(({ n, t, d }) => (
          <div
            key={n}
            className="leader-row"
            style={{ padding: '10px 0', borderBottom: '1px solid var(--hairline-soft)' }}
          >
            <span>
              <span className="doc-section-no">{n}</span>
              <span className="serif" style={{ fontSize: 16, marginLeft: 10 }}>
                {t}
              </span>
            </span>
            <span className="leader-fill" />
            <span className="mono muted" style={{ fontSize: 10.5 }}>
              {d}
            </span>
          </div>
        ))}
      </div>
      <div className="promise-specimen">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            marginBottom: 10,
            flexWrap: 'wrap',
          }}
        >
          <span
            className="mono"
            style={{
              fontSize: 9.5,
              letterSpacing: '0.16em',
              color: 'var(--ink-3)',
              flex: 1,
              whiteSpace: 'nowrap',
            }}
          >
            SPECIMEN · THE MERGE REQUEST TO COME
          </span>
          <span className="stamp neutral" style={{ fontSize: 9 }}>
            Not live yet
          </span>
        </div>
        <div className="mono" style={{ fontSize: 11.5, marginBottom: 4 }}>
          Merge request ·{' '}
          <span style={{ color: 'var(--ember-deep)' }}>phoenix-audit/harden-cluster_a3f81c2e</span>
        </div>
        <div className="mono muted" style={{ fontSize: 10.5 }}>
          +2 files added · 0 modified · 0 read · review &amp; merge stays with you
        </div>
      </div>
    </div>
  )
}
