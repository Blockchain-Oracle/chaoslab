// The signed-report surface for a REAL run (story-9.11): freshly signed
// artifact downloads, honest disclosure when signing/registry failed, and a
// replay CTA when a timeline exists. No fixture preview, no signing theater.

import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'

export interface LiveReportData {
  /** Freshly signed artifact URLs from the registry (report.pdf, report.json,
   *  signature.json, events.json, recipe.md — whichever exist). */
  urls: Record<string, string>
  /** Artifacts whose URL signing failed — distinct from absent. */
  errors: Record<string, string>
  reportAvailable: boolean
  eventsAvailable: boolean
  sample: boolean
  passed: number
  failed: number
  errored: number
  transportFailed: number
  createdAt: string
  targetUrl: string
}

interface ReportPreviewProps {
  runId: string
  /** Present = the registry answered; null = unreachable (see liveError). */
  live: LiveReportData | null
  liveError: string | null
}

function Notice({ tone, children }: { tone: 'warn' | 'fail'; children: React.ReactNode }) {
  return (
    <div
      className="mono"
      style={{
        fontSize: 11,
        color: tone === 'fail' ? 'var(--fail)' : 'var(--warn, #8a6d1a)',
        border: '1px dashed currentColor',
        borderRadius: 4,
        padding: '10px 14px',
        marginBottom: 18,
      }}
    >
      {children}
    </div>
  )
}

const ARTIFACT_BUTTONS: ReadonlyArray<{ name: string; label: string; primary?: boolean }> = [
  { name: 'report.pdf', label: 'Download PDF', primary: true },
  { name: 'report.json', label: 'Signed JSON' },
  { name: 'signature.json', label: 'Signature sidecar' },
  { name: 'recipe.md', label: 'Recipe (md)' },
]

export function ReportPreview({ runId, live, liveError }: ReportPreviewProps) {
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '44px 40px 30px', maxWidth: 900 }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 14 }}>
          <A to="audits" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            AUDIT REGISTRY
          </A>{' '}
          / {runId} / signed report
        </div>

        {liveError ? (
          <Notice tone="warn">
            ⚠ LIVE REGISTRY UNAVAILABLE — this run&apos;s artifacts cannot be fetched right now. (
            {liveError})
          </Notice>
        ) : null}
        {live && !live.reportAvailable ? (
          <Notice tone="warn">
            ⚠ NO SIGNED REPORT FOR THIS RUN — generation was skipped (see the run&apos;s event log).
          </Notice>
        ) : null}
        {live && Object.keys(live.errors).length > 0 ? (
          <Notice tone="fail">
            ✕ DOWNLOAD LINKS TEMPORARILY UNAVAILABLE for: {Object.keys(live.errors).join(', ')} —
            re-signing failed; reload to retry.
          </Notice>
        ) : null}

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 18, marginBottom: 34 }}>
          <div style={{ flex: 1 }}>
            <h1 className="display" style={{ fontSize: 36 }}>
              Signed audit report.
              {live?.sample ? (
                <span
                  className="tag"
                  style={{ marginLeft: 12, fontSize: 10.5, verticalAlign: 'middle' }}
                  title="Seeded sample — a real audit of the demo target, visible to every account"
                >
                  SAMPLE
                </span>
              ) : null}
            </h1>
            {live ? (
              <div className="mono muted" style={{ fontSize: 11.5, marginTop: 8 }}>
                {live.targetUrl} · {fmtDate(live.createdAt)} ·{' '}
                <span style={{ color: 'var(--pass)' }}>{live.passed}✓</span> /{' '}
                <span style={{ color: live.failed ? 'var(--fail)' : 'inherit' }}>
                  {live.failed}✕
                </span>
                {live.errored ? ` · ${live.errored} errored` : ''}
                {live.transportFailed ? ` · ${live.transportFailed} unreachable` : ''}
              </div>
            ) : null}
          </div>
          {live ? (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              {ARTIFACT_BUTTONS.map(({ name, label, primary }) =>
                live.urls[name] ? (
                  <a
                    key={name}
                    className={primary ? 'btn primary' : 'btn ghost'}
                    href={live.urls[name]}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {label}
                  </a>
                ) : null,
              )}
            </div>
          ) : null}
        </div>

        {live && !live.reportAvailable ? (
          <div
            style={{
              border: '1px solid var(--hairline)',
              borderRadius: 'var(--r-lg)',
              padding: '34px 30px',
              textAlign: 'center',
            }}
          >
            <p className="muted" style={{ fontSize: 13.5, maxWidth: 480, margin: '0 auto 14px' }}>
              This run produced no signed report — generation was skipped (most often because the
              audit failed before the battery completed). The registry record carries the outcome;
              completed probes stay preserved in the Phoenix trace.
            </p>
            <A to={`run/${runId}`} className="btn small ghost">
              Open the run summary →
            </A>
          </div>
        ) : live ? (
          <div
            style={{
              border: '1px solid var(--hairline)',
              borderRadius: 'var(--r-lg)',
              padding: '28px 30px',
              display: 'flex',
              alignItems: 'center',
              gap: 24,
            }}
          >
            <div style={{ flex: 1 }}>
              <div className="kicker" style={{ marginBottom: 8 }}>
                Evidence chain
              </div>
              <p className="muted" style={{ fontSize: 13.5, margin: 0, lineHeight: 1.7 }}>
                The PDF and JSON above are the run&apos;s actual signed artifacts — Ed25519-signed
                via Cloud KMS, verifiable against the signature sidecar.
                {live.eventsAvailable
                  ? ' The full probe-by-probe timeline was recorded and can be replayed.'
                  : ''}
              </p>
            </div>
            {live.eventsAvailable ? (
              <A to={`run/${runId}`} className="btn small ember" style={{ whiteSpace: 'nowrap' }}>
                ▶ Replay this audit
              </A>
            ) : null}
          </div>
        ) : null}
      </div>
      <PageFoot />
    </div>
  )
}
