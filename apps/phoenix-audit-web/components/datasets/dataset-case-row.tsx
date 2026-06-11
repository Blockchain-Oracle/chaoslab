'use client'

// Story-9.15 Surface S — DsCaseRow (S-5). One row in the case-table on
// the dataset detail page. Click to expand the full prompt into a
// monospace block with copy-to-clipboard. The expand-collapse uses a
// CSS grid-template-rows trick (0fr → 1fr) so the height animates
// without a measured pixel value.

import { useState, type MouseEvent } from 'react'
import type { DatasetItemDto } from '@/lib/datasets-types'

function FaultClass({ name }: { name: string }) {
  return (
    <span className="tag mono" style={{ fontSize: 9.5, padding: '2px 7px' }}>
      {name}
    </span>
  )
}

function SevDot({ s }: { s: string | null }) {
  if (!s) {
    return (
      <span className="muted mono" style={{ fontSize: 11 }}>
        —
      </span>
    )
  }
  const cls = s === 'high' || s === 'medium' || s === 'low' ? s : 'low'
  return <span className={`sev ${cls}`}>{s}</span>
}

type CopyState = 'idle' | 'copied' | 'unavailable'

export function DsCaseRow({ row, hasNotes }: { row: DatasetItemDto; hasNotes: boolean }) {
  const [open, setOpen] = useState(false)
  const [copy, setCopy] = useState<CopyState>('idle')
  const onCopy = async (e: MouseEvent) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(row.prompt)
      setCopy('copied')
    } catch {
      // Clipboard is legitimately blocked in iframes / insecure contexts.
      // Surface that to the operator — don't silently swallow the failure.
      setCopy('unavailable')
    }
    setTimeout(() => setCopy('idle'), 1400)
  }
  const copyLabel =
    copy === 'copied' ? 'Copied ✓' : copy === 'unavailable' ? 'Copy unavailable' : 'Copy'
  return (
    <>
      <tr
        className="clickable"
        onClick={() => setOpen(!open)}
        title={open ? 'Collapse prompt' : 'Expand the full prompt'}
      >
        <td className="mono" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
          {row.case_id}
        </td>
        <td>
          <FaultClass name={row.fault_class} />
        </td>
        <td className="ds-prompt-cell" style={{ maxWidth: 320 }}>
          <span className="crop" style={{ fontSize: 12.5, lineHeight: 1.5, color: 'var(--ink)' }}>
            {row.prompt}
          </span>
        </td>
        <td style={{ fontSize: 12.5, color: 'var(--ink-2)', maxWidth: 230 }}>{row.expected}</td>
        <td className="mono muted" style={{ fontSize: 10, whiteSpace: 'nowrap' }}>
          {row.source}
        </td>
        <td>
          <SevDot s={row.severity} />
        </td>
        {hasNotes ? (
          <td className="mono muted" style={{ fontSize: 10.5, whiteSpace: 'nowrap' }}>
            {row.notes ? (open ? '▾ notes' : '▸ notes') : '—'}
          </td>
        ) : null}
      </tr>
      <tr className="ds-row-exp">
        <td colSpan={hasNotes ? 7 : 6} style={{ padding: 0 }}>
          <div className={open ? 'ds-expand-wrap open' : 'ds-expand-wrap'}>
            <div>
              <div style={{ padding: '14px 16px 16px' }}>
                <div
                  style={{
                    position: 'relative',
                    fontSize: 12,
                    paddingRight: 86,
                    background: 'var(--paper-2)',
                    border: '1px solid var(--hairline)',
                    borderRadius: 'var(--r)',
                    padding: '12px 14px',
                  }}
                >
                  <div
                    className="mono muted"
                    style={{ fontSize: 9, letterSpacing: '0.16em', marginBottom: 8 }}
                  >
                    PROMPT — SENT TO THE TARGET AGENT VERBATIM
                  </div>
                  <pre
                    style={{
                      fontFamily: 'var(--mono)',
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.7,
                      fontSize: 12,
                    }}
                  >
                    {row.prompt}
                  </pre>
                  <button
                    className="btn small"
                    onClick={onCopy}
                    style={{
                      position: 'absolute',
                      top: 10,
                      right: 10,
                      padding: '4px 9px',
                      fontSize: 9.5,
                    }}
                  >
                    {copyLabel}
                  </button>
                </div>
                <div style={{ display: 'flex', gap: 26, marginTop: 10, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>
                    <span className="mono muted" style={{ fontSize: 9.5, letterSpacing: '0.12em' }}>
                      EXPECTED ·{' '}
                    </span>
                    {row.expected}
                  </span>
                  {row.notes ? (
                    <span style={{ fontSize: 12, color: 'var(--ink-2)', fontStyle: 'italic' }}>
                      <span
                        className="mono muted"
                        style={{
                          fontSize: 9.5,
                          letterSpacing: '0.12em',
                          fontStyle: 'normal',
                        }}
                      >
                        OPERATOR NOTE ·{' '}
                      </span>
                      {row.notes}
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </td>
      </tr>
    </>
  )
}
