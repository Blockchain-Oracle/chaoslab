'use client'

// Story-9.15 Surface S — wizard dataset picker (S-6). Collapsed by
// default; auto-expands and pre-selects when the wizard is opened via
// `/new?dataset=<slug>`. Lists are loaded from /api/agent/datasets
// (proxied to the agent backend); we render the three kinds grouped
// with the same KindChip glyph the listing uses, plus a typeahead
// filter and a "clear" affordance.
//
// The chosen `dataset_id` flows into RunRequest as an OPTIONAL field —
// no dataset = the standard battery probes only, exactly as today.

import { useEffect, useRef, useState } from 'react'
import { A } from '@/components/ui/link'
import type { DatasetKind, DatasetListRowDto } from '@/lib/datasets'

const KIND_GLYPH: Record<DatasetKind, string> = {
  battery: '▣',
  regression: '↻',
  uploaded: '▲',
}

function KindChip({ kind }: { kind: DatasetKind }) {
  return (
    <span className={`kind-chip ${kind}`}>
      <span className="k-glyph">{KIND_GLYPH[kind]}</span>
      {kind}
    </span>
  )
}

interface ComboProps {
  value: string | null
  rows: DatasetListRowDto[]
  onChange: (slug: string | null) => void
}

function DsCombobox({ value, rows, onChange }: ComboProps) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fn = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', fn)
    return () => document.removeEventListener('mousedown', fn)
  }, [])

  const sel = value ? (rows.find((r) => r.dataset_id === value) ?? null) : null
  const hit = (d: DatasetListRowDto) =>
    (d.name + d.dataset_id).toLowerCase().includes(q.toLowerCase())

  const groups: { label: string; list: DatasetListRowDto[] }[] = [
    { label: 'Standing battery', list: rows.filter((r) => r.kind === 'battery') },
    { label: 'Your uploads', list: rows.filter((r) => r.kind === 'uploaded') },
    { label: 'Regression sets', list: rows.filter((r) => r.kind === 'regression') },
  ]

  return (
    <div className="ds-combo" ref={ref}>
      <button
        type="button"
        className="ds-combo-btn"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen(!open)}
      >
        {sel ? (
          <>
            <KindChip kind={sel.kind} />
            <span
              className="mono"
              style={{
                fontSize: 13,
                flex: 1,
                minWidth: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {sel.name}
            </span>
            <span className="mono muted" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
              {sel.row_count} rows
            </span>
          </>
        ) : (
          <span className="muted" style={{ flex: 1 }}>
            Choose a dataset — battery, regression, or one of yours…
          </span>
        )}
        <span className="mono muted" style={{ fontSize: 11 }}>
          {open ? '▴' : '▾'}
        </span>
      </button>
      {open ? (
        <div className="ds-combo-pop" role="listbox">
          <div style={{ padding: '10px 12px 4px' }}>
            <input
              className="text-input"
              style={{ padding: '8px 10px', fontSize: 12 }}
              placeholder="Filter by name…"
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          {value ? (
            <button
              type="button"
              className="ds-combo-row"
              onClick={() => {
                onChange(null)
                setOpen(false)
              }}
            >
              <span className="mono muted" style={{ fontSize: 11 }}>
                ✕ clear — run the standard probes only
              </span>
            </button>
          ) : null}
          {groups.map(({ label, list }) => {
            const hits = list.filter(hit)
            if (!hits.length) return null
            return (
              <div key={label}>
                <div className="ds-combo-group">{label}</div>
                {hits.map((d) => (
                  <button
                    type="button"
                    key={d.dataset_id}
                    className={d.dataset_id === value ? 'ds-combo-row hl' : 'ds-combo-row'}
                    role="option"
                    aria-selected={d.dataset_id === value}
                    onClick={() => {
                      onChange(d.dataset_id)
                      setOpen(false)
                      setQ('')
                    }}
                  >
                    <KindChip kind={d.kind} />
                    <span className="nm mono" style={{ fontSize: 12.5 }}>
                      {d.name}
                    </span>
                    <span className="mono muted" style={{ fontSize: 10.5, whiteSpace: 'nowrap' }}>
                      {d.row_count} rows
                    </span>
                  </button>
                ))}
              </div>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}

interface PickerProps {
  value: string | null
  onChange: (slug: string | null) => void
  /** When truthy, the accordion starts expanded (deep-link from /datasets). */
  initiallyOpen: boolean
}

export function DatasetPicker({ value, onChange, initiallyOpen }: PickerProps) {
  const [open, setOpen] = useState(initiallyOpen)
  const [rows, setRows] = useState<DatasetListRowDto[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await fetch('/api/agent/datasets')
        if (!res.ok) throw new Error(`agent API ${res.status} on /datasets`)
        const body = (await res.json()) as { datasets: unknown }
        if (cancelled) return
        if (!Array.isArray(body.datasets)) {
          throw new Error('agent API returned non-array datasets — contract drift')
        }
        setRows(body.datasets as DatasetListRowDto[])
        setLoaded(true)
      } catch (err) {
        if (cancelled) return
        setLoadError(err instanceof Error ? err.message : String(err))
        setLoaded(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const sel = value ? (rows.find((r) => r.dataset_id === value) ?? null) : null

  return (
    <div
      style={{
        border: '1px solid var(--hairline)',
        borderRadius: 'var(--r-lg)',
        marginBottom: 40,
      }}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: '100%',
          background: 'none',
          border: 'none',
          padding: '15px 18px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          textAlign: 'left',
          cursor: 'pointer',
        }}
      >
        <span className="doc-section-no">§3b</span>
        <span className="serif" style={{ fontSize: 16, flex: 1 }}>
          Use a specific dataset{' '}
          <span className="muted" style={{ fontSize: 12.5, fontFamily: 'var(--sans)' }}>
            · optional
          </span>
        </span>
        {sel && !open ? <KindChip kind={sel.kind} /> : null}
        {sel && !open ? (
          <span className="mono muted" style={{ fontSize: 11 }}>
            {sel.name}
          </span>
        ) : null}
        <span className="mono muted" style={{ fontSize: 12 }}>
          {open ? '− collapse' : '+ expand'}
        </span>
      </button>
      {open ? (
        <div style={{ padding: '4px 18px 20px', borderTop: '1px solid var(--hairline-soft)' }}>
          <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.6, margin: '10px 0 14px' }}>
            Runs a named, persistent set of test cases <em>alongside</em> the standard probes — the
            same battery on the same agent, before and after the fix.{' '}
            <A to="datasets" className="span-link" style={{ fontSize: 12 }}>
              Browse datasets →
            </A>
          </p>
          {loaded ? (
            <DsCombobox value={value} rows={rows} onChange={onChange} />
          ) : (
            <div className="mono muted" style={{ fontSize: 11 }}>
              loading datasets…
            </div>
          )}
          {loadError ? (
            <div
              className="mono"
              role="alert"
              style={{ fontSize: 11, color: 'var(--fail)', marginTop: 8 }}
            >
              ◌ could not load datasets ({loadError}) — re-run with the standard probes only
            </div>
          ) : null}
          {sel ? (
            <div
              className="mono"
              style={{
                fontSize: 11,
                letterSpacing: '0.03em',
                color: 'var(--ink-2)',
                marginTop: 12,
                display: 'flex',
                gap: 8,
                alignItems: 'baseline',
              }}
            >
              <span style={{ color: 'var(--ember-deep)' }}>◆</span>
              this audit will run 8 standard probes + {sel.row_count} rows from{' '}
              <span className="mono">{sel.name}</span>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
