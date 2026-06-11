// Story-9.14 redesign — Docket (O-1). The left-rail table of contents
// for the 4 questions; each row carries the answered value so the
// operator can see at a glance what she's said. Visited rows are
// clickable to jump back; current row is highlighted; unvisited rows
// are disabled.
//
// The state machine lives in the reducer; this component just renders
// and emits `jumpTo` actions for visited rows.

import type { WizardStep } from '@/lib/onboarding'

interface Props {
  step: WizardStep
  maxVisited: WizardStep
  orgName: string
  framework: string
  destination: 'new' | 'audits' | null
  skipped: ReadonlySet<WizardStep>
  onJump: (step: WizardStep) => void
}

const STEP_ORDER: ReadonlyArray<WizardStep> = ['welcome', 'org', 'framework', 'gitlab', 'cta']

const ROWS: { step: WizardStep; q: string; label: string }[] = [
  { step: 'welcome', q: 'W', label: 'Welcome' },
  { step: 'org', q: '01', label: 'Your organization' },
  { step: 'framework', q: '02', label: 'Default framework' },
  { step: 'gitlab', q: '03', label: 'GitLab · preview' },
  { step: 'cta', q: '04', label: 'Where you land' },
]

function valueFor(
  step: WizardStep,
  row: WizardStep,
  maxVisited: WizardStep,
  orgName: string,
  framework: string,
  destination: 'new' | 'audits' | null,
  skipped: ReadonlySet<WizardStep>,
): string {
  if (row === step) return 'now'
  const rowIdx = STEP_ORDER.indexOf(row)
  const visitedIdx = STEP_ORDER.indexOf(maxVisited)
  if (row === 'welcome') return visitedIdx > 0 ? 'done' : '·'
  if (row === 'org') {
    if (orgName) return orgName
    if (skipped.has('org')) return 'skipped · Settings'
    return rowIdx <= visitedIdx ? 'blank · Settings' : '·'
  }
  if (row === 'framework') {
    return rowIdx <= visitedIdx ? framework : `${framework} · dflt`
  }
  if (row === 'gitlab') return 'no input'
  if (row === 'cta') {
    if (destination === 'new') return 'first audit'
    if (destination === 'audits') return 'sample audits'
    return '·'
  }
  return '·'
}

export function Docket({
  step,
  maxVisited,
  orgName,
  framework,
  destination,
  skipped,
  onJump,
}: Props) {
  const currentIdx = STEP_ORDER.indexOf(step)
  return (
    <div>
      <div className="onb-fraction">
        <span className="num">
          {Math.max(0, currentIdx)}
          <span style={{ color: 'var(--ink-3)', fontSize: 21 }}> / 4</span>
        </span>
        <span
          className="mono"
          style={{ fontSize: 9.5, letterSpacing: '0.16em', color: 'var(--ink-3)' }}
        >
          QUESTIONS · ALL SKIPPABLE
        </span>
      </div>
      <div className="onb-toc" role="list">
        {ROWS.map(({ step: rowStep, q, label }) => {
          const visitedIdx = STEP_ORDER.indexOf(maxVisited)
          const rowIdx = STEP_ORDER.indexOf(rowStep)
          const jumpable = rowStep !== step && rowIdx <= visitedIdx
          const isCurrent = rowStep === step
          const isDone = rowIdx < currentIdx || (rowStep !== step && rowIdx <= visitedIdx)
          const cls = ['onb-toc-row', isCurrent ? 'current' : '', isDone ? 'done' : '']
            .filter(Boolean)
            .join(' ')
          return (
            <button
              type="button"
              key={rowStep}
              role="listitem"
              className={cls}
              disabled={!jumpable}
              onClick={jumpable ? () => onJump(rowStep) : undefined}
              title={jumpable ? 'Revisit this step' : undefined}
            >
              <span className="q">{q}</span>
              <span>{label}</span>
              <span className="fill" />
              <span className="val">
                {valueFor(step, rowStep, maxVisited, orgName, framework, destination, skipped)}
              </span>
            </button>
          )
        })}
      </div>
      <div className="onb-contract">
        <span className="mark">◆</span>
        <span>
          Skipping keeps the default, and <strong>Finish always opens the register</strong> — even
          if you skip everything. Change any answer later in Settings.
        </span>
      </div>
    </div>
  )
}
