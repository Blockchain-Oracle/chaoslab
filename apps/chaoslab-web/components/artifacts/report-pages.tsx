import { Seal } from '@/components/ui/seal'
import { A } from '@/components/ui/link'
import { Wordmark } from '@/components/ui/wordmark'
import { Citation, Verdict } from '@/components/ui/stamps'
import { CLUSTER_SET, HERO_RUN, TESTS, fmtDate } from '@/lib/fixtures'
import { LockedParagraph } from './locked-paragraph'

export type ReportPageId = 'cover' | 'exec' | 'tests' | 'clusters' | 'recipe' | 'appendix'

export interface ReportPageDef {
  id: ReportPageId
  label: string
}

export const REPORT_PAGES: ReportPageDef[] = [
  { id: 'cover', label: 'Cover & attestation' },
  { id: 'exec', label: 'Executive summary' },
  { id: 'tests', label: 'Adversarial tests (6)' },
  { id: 'clusters', label: 'Failure clusters' },
  { id: 'recipe', label: 'Hardening recipe' },
  { id: 'appendix', label: 'EU AI Act mapping' },
]

const COVER_ROWS: ReadonlyArray<[string, string]> = [
  ['Audit run', HERO_RUN.id],
  ['Target agent', HERO_RUN.targetUrl],
  ['Commit', HERO_RUN.commitSha],
  ['Framework', HERO_RUN.framework + ' · ' + HERO_RUN.frameworkDetail],
  ['Filed', fmtDate(HERO_RUN.createdAt)],
  ['Signing key', 'Cloud KMS · SHA-256 4B:9E:F1:0A'],
]

const EXEC_STATS: ReadonlyArray<[string, string]> = [
  ['6', 'tests'],
  ['3 / 3', 'pass / fail'],
  ['1', 'root cause'],
  ['87.3 s', 'wall-clock'],
]

const APPENDIX_ROWS: ReadonlyArray<[string, string, string]> = [
  ['Article 9', 'Risk management system', '1 finding'],
  ['Article 14', 'Human oversight', '1 finding'],
  ['Article 15', 'Accuracy, robustness, cybersecurity', '1 finding'],
  ['Article 12', 'Record-keeping', 'satisfied via Phoenix traces'],
  ['Article 72', 'Post-market monitoring', 'see continuous monitoring'],
]

interface ReportPageProps {
  page: ReportPageId
  signed: boolean
}

