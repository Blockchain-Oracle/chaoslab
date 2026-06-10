'use client'

import { useEffect, useState } from 'react'
import { Glyph } from '@/components/ui/glyph'
import { A } from '@/components/ui/link'
import { HERO_RUN } from '@/lib/fixtures'

interface ReceiptProps {
  mode: 'replay' | 'live'
}

const ROWS: ReadonlyArray<[string, string]> = [
  ['Run', HERO_RUN.id],
  ['Target agent', 'prior-auth · ADK'],
  ['Framework', 'EU AI Act · high-risk'],
  ['Adversarial tests', '6 · 3 pass · 3 fail'],
  ['Root cause clusters', '1 · cluster_a3f81c2e'],
  ['Hardening recipe', 'generated · 4.1 s'],
  ['Wall-clock', HERO_RUN.durationSec + ' s'],
  ['Cost of run', '$' + HERO_RUN.costUsd.toFixed(2)],
]

export function Receipt({ mode }: ReceiptProps) {
  const [animating, setAnimating] = useState(true)
  useEffect(() => {
    const id = setTimeout(() => setAnimating(false), 900)
    return () => clearTimeout(id)
  }, [])
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '0 6vw',
        background: 'rgba(10,7,4,0.55)',
        backdropFilter: 'blur(3px)',
      }}
    >
      <div
        className={'receipt ' + (animating ? 'slide-in' : '')}
        style={{ width: 420, maxHeight: '92vh', overflowY: 'auto' }}
      >
        <div style={{ padding: '26px 30px 22px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid var(--ink)',
              paddingBottom: 12,
              marginBottom: 16,
            }}
          >
            <span className="mono" style={{ fontSize: 10.5, letterSpacing: '0.2em' }}>
              AUDIT COMPLETE
            </span>
            <Glyph size={16} color="var(--ember-deep)" />
          </div>
          {ROWS.map(([k, v]) => (
            <div key={k} className="leader-row" style={{ padding: '5.5px 0' }}>
              <span style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{k}</span>
              <span className="leader-fill"></span>
              <span className="mono num" style={{ fontSize: 11.5 }}>
                {v}
              </span>
            </div>
          ))}
          <div
            className="fallback-flag"
            style={{ marginTop: 14, width: '100%', justifyContent: 'flex-start' }}
          >
            ⚠ 1 probe did not confirm audit-mode headers — see report warning
          </div>
          <div style={{ display: 'grid', gap: 10, marginTop: 20 }}>
            <A to={'report/' + HERO_RUN.id} className="btn primary">
              Open signed report preview
            </A>
            <A to={'recipe/' + HERO_RUN.recipeId} className="btn">
              View hardening recipe
            </A>
            <a
              className="btn ghost"
              href={HERO_RUN.mrUrl}
              onClick={(e) => e.preventDefault()}
              title="Opens the real merge request in your connected GitLab"
            >
              GitLab MR !214 ↗
            </a>
          </div>
          {mode === 'replay' ? (
            <div
              style={{
                marginTop: 18,
                paddingTop: 14,
                borderTop: '1px dotted var(--hairline)',
                textAlign: 'center',
              }}
            >
              <A
                to="new"
                className="mono"
                style={{
                  fontSize: 11.5,
                  letterSpacing: '0.08em',
                  color: 'var(--ember-deep)',
                }}
              >
                RUN ONE AGAINST YOUR OWN AGENT →
              </A>
            </div>
          ) : null}
        </div>
        <div className="receipt-tear"></div>
      </div>
    </div>
  )
}
