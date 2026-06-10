'use client'

import { useId } from 'react'

// Concentric rings + rotating circular ring-text + center glyph.
// Used at signing moments and as the brand's hero asset.
interface SealProps {
  size?: number
  spin?: boolean
  dark?: boolean
  text?: string
}

export function Seal({
  size = 150,
  spin = true,
  dark = false,
  text = 'PHOENIX AUDIT · CRYPTOGRAPHICALLY SIGNED · CLOUD KMS · ',
}: SealProps) {
  const c = dark ? 'var(--ember-glow)' : 'var(--ember-deep)'
  const sub = dark ? 'var(--chamber-ink-3)' : 'var(--ink-3)'
  const uid = useId().replace(/:/g, '')
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      aria-label="Phoenix Audit seal"
    >
      <circle cx="60" cy="60" r="58" stroke={c} strokeWidth="1.4" />
      <circle cx="60" cy="60" r="54.5" stroke={sub} strokeWidth="0.6" strokeDasharray="1.5 3" />
      <circle cx="60" cy="60" r="35" stroke={c} strokeWidth="0.9" />
      <g className={spin ? 'seal-spin' : ''}>
        <defs>
          <path id={'ring' + uid} d="M 60,60 m -45,0 a 45,45 0 1,1 90,0 a 45,45 0 1,1 -90,0" />
        </defs>
        <text fontSize="8.1" fontFamily="var(--mono)" letterSpacing="1.9" fill={c}>
          <textPath href={'#ring' + uid}>{text}</textPath>
        </text>
      </g>
      <g transform="translate(60 60) scale(2.1) translate(-12 -12)">
        <path d="M12 7.6 L17.4 13.8 L12 20 L6.6 13.8 Z" fill={c} />
        <path d="M14.2 5.4 L16.4 3.2 L18.6 5.4 L16.4 7.6 Z" fill={c} opacity="0.55" />
        <path d="M9.8 4.2 L12 2 L14.2 4.2 L12 6.4 Z" fill={c} />
      </g>
    </svg>
  )
}
