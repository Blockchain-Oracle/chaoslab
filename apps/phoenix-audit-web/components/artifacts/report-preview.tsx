'use client'

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { Seal } from '@/components/ui/seal'
import { TopBar } from '@/components/ui/topbar'
import { HERO_RUN } from '@/lib/fixtures'
import { useSafeTimeout } from '@/lib/use-safe-timeout'
import { PageThumb } from './page-thumb'
import { REPORT_PAGES, ReportPage, type ReportPageId } from './report-pages'

export interface LiveReportData {
  /** Freshly signed artifact URLs from the registry (report.pdf, report.json,
   *  signature.json, recipe.md — whichever exist). */
  urls: Record<string, string>
  /** Artifacts whose URL signing failed — distinct from absent. */
  errors: Record<string, string>
  reportAvailable: boolean
  passed: number
  failed: number
  createdAt: string
  targetUrl: string
}

interface ReportPreviewProps {
  runId?: string
  /** Present = REAL run from the registry; the report was signed during the
   *  run, so the signing theater is skipped and downloads are live. */
  live?: LiveReportData | null
  /** Live registry unreachable for a non-sample run id. */
  liveError?: string | null
}

type SignState = 'idle' | 'signing' | 'signed'

export function ReportPreview({ runId, live, liveError }: ReportPreviewProps) {
  const r = HERO_RUN
  const isLive = Boolean(live)
  const [page, setPage] = useState<ReportPageId>('cover')
  const [signState, setSignState] = useState<SignState>(isLive ? 'signed' : 'idle')
  const schedule = useSafeTimeout()
  const sign = () => {
    setSignState('signing')
    schedule(() => setSignState('signed'), 2100)
  }
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '44px 40px 30px' }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 14 }}>
          <A to="audits" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            AUDIT REGISTRY
          </A>{' '}
          / {runId ?? r.id} / signed report
        </div>
        {liveError ? (
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
            ⚠ LIVE REGISTRY UNAVAILABLE — this run&apos;s artifacts cannot be fetched right now. (
            {liveError})
          </div>
        ) : null}
        {isLive && live && !live.reportAvailable ? (
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
            ⚠ NO SIGNED REPORT FOR THIS RUN — generation was skipped (see the run&apos;s event log).
          </div>
        ) : null}
        {isLive && live && Object.keys(live.errors).length > 0 ? (
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--fail)',
              border: '1px dashed currentColor',
              borderRadius: 4,
              padding: '10px 14px',
              marginBottom: 18,
            }}
          >
            ✕ DOWNLOAD LINKS TEMPORARILY UNAVAILABLE for: {Object.keys(live.errors).join(', ')} —
            re-signing failed; reload to retry.
          </div>
        ) : null}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 18,
            marginBottom: 34,
          }}
        >
          <div style={{ flex: 1 }}>
            <h1 className="display" style={{ fontSize: 36 }}>
              Signed audit report.
            </h1>
            <div className="mono muted" style={{ fontSize: 11.5, marginTop: 8 }}>
              {r.signingKey}
            </div>
          </div>
          {isLive && live ? (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              {live.urls['report.pdf'] ? (
                <a
                  className="btn primary"
                  href={live.urls['report.pdf']}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download PDF
                </a>
              ) : null}
              {live.urls['report.json'] ? (
                <a
                  className="btn ghost"
                  href={live.urls['report.json']}
                  target="_blank"
                  rel="noreferrer"
                >
                  Signed JSON
                </a>
              ) : null}
              {live.urls['signature.json'] ? (
                <a
                  className="btn ghost"
                  href={live.urls['signature.json']}
                  target="_blank"
                  rel="noreferrer"
                >
                  Signature sidecar
                </a>
              ) : null}
              {live.urls['recipe.md'] ? (
                <a
                  className="btn ghost"
                  href={live.urls['recipe.md']}
                  target="_blank"
                  rel="noreferrer"
                >
                  Recipe (md)
                </a>
              ) : null}
            </div>
          ) : signState === 'signed' ? (
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn primary">Download PDF</button>
              <button className="btn ghost">Download signed JSON</button>
            </div>
          ) : (
            <button
              className="btn ember"
              onClick={sign}
              disabled={signState === 'signing'}
              style={{ minWidth: 190 }}
            >
              {signState === 'signing' ? 'Signing via Cloud KMS…' : 'Sign and file'}
            </button>
          )}
        </div>

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
                signed={signState === 'signed'}
                onClick={() => setPage(p.id)}
              />
            ))}
          </div>

          <div style={{ position: 'relative' }}>
            <div
              style={{
                background: '#fff',
                border: '1px solid var(--hairline)',
                boxShadow: '0 18px 50px rgba(28,23,18,0.10)',
                borderRadius: 2,
                maxWidth: 660,
                margin: '0 auto',
                padding: '54px 58px',
                minHeight: 760,
                position: 'relative',
              }}
            >
              <ReportPage page={page} signed={signState === 'signed'} />
            </div>

            {signState === 'signing' ? (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'grid',
                  placeItems: 'center',
                  background: 'rgba(250,247,240,0.82)',
                  backdropFilter: 'blur(2px)',
                  zIndex: 5,
                }}
              >
                <div style={{ textAlign: 'center' }}>
                  <Seal size={130} />
                  <div
                    className="mono"
                    style={{
                      fontSize: 11,
                      letterSpacing: '0.14em',
                      color: 'var(--ember-deep)',
                      marginTop: 16,
                    }}
                  >
                    CLOUD KMS · SIGNING DIGEST SHA-256
                    <span className="blink-caret">▌</span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
      <PageFoot />
    </div>
  )
}