export function ReportPage({ page, signed }: ReportPageProps) {
  if (page === 'cover') {
    return (
      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 46,
          }}
        >
          <Wordmark size={15} glyph={17} />
          <span className="mono muted" style={{ fontSize: 10 }}>
            {HERO_RUN.id}
          </span>
        </div>
        <div className="kicker" style={{ marginBottom: 14 }}>
          Signed audit report
        </div>
        <h2 className="display" style={{ fontSize: 30, marginBottom: 30 }}>
          Prior-Authorization Agent
          <br />
          <em>EU AI Act · high-risk system</em>
        </h2>
        {COVER_ROWS.map(([k, v]) => (
          <div key={k} className="leader-row" style={{ padding: '4.5px 0' }}>
            <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{k}</span>
            <span className="leader-fill"></span>
            <span className="mono" style={{ fontSize: 10.5 }}>
              {v}
            </span>
          </div>
        ))}
        {/* Locked texts render VERBATIM from the canonical fixtures —
            docs/run-config-schema.md §"Default-mode variant" and
            docs/header-convention.md §"Audit-report warning". No rewording
            permitted (verbatim-lock discipline; only declared placeholders
            may substitute — here {N} = 1 for probe 06). */}
        <LockedParagraph title="DATA RESIDENCY — DEFAULT HOSTING VARIANT">
          Audit traces are retained in Phoenix Audit&apos;s hosted Phoenix project for 24 hours
          after this report&apos;s cryptographic signature is emitted, then cryptographically erased
          via Cloud KMS key-shred. Phoenix Audit acts as a GDPR Article 28 data processor for the
          duration of the retention window. This signed PDF is the durable artifact; all underlying
          probe-and-response data is destroyed after the retention window closes.
        </LockedParagraph>
        <p
          className="mono"
          style={{
            fontSize: 9.5,
            color: 'var(--ink-3)',
            margin: '-6px 0 8px',
            letterSpacing: '0.04em',
          }}
        >
          Erasure requests (GDPR Art. 17): erasure@phoenix-audit.example · honored within 72 h
        </p>
        <LockedParagraph title="HEADER CONVENTION WARNING — INCLUDED FOR THIS RUN">
          Target did not signal it honored the X-Phoenix-Audit-* headers (`phoenix_audit.honored =
          true` was absent from 1 probe-response spans). Side-effecting tool calls during this audit
          run MAY have been executed for real against the target. To opt into dry-run behavior, the
          target must read `X-Phoenix-Audit-Dry-Run` and short-circuit side-effecting tools when its
          value is `true`, AND emit `phoenix_audit.honored = true` as a span attribute on every
          response.
        </LockedParagraph>
        {signed ? (
          <div
            style={{
              position: 'absolute',
              right: 70,
              bottom: 64,
              transform: 'rotate(-8deg)',
              filter: 'drop-shadow(0 6px 16px rgba(28,23,18,0.2))',
            }}
            className="verdict-in"
          >
            <Seal size={120} spin={false} />
          </div>
        ) : null}
      </div>
    )
  }

  if (page === 'exec') {
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 14 }}>
          Executive summary — board-ready, unedited
        </div>
        <h2 className="serif" style={{ fontSize: 24, marginBottom: 18 }}>
          Three failures. One root cause. Patched.
        </h2>
        <p
          style={{
            fontSize: 13.5,
            lineHeight: 1.75,
            color: 'var(--ink-2)',
            marginBottom: 18,
            textWrap: 'pretty',
          }}
        >
          On 9 June 2026, Phoenix Audit ran a six-test adversarial battery against the
          Prior-Authorization Agent under the EU AI Act high-risk profile. Three tests passed. Three
          failed — and all three failures trace to a single root cause: the agent submits
          authorizations on unvalidated input. A hardening recipe was generated in 4.1 seconds and
          filed as merge request !214 with regression tests.
        </p>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            borderTop: '1px solid var(--ink)',
          }}
        >
          {EXEC_STATS.map(([v, l]) => (
            <div key={l} style={{ padding: '14px 12px 0 0' }}>
              <div className="serif num" style={{ fontSize: 24 }}>
                {v}
              </div>
              <div
                className="mono muted"
                style={{
                  fontSize: 9.5,
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  marginTop: 4,
                }}
              >
                {l}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (page === 'tests') {
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 18 }}>
          Adversarial test entries
        </div>
        {TESTS.map((t) => (
          <div
            key={t.n}
            style={{
              borderBottom: '1px solid var(--hairline-soft)',
              padding: '11px 0',
              display: 'flex',
              gap: 10,
              alignItems: 'center',
            }}
          >
            <span className="mono muted" style={{ fontSize: 10 }}>
              {String(t.n).padStart(2, '0')}
            </span>
            <span style={{ fontSize: 12.5, flex: 1 }}>{t.name}</span>
            <Citation>{t.citation}</Citation>
            <span className="tag" style={{ fontSize: 9.5 }}>
              {t.mode}
            </span>
            <Verdict v={t.verdict} />
          </div>
        ))}
        <p className="mono muted" style={{ fontSize: 9.5, marginTop: 14, lineHeight: 1.7 }}>
          Each entry in the full report includes the prompt sent, the agent&apos;s response, the
          judge verdict, the regulatory article violated, and the session shape (3 single-turn · 3
          two-turn).
        </p>
      </div>
    )
  }

  if (page === 'clusters') {
    const c = CLUSTER_SET.clusters[0]
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 18 }}>
          Failure clusters
        </div>
        {c ? (
          <div
            style={{
              border: '1px solid var(--hairline)',
              borderLeft: '3px solid var(--ember-deep)',
              padding: '14px 18px',
              borderRadius: '0 3px 3px 0',
            }}
          >
            <div
              className="mono"
              style={{
                fontSize: 10,
                color: 'var(--ember-deep)',
                letterSpacing: '0.12em',
                marginBottom: 8,
              }}
            >
              {c.clusterId} · {c.failureCount} FAILURES
            </div>
            <p className="serif" style={{ fontSize: 15, lineHeight: 1.55 }}>
              {c.rootCause}
            </p>
            <div className="mono muted" style={{ fontSize: 10, marginTop: 10 }}>
              spans: {c.spanIds.join(' · ')}
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  if (page === 'recipe') {
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 18 }}>
          Hardening recipe (excerpt)
        </div>
        <p
          style={{
            fontSize: 13,
            color: 'var(--ink-2)',
            lineHeight: 1.7,
            marginBottom: 14,
          }}
        >
          Two prompt patches, two tool validation diffs, three regression test cases. Estimated
          resilience improvement +62%.
        </p>
        <A to={'recipe/' + HERO_RUN.recipeId} className="span-link" style={{ fontSize: 12 }}>
          Open the full hardening recipe view →
        </A>
      </div>
    )
  }

  // appendix
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 18 }}>
        Regulatory framework mapping — EU AI Act
      </div>
      {APPENDIX_ROWS.map(([a, t, n]) => (
        <div key={a} className="leader-row" style={{ padding: '7px 0' }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--ember-deep)', width: 78 }}>
            {a}
          </span>
          <span style={{ fontSize: 12.5 }}>{t}</span>
          <span className="leader-fill"></span>
          <span className="mono muted" style={{ fontSize: 10.5 }}>
            {n}
          </span>
        </div>
      ))}
    </div>
  )
}
