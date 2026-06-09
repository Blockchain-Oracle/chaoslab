'use client'

import { Field } from '@/components/ui/field'

const CATS = ['prompt_injection', 'context_poisoning', 'malformed_tool_output', 'latency_spike']

interface OverridesBlockProps {
  showOverrides: boolean
  setShowOverrides: (v: boolean) => void
  skipCats: string[]
  setSkipCats: (cats: string[]) => void
  cap: number
  setCap: (n: number) => void
  judge: string
  setJudge: (j: string) => void
}

export function OverridesBlock(props: OverridesBlockProps) {
  const { showOverrides, setShowOverrides, skipCats, setSkipCats, cap, setCap, judge, setJudge } =
    props
  return (
    <div
      style={{
        border: '1px solid var(--hairline)',
        borderRadius: 'var(--r-lg)',
        marginBottom: 44,
      }}
    >
      <button
        onClick={() => setShowOverrides(!showOverrides)}
        style={{
          width: '100%',
          background: 'none',
          border: 'none',
          padding: '15px 18px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          textAlign: 'left',
        }}
      >
        <span className="doc-section-no">§4</span>
        <span className="serif" style={{ fontSize: 16, flex: 1 }}>
          Override settings{' '}
          <span className="muted" style={{ fontSize: 12.5, fontFamily: 'var(--sans)' }}>
            · optional
          </span>
        </span>
        <span className="mono muted" style={{ fontSize: 12 }}>
          {showOverrides ? '− collapse' : '+ expand'}
        </span>
      </button>
      {showOverrides ? (
        <div style={{ padding: '4px 18px 20px', borderTop: '1px solid var(--hairline-soft)' }}>
          <Field
            label="Skip adversarial categories"
            hint="Category names follow the OWASP AGT taxonomy as it lands."
          >
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', paddingTop: 4 }}>
              {CATS.map((c) => {
                const off = skipCats.includes(c)
                return (
                  <button
                    key={c}
                    onClick={() =>
                      setSkipCats(off ? skipCats.filter((x) => x !== c) : [...skipCats, c])
                    }
                    className="tag"
                    style={{
                      cursor: 'pointer',
                      textDecoration: off ? 'line-through' : 'none',
                      opacity: off ? 0.45 : 1,
                      border: '1px solid var(--hairline)',
                    }}
                  >
                    {c}
                  </button>
                )
              })}
            </div>
          </Field>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="Cap number of tests">
              <input
                className="text-input"
                type="number"
                min={1}
                max={24}
                value={cap}
                onChange={(e) => setCap(Number(e.target.value) || 0)}
              />
            </Field>
            <Field label="Judge model override">
              <select
                className="text-input"
                value={judge}
                onChange={(e) => setJudge(e.target.value)}
              >
                <option>gemini-3.5-flash (default)</option>
                <option>gemini-3.5-pro</option>
                <option>custom rubric endpoint…</option>
              </select>
            </Field>
          </div>
        </div>
      ) : null}
    </div>
  )
}
