interface StatBlockProps {
  value: string | number
  label: string
}

export function StatBlock({ value, label }: StatBlockProps) {
  return (
    <div
      style={{
        padding: '18px 26px 16px 0',
        borderRight: '1px solid var(--hairline)',
        marginRight: 26,
      }}
    >
      <div className="serif num" style={{ fontSize: 38, lineHeight: 1 }}>
        {value}
      </div>
      <div
        className="mono muted"
        style={{
          fontSize: 10.5,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          marginTop: 8,
        }}
      >
        {label}
      </div>
    </div>
  )
}
