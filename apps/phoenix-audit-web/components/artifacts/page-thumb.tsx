import { Seal } from '@/components/ui/seal'
import type { ReportPageDef } from './report-pages'
import { REPORT_PAGES } from './report-pages'

interface PageThumbProps {
  p: ReportPageDef
  active: boolean
  signed: boolean
  onClick: () => void
}

const SCRIBBLE_LINES = [34, 90, 78, 84, 60, 88, 72] as const
const TEST_THUMBS: ReadonlyArray<'P' | 'F'> = ['P', 'P', 'F', 'P', 'F', 'F']

export function PageThumb({ p, active, signed, onClick }: PageThumbProps) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'block',
        width: '100%',
        textAlign: 'left',
        background: 'none',
        border: 'none',
        padding: 0,
        marginBottom: 14,
      }}
    >
      <div
        style={{
          aspectRatio: '1 / 1.414',
          background: '#fff',
          border: '1px solid ' + (active ? 'var(--ink)' : 'var(--hairline)'),
          borderRadius: 2,
          boxShadow: active ? '0 0 0 2px var(--ember-soft)' : '0 1px 3px rgba(28,23,18,0.06)',
          padding: '12px 10px',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {p.id === 'cover' ? (
          <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>
            <Seal size={54} spin={false} />
          </div>
        ) : (
          <div>
            {SCRIBBLE_LINES.map((w, i) => (
              <div
                key={i}
                style={{
                  height: i === 0 ? 5 : 3,
                  width: w + '%',
                  background: i === 0 ? 'var(--ink-3)' : 'var(--paper-3)',
                  marginBottom: 6,
                  borderRadius: 1,
                }}
              ></div>
            ))}
            {p.id === 'tests' ? (
              <div style={{ display: 'flex', gap: 3, marginTop: 6 }}>
                {TEST_THUMBS.map((v, i) => (
                  <span
                    key={i}
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: 1,
                      background: v === 'P' ? 'var(--pass-soft)' : 'var(--fail-soft)',
                      border: '1px solid ' + (v === 'P' ? 'var(--pass)' : 'var(--fail)'),
                    }}
                  ></span>
                ))}
              </div>
            ) : null}
          </div>
        )}
        {signed && p.id === 'cover' ? (
          <span
            className="stamp pass"
            style={{ position: 'absolute', bottom: 6, right: 6, fontSize: 8 }}
          >
            Signed
          </span>
        ) : null}
      </div>
      <div
        className="mono"
        style={{
          fontSize: 10,
          letterSpacing: '0.06em',
          color: active ? 'var(--ink)' : 'var(--ink-3)',
          marginTop: 6,
        }}
      >
        {String(REPORT_PAGES.indexOf(p) + 1).padStart(2, '0')} · {p.label}
      </div>
    </button>
  )
}
