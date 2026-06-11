'use client'

// The signed-report multi-page preview (story-9.13 round 2 — prototype
// fidelity). Top-right action row mirrors `Phoenix Audit.html`:
//   [ Download PDF ] [ View JSON ] [ View signature ]
// Page thumbnails sit in a HORIZONTAL strip above the preview pane so a
// user can switch to any page without scrolling past the whole report.
// The preview pane itself scrolls in place. Each artifact link navigates
// to a dedicated viewer screen — never a raw browser tab.

import { useEffect, useRef, useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import { EmailReportButton } from './email-report-button'
import { PageThumb } from './page-thumb'
import { REPORT_PAGES, ReportPage, type ReportPageId, type ReportView } from './report-pages'

export interface LiveReportData {
  urls: Record<string, string>
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
  live: LiveReportData | null
  liveError: string | null
  view: ReportView | null
  reportDocError: string | null
  initialPage?: ReportPageId
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

export function ReportPreview({
  runId,
  live,
  liveError,
  view,
  reportDocError,
  initialPage,
}: ReportPreviewProps) {
  const [page, setPage] = useState<ReportPageId>(initialPage ?? 'cover')
  const signed = Boolean(live?.reportAvailable)
  const previewRef = useRef<HTMLDivElement>(null)

  // Reset the preview's own scroll when switching pages — the rail stays
  // visible above; a long page should start at its top, not where the
  // previous page left off.
  useEffect(() => {
    previewRef.current?.scrollTo({ top: 0 })
  }, [page])

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '44px 40px 30px', maxWidth: 1080 }}>
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
            {reportDocError ? ` (${reportDocError})` : ''}; the artifact viewer links below remain
            available.
          </Notice>
        ) : null}

        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 18,
            marginBottom: 22,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ flex: 1, minWidth: 320 }}>
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
          {live?.reportAvailable ? (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {live.urls['report.pdf'] ? (
                // The IN-APP report preview (this page) is the PDF view.
                // This button downloads / opens the binary artifact itself.
                <a
                  className="btn primary"
                  href={live.urls['report.pdf']}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download PDF
                </a>
              ) : null}
              <EmailReportButton runId={runId} />
              {live.urls['report.json'] ? (
                <A to={`report/${runId}/json`} className="btn ghost">
                  View JSON
                </A>
              ) : null}
              {live.urls['signature.json'] ? (
                <A to={`report/${runId}/signature`} className="btn ghost">
                  View signature
                </A>
              ) : null}
              {view?.report.recipeId ? (
                <A to={`recipe/${runId}`} className="btn ghost">
                  View recipe
                </A>
              ) : null}
              {live.eventsAvailable ? (
                <A to={`run/${runId}`} className="btn ember">
                  ▶ Replay
                </A>
              ) : null}
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
        ) : null}

        {live?.reportAvailable && view ? (
          <div
            className="report-preview-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: '150px 1fr',
              gap: 36,
              alignItems: 'start',
            }}
          >
            {/* Vertical page rail — SCROLLS INTERNALLY when there are many
                pages so the main viewport never has to scroll just to reach
                page N. Bounded height matches the preview pane below. */}
            <div
              style={{
                maxHeight: '78vh',
                overflowY: 'auto',
                paddingRight: 6,
                position: 'sticky',
                top: 24,
              }}
            >
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
              ref={previewRef}
              className="report-sheet"
              style={{
                background: '#fff',
                border: '1px solid var(--hairline)',
                boxShadow: '0 18px 50px rgba(28,23,18,0.10)',
                borderRadius: 2,
                maxWidth: 720,
                margin: '0 auto',
                padding: '54px 58px',
                position: 'relative',
                // The preview pane SCROLLS INTERNALLY too — page content
                // never forces the outer viewport to scroll.
                maxHeight: '78vh',
                overflowY: 'auto',
              }}
            >
              <ReportPage page={page} view={view} signed={signed} runId={runId} />
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
              The downloads above are the run&apos;s actual signed artifacts — Ed25519-signed via
              Cloud KMS, verifiable against the signature sidecar.
            </p>
          </div>
        ) : null}
      </div>
      <PageFoot />
    </div>
  )
}
