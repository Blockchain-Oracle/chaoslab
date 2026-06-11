// /docs — public product documentation (story-9.10 W0.4; navigable manual
// per story-9.20). Plain answers in the designer's idiom; the section model
// lives in lib/docs-sections (shared with the rail + tests); screenshots are
// captured from the LIVE app by scripts/capture-docs-shots.ts and land in
// /public/docs-shots/.

import type { Metadata } from 'next'
import Image from 'next/image'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { DocsRail } from '@/components/docs/docs-rail'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { Wordmark } from '@/components/ui/wordmark'
import { SECTIONS } from '@/lib/docs-sections'

export const metadata: Metadata = {
  title: 'Docs — Phoenix Audit',
  description: 'How to register an agent, run an audit, and read the signed evidence.',
}

function shotPath(file: string): string | null {
  // Renders only screenshots that exist — an empty frame is worse than no
  // frame. NOTE: this page prerenders, so existsSync runs at BUILD time;
  // captures must be committed (scripts/capture-docs-shots.ts) and shipped
  // by the next build, not dropped onto a running container.
  const abs = join(process.cwd(), 'public', 'docs-shots', file)
  return existsSync(abs) ? `/docs-shots/${file}` : null
}

export default function DocsPage() {
  return (
    <div className="page-enter">
      <header className="login-strip">
        <A to="" style={{ textDecoration: 'none', color: 'inherit', display: 'flex' }}>
          <Wordmark size={16} glyph={18} />
        </A>
        <div style={{ display: 'flex', gap: 22, alignItems: 'center' }}>
          <A
            to="replay"
            className="mono"
            style={{ fontSize: 10.5, letterSpacing: '0.14em', color: 'var(--ink-3)' }}
          >
            DEMO REPLAY
          </A>
          <A to="login" className="btn small ember">
            Sign in
          </A>
        </div>
      </header>
      <div className="shell docs-shell" style={{ padding: '40px 40px 60px' }}>
        <DocsRail />
        <div className="docs-content">
          <div className="kicker" style={{ marginBottom: 12 }}>
            Documentation
          </div>
          <h1 className="display" style={{ fontSize: 40, marginBottom: 10 }}>
            How Phoenix Audit works.
          </h1>
          <p className="muted" style={{ maxWidth: 620, marginBottom: 48 }}>
            From registering your first agent to filing signed evidence with your regulator — every
            surface, in the order you will meet it.
          </p>

          {SECTIONS.map((s) => {
            const src = s.shot ? shotPath(s.shot) : null
            return (
              <section key={s.id} id={s.id} style={{ marginBottom: 52, scrollMarginTop: 24 }}>
                <SectionHead no={s.no} title={s.title} />
                {s.body.map((p, i) => (
                  <p
                    key={i}
                    style={{
                      fontSize: 14,
                      lineHeight: 1.75,
                      color: 'var(--ink-2)',
                      marginBottom: 12,
                    }}
                  >
                    {p}
                  </p>
                ))}
                {src ? (
                  <Image
                    src={src}
                    alt={s.shotAlt ?? s.title}
                    width={1280}
                    height={800}
                    style={{
                      width: '100%',
                      height: 'auto',
                      border: '1px solid var(--hairline)',
                      borderRadius: 'var(--r-lg)',
                      marginTop: 8,
                    }}
                  />
                ) : null}
              </section>
            )
          })}
        </div>
      </div>
      <PageFoot />
    </div>
  )
}
