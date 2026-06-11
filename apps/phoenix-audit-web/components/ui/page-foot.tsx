import Link from 'next/link'
import { Glyph } from './glyph'

const META_LINK_STYLE = {
  fontSize: 10.5,
  letterSpacing: '0.06em',
  whiteSpace: 'nowrap' as const,
}

export function PageFoot() {
  return (
    <footer style={{ borderTop: '1px solid var(--hairline)', marginTop: 80 }}>
      <div
        className="shell"
        style={{
          padding: '26px 40px',
          display: 'flex',
          gap: 22,
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <Glyph size={15} color="var(--ink-3)" />
        <span className="mono muted" style={META_LINK_STYLE}>
          PHOENIX AUDIT · APACHE-2.0
        </span>
        <span className="muted" style={{ fontSize: 12, flex: 1 }}>
          Built on Arize Phoenix &amp; Google Cloud Agent Builder · cites HarmBench, OWASP LLM Top
          10, MITRE ATLAS, CARES, Lakera PINT, deepankarm/agent-chaos
        </span>
        {/* Story-9.20 follow-up: surface the docs page in the footer so a
         *  curious operator can find the manual without already knowing the
         *  URL. The topbar stays at 5 items — this is the lighter-touch
         *  discoverability fix. */}
        <Link className="mono muted" style={META_LINK_STYLE} href="/docs">
          Docs ↗
        </Link>
        <a
          className="mono muted"
          style={META_LINK_STYLE}
          href="https://github.com/Blockchain-Oracle/phoenix-audit"
          target="_blank"
          rel="noreferrer noopener"
        >
          GITHUB ↗
        </a>
      </div>
    </footer>
  )
}
