'use client'

// The signed-report surface for a REAL run (story-9.13 restore): the designed
// multi-page preview (cover seal, verdict stamps, clusters, in-app recipe with
// diffs) rendered from the run's actual artifacts, an in-app signature verify
// panel, and honest disclosure when anything could not be loaded.

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import { PageThumb } from './page-thumb'
import { REPORT_PAGES, ReportPage, type ReportPageId, type ReportView } from './report-pages'

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
  /** Parsed artifact set — null report doc = preview unavailable, page
   *  falls back to downloads + disclosure (reportDocError says why). */
  view: ReportView | null
  reportDocError: string | null
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

const DOWNLOADS: ReadonlyArray<{ name: string; label: string; primary?: boolean }> = [
  { name: 'report.pdf', label: 'Download PDF', primary: true },
  { name: 'report.json', label: 'report.json' },
  { name: 'signature.json', label: 'signature.json' },
  { name: 'recipe.md', label: 'recipe.md' },
]

function VerifyPanel({ view, live }: { view: ReportView; live: LiveReportData }) {
  const sig = view.signature
  return (
    <div
      style={{
        border: '1px solid var(--hairline)',
        borderRadius: 'var(--r-lg)',
        padding: '16px 20px',
        marginBottom: 26,
        display: 'flex',
        gap: 18,
        alignItems: 'center',
        flexWrap: 'wrap',
      }}
    >
      <div style={{ flex: 1, minWidth: 260 }}>
        <div className="kicker" style={{ marginBottom: 6 }}>
          Signature
        </div>
        {sig ? (
          <div className="mono" style={{ fontSize: 11, lineHeight: 1.8 }}>
            <span style={{ color: 'var(--pass)' }}>●</span> Signed with{' '}
            {sig.algorithm.includes('ED25519') ? 'Ed25519' : sig.algorithm} via Cloud KMS · key
            fingerprint <span title={sig.fingerprint}>{sig.fingerprint.slice(0, 16)}…</span>
            <br />
            {sig.artifacts.length
              ? `${sig.artifacts.length} artifact${sig.artifacts.length === 1 ? '' : 's'} SHA-256-signed (${sig.artifacts.map((a) => a.file).join(', ')}) · verifiable offline against the sidecar`
              : 'verifiable offline against the sidecar'}
          </div>
        ) : (
          <div className="mono" style={{ fontSize: 11, color: 'var(--warn, #8a6d1a)' }}>
            ⚠ signature sidecar could not be loaded
            {view.signatureError ? ` (${view.signatureError})` : ''} — download it below to verify
            offline.
          </div>
        )}
      </div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {DOWNLOADS.map(({ name, label, primary }) =>
          live.urls[name] ? (
            <a
              key={name}
              className={primary ? 'btn primary' : 'btn small ghost'}
              href={live.urls[name]}
              target="_blank"
              rel="noreferrer"
            >
              {primary ? label : `↓ ${label}`}
            </a>
          ) : null,
        )}
      </div>
    </div>
  )
}

export function ReportPreview({
  runId,
  live,
  liveError,
  view,
  reportDocError,
}: ReportPreviewProps) {
  const [page, setPage] = useState<ReportPageId>('cover')
  const signed = Boolean(live?.reportAvailable)

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '44px 40px 30px', maxWidth: 980 }}>
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
        {live?.reportAvailable && !view ? (
          <Notice tone="warn">
            ⚠ REPORT PREVIEW UNAVAILABLE — report.json could not be loaded
            {reportDocError ? ` (${reportDocError})` : ''}; the signed downloads below remain the
            authoritative artifacts.
          </Notice>
        ) : null}

        <div style={{ marginBottom: 22 }}>
          <h1 className="display" style={{ fontSize: 36, whiteSpace: 'nowrap' }}>
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
              <span style={{ color: live.failed ? 'var(--fail)' : 'inherit' }}>{live.failed}✕</span>
              {live.errored ? ` · ${live.errored} errored` : ''}
              {live.transportFailed ? ` · ${live.transportFailed} unreachable` : ''}
            </div>
          ) : null}
        </div>

        {live && view ? <VerifyPanel view={view} live={live} /> : null}

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
        ) : null}

        {live?.reportAvailable && view ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '150px 1fr',
              gap: 36,
              alignItems: 'start',
            }}
          >
            <div>
              {REPORT_PAGES.map((p) => (
                <PageThumb
                  key={p.id}
                  p={p}
                  active={page === p.id}
                  signed={signed}
                  onClick={() => setPage(p.id)}
                  testThumbs={view.report.probes.map((pr) => (pr.verdict === 'pass' ? 'P' : 'F'))}
                />
              ))}
            </div>
            <div
              style={{
                background: '#fff',
                border: '1px solid var(--hairline)',
                boxShadow: '0 18px 50px rgba(28,23,18,0.10)',
                borderRadius: 2,
                maxWidth: 680,
                margin: '0 auto',
                padding: '54px 58px',
                minHeight: 760,
                position: 'relative',
                width: '100%',
              }}
            >
              <ReportPage page={page} view={view} signed={signed} />
            </div>
          </div>
        ) : null}

        {live?.reportAvailable && !view ? (
          <div
            style={{
              border: '1px solid var(--hairline)',
              borderRadius: 'var(--r-lg)',
              padding: '28px 30px',
            }}
          >
            <div className="kicker" style={{ marginBottom: 8 }}>
              Evidence chain
            </div>
            <p className="muted" style={{ fontSize: 13.5, margin: 0, lineHeight: 1.7 }}>
              The PDF and JSON above are the run&apos;s actual signed artifacts — Ed25519-signed via
              Cloud KMS, verifiable against the signature sidecar.
            </p>
          </div>
        ) : null}

        {live?.eventsAvailable ? (
          <div style={{ marginTop: 26, textAlign: 'right' }}>
            <A to={`run/${runId}`} className="btn small ember">
              ▶ Replay this audit
            </A>
          </div>
        ) : null}
      </div>
      <PageFoot />
    </div>
  )
}
