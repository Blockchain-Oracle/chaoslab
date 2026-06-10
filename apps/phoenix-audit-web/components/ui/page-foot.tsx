import { Glyph } from './glyph'

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
        <span
          className="mono muted"
          style={{ fontSize: 10.5, letterSpacing: '0.06em', whiteSpace: 'nowrap' }}
        >
          PHOENIX AUDIT · APACHE-2.0
        </span>
        <span className="muted" style={{ fontSize: 12, flex: 1 }}>
          Built on Arize Phoenix &amp; Google Cloud Agent Builder · cites HarmBench, OWASP LLM Top
          10, MITRE ATLAS, CARES, Lakera PINT, deepankarm/agent-chaos
        </span>
        <a
          className="mono muted"
          style={{ fontSize: 10.5, letterSpacing: '0.06em', whiteSpace: 'nowrap' }}
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
