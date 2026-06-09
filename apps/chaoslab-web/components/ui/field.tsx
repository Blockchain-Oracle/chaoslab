import type { ReactNode } from 'react'

interface FieldProps {
  label: string
  children: ReactNode
  hint?: string
  error?: string | null
}

export function Field({ label, children, hint, error }: FieldProps) {
  return (
    <div style={{ marginBottom: 26 }}>
      <label className="field-label">{label}</label>
      {children}
      {error ? (
        <div className="field-error">
          <span>✕</span>
          <span>{error}</span>
        </div>
      ) : null}
      {hint && !error ? <div className="field-hint">{hint}</div> : null}
    </div>
  )
}
