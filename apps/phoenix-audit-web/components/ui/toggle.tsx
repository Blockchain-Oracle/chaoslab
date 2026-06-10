'use client'

interface ToggleProps {
  on: boolean
  onChange?: (next: boolean) => void
  label?: string
}

export function Toggle({ on, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      className={'toggle ' + (on ? 'on' : '')}
      role="switch"
      aria-checked={on}
      aria-label={label ?? 'toggle'}
      onClick={() => onChange?.(!on)}
      style={{ cursor: 'pointer' }}
    ></button>
  )
}
