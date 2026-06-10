// Renders the run's REAL recipe.md in-app (story-9.13) — the designed diff
// idiom (colored +/- lines) applied to the patcher's actual output, replacing
// the raw-text-in-a-new-tab experience.

import { Fragment } from 'react'
import { diffLineKind, type RecipeBlock } from '@/lib/report-doc'

/** Minimal inline renderer for OUR generated markdown: `code` and **bold**.
 *  Unknown constructs render as-is — content must never disappear. */
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
    <pre className="codeblock" style={{ margin: '0 0 14px', whiteSpace: 'pre-wrap' }}>
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

export function RecipeMdView({ blocks }: { blocks: RecipeBlock[] }) {
  return (
    <div>
      {blocks.map((b, i) => {
        if (b.kind === 'heading') {
          if (b.level === 1) {
            return (
              <div key={i} className="kicker" style={{ margin: '0 0 14px' }}>
                <Inline text={b.text} />
              </div>
            )
          }
          return (
            <h3
              key={i}
              className={b.level === 2 ? 'serif' : 'mono'}
              style={
                b.level === 2
                  ? { fontSize: 17, margin: '22px 0 10px' }
                  : {
                      fontSize: 11,
                      letterSpacing: '0.1em',
                      color: 'var(--ember-deep)',
                      margin: '16px 0 8px',
                    }
              }
            >
              <Inline text={b.text} />
            </h3>
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
