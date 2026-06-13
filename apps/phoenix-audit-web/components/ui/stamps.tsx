import type { ReactNode } from 'react'

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
  v: 'pass' | 'fail' | 'error' | 'skip' | 'pending'
}

export function Verdict({ v }: VerdictProps) {
  if (v === 'pass') return <span className="stamp pass">Pass</span>
  if (v === 'fail') return <span className="stamp fail">Fail</span>
  // Audit deliberately did not score this probe (F1/F4 in black-box mode).
  // Distinct from `error` so the regulator sees "excluded by design" vs
  // "could not be scored". Matches the signed-report SKIP stamp.
  if (v === 'skip')
    return (
      <span
        className="stamp warn"
        title="Disclosed-skip: target lacks instrumentation for this fault class"
      >
        Skip
      </span>
    )
  // The judge rubric itself failed — a marked non-verdict, distinct from
  // pass/fail so a regulator can never mistake it for a scored outcome.
  if (v === 'error') return <span className="stamp warn">Error</span>
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
  /** Story-9.21: when set, the link opens the span in Phoenix. Absent →
   *  text-only id, never a dead link. */
  href?: string | null
}

export function SpanLink({ id, href }: SpanLinkProps) {
  if (!href) {
    return (
      <span className="span-link" title="Phoenix UI not configured — span id only">
        {id}
      </span>
    )
  }
  return (
    <a
      className="span-link"
      href={href}
      target="_blank"
      rel="noreferrer"
      title="Open this span in Phoenix (new tab)"
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
