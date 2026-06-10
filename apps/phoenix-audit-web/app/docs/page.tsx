// /docs — public product documentation (story-9.10 W0.4). Plain answers in
// the designer's idiom; screenshots are captured from the LIVE app by
// scripts/capture-docs-shots.ts and land in /public/docs-shots/.

import type { Metadata } from 'next'
import Image from 'next/image'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { Wordmark } from '@/components/ui/wordmark'

export const metadata: Metadata = {
  title: 'Docs — Phoenix Audit',
  description: 'How to register an agent, run an audit, and read the signed evidence.',
}

interface DocSection {
  no: string
  title: string
  body: string[]
  shot?: string
  shotAlt?: string
}

const SECTIONS: DocSection[] = [
  {
    no: '§1',
    title: 'What Phoenix Audit does',
    body: [
      'Phoenix Audit is an AI agent that audits your other AI agents. Point it at a production agent — a support copilot, a prior-authorization bot, a coding agent — and it runs an adversarial test battery (prompt injection, poisoned context, malformed tool output, latency spikes), reads the resulting traces in Arize Phoenix, clusters the failures into root causes, and produces a cryptographically signed, regulator-ready audit report in about 90 seconds.',
      'Three artifacts come out of every audit: a signed PDF report (Cloud KMS, Ed25519), a hardening recipe (prompt patches + tool-validation diffs + regression tests), and a GitLab merge request that files the fixes against your agent’s repository.',
    ],
    shot: 'chamber.png',
    shotAlt: 'The live audit chamber mid-run',
  },
  {
    no: '§2',
    title: 'Sign in — your register is private',
    body: [
      'Audits, target agents and monitoring schedules belong to the account that created them. Create an account with email and password (or Google). The landing page and the demo replay stay public; every product surface is behind sign-in.',
    ],
    shot: 'login.png',
    shotAlt: 'The sign-in surface',
  },
  {
    no: '§3',
    title: 'Register a target agent',
    body: [
      'Your first audit against a URL registers it: start a New audit, point it at a reachable address — an HTTPS endpoint, or an A2A address for ADK-native agents — and the target appears in your registry. Tier 1 agents (ADK over A2A) get full trace-depth audits; HTTP black-box targets are audited from the wire only, so verdicts are correct but root-cause clustering is per-test.',
      'The seeded “Demo Support Agent” is a real, deployed ADK agent you can audit immediately — it exists so your first audit needs zero setup.',
    ],
    shot: 'agents.png',
    shotAlt: 'The target agents registry',
  },
  {
    no: '§4',
    title: 'Run an audit',
    body: [
      'Every audit starts in the wizard (New audit) — there are no one-click live runs anywhere in the app. Pick the target, cap the probe budget if you want, and start. The live chamber streams every probe over SSE: injector battery, judge verdicts as they land, failure clustering, and the recipe being generated.',
      'A run that fails before completing produces no signed report — the run’s event log is the evidence trail, and the registry says so plainly. Phoenix Audit never renders a report it did not sign.',
    ],
    shot: 'wizard.png',
    shotAlt: 'The new-audit wizard',
  },
  {
    no: '§5',
    title: 'Read the evidence',
    body: [
      'Each finished audit files three artifacts. The signed PDF carries the verdict table, the root-cause clusters, the locked residency paragraph, and the Ed25519 signature fingerprint — verify it offline with the signature sidecar. The hardening recipe is also downloadable as Markdown. The merge request lands on your agent’s repo with the prompt patches and regression tests as reviewable diffs.',
      'Every failure links to its span-level evidence in Arize Phoenix — the trace is the source of truth, the report is the signed summary of it.',
    ],
    shot: 'report.png',
    shotAlt: 'A signed audit report',
  },
  {
    no: '§6',
    title: 'Monitor continuously',
    body: [
      'Monitoring schedules re-run the battery hourly or daily (EU AI Act Article 72 post-market monitoring). Scheduled runs land in your registry tagged “scheduled”, and email summaries deliver the verdict counts plus the signed-report link to the address on the schedule.',
    ],
    shot: 'monitoring.png',
    shotAlt: 'Continuous monitoring schedules',
  },
  {
    no: '§7',
    title: 'Sample data vs your data',
    body: [
      'Fresh accounts start empty — the stat blocks count your real audits only. The seeded Meridian sample world (the audits, agents and reports marked SAMPLE) exists so you can explore a finished audit before running one; it never mixes silently with your records, and sample fixtures are labeled everywhere they appear. The public demo replay at /replay is a recorded sample run.',
    ],
  },
]

function shotPath(file: string): string | null {
  // Screenshots are captured from the live app post-deploy; render only the
  // ones that exist — an empty frame is worse than no frame.
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
      <div className="shell" style={{ padding: '40px 40px 60px', maxWidth: 880 }}>
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
            <section key={s.no} style={{ marginBottom: 52 }}>
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
      <PageFoot />
    </div>
  )
}
