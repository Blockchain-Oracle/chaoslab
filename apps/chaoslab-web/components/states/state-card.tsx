import type { ReactNode } from 'react'

interface StateCardProps {
  label: string
  children: ReactNode
}

export function StateCard({ label, children }: StateCardProps) {
  return (
    <div>
      <div
        className="mono muted"
        style={{
          fontSize: 10.5,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          marginBottom: 10,
        }}
      >
        {label}
      </div>
      <div className="card" style={{ padding: '20px 22px', minHeight: 130 }}>
        {children}
      </div>
    </div>
  )
}
