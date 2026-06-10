'use client'

// In-app viewer for the run's signed report.json (story-9.13 round 2,
// restyled to the prototype's section/card vocabulary). Header summary card
// surfaces the key facts → SectionHead-divided body → raw JSON block with
// line numbers. Download / Copy actions live on this page.

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import type { ReportDoc } from '@/lib/report-doc'

interface JsonViewProps {
  runId: string
  /** Pretty-printed JSON text — fed to the line-numbered code panel. */
  jsonText: string | null
  /** Parsed/validated report doc — drives the header summary card. */
  report: ReportDoc | null
  jsonError: string | null
  /** Set when fetch succeeded but parser rejected the doc — drives a
   *  disclosure notice so the missing RECORD SUMMARY isn't an unexplained
   *  blank space. */
  reportParseError: string | null
  downloadUrl: string | null
  sample: boolean
}

function MetaRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="leader-row" style={{ padding: '5px 0' }}>
      <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{k}</span>
      <span className="leader-fill"></span>
      <span className="mono" style={{ fontSize: 11, textAlign: 'right' }}>
        {v}
      </span>
    </div>
  )
}

export function JsonView({
  runId,
  jsonText,
  report,
  jsonError,
  reportParseError,
  downloadUrl,
  sample,
}: JsonViewProps) {
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState<string | null>(null)
  const copy = async () => {
    if (!jsonText) return
    setCopyError(null)
    // navigator.clipboard is undefined on insecure origins (http://) and
    // writeText throws on permission denial / private mode. NEVER show
    // "Copied ✓" if nothing reached the clipboard — that would have the
    // user paste stale text into a regulator ticket.
    if (!navigator.clipboard?.writeText) {
      setCopyError('clipboard API unavailable in this context')
      return
    }
    try {
      await navigator.clipboard.writeText(jsonText)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('clipboard write failed:', err)
      setCopyError(msg)
    }
  }
  const lines = jsonText?.split('\n') ?? []

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '44px 40px 30px', maxWidth: 1000 }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 16 }}>
          <A to="audits" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            AUDIT REGISTRY
          </A>{' '}
          /{' '}
          <A to={`report/${runId}`} style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            {runId}
          </A>{' '}
          / report.json
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 18,
            marginBottom: 26,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ flex: 1, minWidth: 280 }}>
            <h1 className="display" style={{ fontSize: 36 }}>
              report.json
              {sample ? (
                <span
                  className="tag"
                  style={{ marginLeft: 12, fontSize: 10.5, verticalAlign: 'middle' }}
                  title="Seeded sample — a real audit of the demo target, visible to every account"
                >
                  SAMPLE
                </span>
              ) : null}
            </h1>
            <div className="mono muted" style={{ fontSize: 11.5, marginTop: 8 }}>
              The structured audit record — what every other artifact is derived from
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {downloadUrl ? (
              <a className="btn primary" href={downloadUrl} download="report.json">
                Download report.json
              </a>
            ) : null}
            <button className="btn small ghost" onClick={copy} disabled={!jsonText} type="button">
              {copied ? 'Copied ✓' : 'Copy raw'}
            </button>
          </div>
        </div>
        {copyError ? (
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--warn, #8a6d1a)',
              border: '1px dashed currentColor',
              borderRadius: 4,
              padding: '8px 12px',
              marginBottom: 18,
            }}
          >
            ⚠ copy failed — {copyError}. Use the Download button instead.
          </div>
        ) : null}
        {reportParseError ? (
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--warn, #8a6d1a)',
              border: '1px dashed currentColor',
              borderRadius: 4,
              padding: '10px 14px',
              marginBottom: 18,
            }}
          >
            ⚠ {reportParseError}
          </div>
        ) : null}

        {report ? (
          <div
            className="card"
            style={{
              padding: '18px 22px',
              marginBottom: 36,
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
                marginBottom: 12,
              }}
            >
              RECORD SUMMARY
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 36px' }}>
              <MetaRow k="Audit run" v={report.runId} />
              <MetaRow k="Filed" v={fmtDate(report.createdAt)} />
              <MetaRow k="Target agent" v={report.targetUrl} />
              <MetaRow k="Framework" v={report.frameworkLabel} />
              <MetaRow
                k="Verdicts"
                v={
                  <>
                    <span style={{ color: 'var(--pass)' }}>{report.passed}✓</span> /{' '}
                    <span style={{ color: report.failed ? 'var(--fail)' : 'inherit' }}>
                      {report.failed}✕
                    </span>
                    {report.errored ? ` · ${report.errored} errored` : ''}
                  </>
                }
              />
              <MetaRow
                k="Root causes"
                v={`${report.rootCauses.length} cluster${report.rootCauses.length === 1 ? '' : 's'}`}
              />
              <MetaRow k="Recipe id" v={report.recipeId ?? '—'} />
              <MetaRow
                k="Honored-header gaps"
                v={`${report.honoredMissingCount} probe-response span${
                  report.honoredMissingCount === 1 ? '' : 's'
                }`}
              />
            </div>
          </div>
        ) : null}

        <SectionHead
          no="§"
          title="Raw record"
          right={
            <span className="mono muted" style={{ fontSize: 10.5 }}>
              {jsonText ? `${lines.length} lines` : 'unavailable'}
            </span>
          }
        />

        {jsonText ? (
          <div
            style={{
              border: '1px solid var(--hairline)',
              borderRadius: 'var(--r-lg)',
              background: 'var(--paper-2)',
              padding: '14px 0',
              maxHeight: '60vh',
              overflowY: 'auto',
            }}
          >
            <pre
              style={{
                margin: 0,
                fontFamily: 'var(--mono)',
                fontSize: 12,
                lineHeight: 1.65,
                whiteSpace: 'pre',
                overflowX: 'auto',
              }}
            >
              {lines.map((line, i) => (
                <div key={i} style={{ display: 'flex', padding: '0 22px', whiteSpace: 'pre' }}>
                  <span
                    style={{
                      width: 44,
                      color: 'var(--ink-3)',
                      textAlign: 'right',
                      paddingRight: 16,
                      userSelect: 'none',
                    }}
                  >
                    {i + 1}
                  </span>
                  <span style={{ color: 'var(--ink)' }}>{line}</span>
                </div>
              ))}
            </pre>
          </div>
        ) : (
          <div
            className="mono"
            style={{
              fontSize: 12,
              color: 'var(--warn, #8a6d1a)',
              border: '1px dashed currentColor',
              borderRadius: 4,
              padding: '12px 16px',
            }}
          >
            ⚠ report.json could not be loaded{jsonError ? ` (${jsonError})` : ''}.
            {downloadUrl ? ' Use the Download button to fetch the raw artifact.' : ''}
          </div>
        )}
      </div>
      <PageFoot />
    </div>
  )
}
