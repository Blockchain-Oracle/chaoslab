import type { MouseEvent, ReactNode } from 'react'

// Small chrome primitives — citations, verdict stamps, mode tags, honored
// indicator, span deep-links. Used across the audit chamber, report preview,
// recipe view, and history ledger.

interface CitationProps {
  children: ReactNode
  title?: string
}

export function Citation({ children, title }: CitationProps) {
  return (
    <span className="citation" title={title}>
      {children}
    </span>
  )
}

interface VerdictProps {
  v: 'pass' | 'fail' | 'pending'
}

export function Verdict({ v }: VerdictProps) {
  if (v === 'pass') return <span className="stamp pass">Pass</span>
  if (v === 'fail') return <span className="stamp fail">Fail</span>
  return <span className="stamp neutral">Pending</span>
}

interface ModeTagProps {
  mode: string
}

export function ModeTag({ mode }: ModeTagProps) {
  return (
    <span className="tag" title="Session shape — disclosed per test in the signed audit report">
      {mode}
    </span>
  )
}

interface HonoredDotProps {
  honored: boolean
  dark?: boolean
}

export function HonoredDot({ honored, dark }: HonoredDotProps) {
  const ok = honored
  const color = ok
    ? dark
      ? 'var(--pass-glow)'
      : 'var(--pass)'
    : dark
      ? 'var(--fail-glow)'
      : 'var(--warn)'
  return (
    <span
      title={
        ok
          ? 'Audit-mode headers honored — target short-circuited side-effecting tool calls'
          : 'Audit-mode headers NOT honored — side-effecting tool calls may have executed for real'
      }
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontFamily: 'var(--mono)',
        fontSize: 10.5,
        color,
        letterSpacing: '0.06em',
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: ok ? color : 'transparent',
          border: '1.4px solid ' + color,
          display: 'inline-block',
        }}
      ></span>
      {ok ? 'HDR HONORED' : 'HDR UNCONFIRMED'}
    </span>
  )
}

interface SpanLinkProps {
  id: string
}

export function SpanLink({ id }: SpanLinkProps) {
  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault()
  }
  return (
    <a
      className="span-link"
      href="#phoenix-trace"
      title="Opens this span in the Phoenix observability UI (new tab)"
      onClick={handleClick}
    >
      {id} ↗
    </a>
  )
}

// Category label — content slot (OWASP AGT rename pending).
interface FaultClassProps {
  name: string
}

export function FaultClass({ name }: FaultClassProps) {
  return (
    <span className="tag mono" style={{ fontSize: 10.5 }}>
      {name}
    </span>
  )
}
