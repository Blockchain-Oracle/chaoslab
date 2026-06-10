// Renders the run's REAL recipe.md in-app. The diff idiom matches the
// prototype's Surface G: paper-2 background, ink text, soft red/green tints
// on +/- lines (NOT the audit chamber's dark codeblock). Top-level (h2)
// markdown headings are wrapped in SectionHead with auto §-numbering when
// `numbered` is on, so the Surface G page reads §1 Summary, §2 Root Causes,
// §3 Prompt Patches, etc. without anyone hand-numbering anything.

import { Fragment } from 'react'
import { SectionHead } from '@/components/ui/section-head'
import { diffLineKind, type RecipeBlock } from '@/lib/report-doc'

/** Minimal inline renderer for OUR generated markdown: `code` and **bold**. */
function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i}>{part.slice(2, -2)}</strong>
        }
        if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
          return (
            <code key={i} className="mono" style={{ fontSize: '0.92em' }}>
              {part.slice(1, -1)}
            </code>
          )
        }
        return <Fragment key={i}>{part}</Fragment>
      })}
    </>
  )
}

function CodeBlock({ lines }: { lines: string[] }) {
  return (
    <pre className="codeblock light" style={{ margin: '0 0 16px', whiteSpace: 'pre-wrap' }}>
      {lines.map((line, i) => {
        const kind = diffLineKind(line)
        const cls = kind === 'add' ? 'add' : kind === 'del' ? 'del' : kind === 'hunk' ? 'dim' : ''
        return (
          <div key={i} className={cls}>
            {line}
          </div>
        )
      })}
    </pre>
  )
}

interface RecipeMdViewProps {
  blocks: RecipeBlock[]
  /** When true, every h2 wraps in a SectionHead with auto §1, §2, …
   *  Use on the standalone Surface G; leave off in the small report-preview
   *  excerpt so the embedded view stays compact. */
  numbered?: boolean
}

export function RecipeMdView({ blocks, numbered = false }: RecipeMdViewProps) {
  let h2Index = 0
  return (
    <div>
      {blocks.map((b, i) => {
        if (b.kind === 'heading') {
          // The recipe's own h1 title — the surrounding page already shows one.
          if (b.level === 1) return null
          if (b.level === 2) {
            h2Index += 1
            const inline = <Inline text={b.text} />
            if (numbered) {
              return (
                <div key={i} style={{ margin: '32px 0 14px' }}>
                  <SectionHead no={`§${h2Index}`} title={inline} />
                </div>
              )
            }
            return (
              <h3 key={i} className="serif" style={{ fontSize: 17, margin: '22px 0 10px' }}>
                {inline}
              </h3>
            )
          }
          // h3 / sub-heads (e.g. cluster ids in the recipe markdown) — keep
          // them as ember-deep mono so they read as identifiers.
          return (
            <h4
              key={i}
              className="mono"
              style={{
                fontSize: 11,
                letterSpacing: '0.1em',
                color: 'var(--ember-deep)',
                margin: '16px 0 8px',
              }}
            >
              <Inline text={b.text} />
            </h4>
          )
        }
        if (b.kind === 'code') {
          return <CodeBlock key={i} lines={b.lines} />
        }
        return (
          <p
            key={i}
            style={{
              fontSize: 12.5,
              lineHeight: 1.7,
              color: 'var(--ink-2)',
              margin: '0 0 12px',
              whiteSpace: 'pre-wrap',
            }}
          >
            <Inline text={b.text} />
          </p>
        )
      })}
    </div>
  )
}
