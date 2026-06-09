// The Phoenix Audit brand mark: a diamond (the agent under audit) with
// a spark diamond rising off its top vertex — the phoenix, abstracted
// to pure geometry.
interface GlyphProps {
  size?: number
  color?: string
}

export function Glyph({ size = 22, color = 'currentColor' }: GlyphProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 7.6 L17.4 13.8 L12 20 L6.6 13.8 Z" fill={color} />
      <path d="M14.2 5.4 L16.4 3.2 L18.6 5.4 L16.4 7.6 Z" fill={color} opacity="0.55" />
      <path d="M9.8 4.2 L12 2 L14.2 4.2 L12 6.4 Z" fill={color} />
    </svg>
  )
}
