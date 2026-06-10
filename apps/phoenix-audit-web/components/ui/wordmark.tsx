import { Glyph } from './glyph'

interface WordmarkProps {
  size?: number
  glyph?: number
}

export function Wordmark({ size = 17, glyph = 20 }: WordmarkProps) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
      <Glyph size={glyph} />
      <span
        className="serif"
        style={{
          fontSize: size,
          letterSpacing: '0.005em',
          fontWeight: 500,
          whiteSpace: 'nowrap',
        }}
      >
        Phoenix&nbsp;Audit
      </span>
    </span>
  )
}
