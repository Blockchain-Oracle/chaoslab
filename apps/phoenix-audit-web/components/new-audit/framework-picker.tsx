import { SectionHead } from '@/components/ui/section-head'

const FRAMEWORKS: ReadonlyArray<[string, string]> = [
  ['EU AI Act', 'Articles 9, 11–15, 72 · Annex IV documentation'],
  ['NIST AI RMF', 'GOVERN / MAP / MEASURE / MANAGE functions'],
  ['HIPAA', '§164.312 technical safeguards'],
  ['SOC 2 + AI', 'Trust services criteria, AI addendum'],
  ['Custom', 'Bring your own control mapping'],
]

interface FrameworkPickerProps {
  framework: string
  setFramework: (f: string) => void
}

export function FrameworkPicker({ framework, setFramework }: FrameworkPickerProps) {
  return (
    <>
      <SectionHead
        no="§3"
        title="Regulatory framework"
        right={
          <span className="tag">EU AI Act applied to every report — selection coming soon</span>
        }
      />
      <div
        style={{
          display: 'grid',
          gap: 0,
          border: '1px solid var(--hairline)',
          borderRadius: 'var(--r-lg)',
          overflow: 'hidden',
          marginBottom: 40,
        }}
        role="radiogroup"
      >
        {FRAMEWORKS.map(([f, sub], i) => (
          <div
            key={f}
            onClick={() => setFramework(f)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                setFramework(f)
              }
            }}
            role="radio"
            aria-checked={framework === f}
            tabIndex={0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              padding: '14px 18px',
              cursor: 'pointer',
              borderTop: i > 0 ? '1px solid var(--hairline-soft)' : 'none',
              background: framework === f ? '#fff' : 'transparent',
              boxShadow: framework === f ? 'inset 3px 0 0 var(--ember-deep)' : 'none',
              transition: 'background 0.15s ease',
            }}
          >
            <span
              style={{
                width: 14,
                height: 14,
                borderRadius: '50%',
                border:
                  '1.5px solid ' + (framework === f ? 'var(--ember-deep)' : 'var(--hairline)'),
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {framework === f ? (
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: 'var(--ember-deep)',
                  }}
                ></span>
              ) : null}
            </span>
            <span className="serif" style={{ fontSize: 16, width: 150 }}>
              {f}
            </span>
            <span className="mono muted" style={{ fontSize: 11 }}>
              {sub}
            </span>
          </div>
        ))}
      </div>
    </>
  )
}
