import { A } from '../ui/link'
import { Seal } from '../ui/seal'

// Hero specimen — a miniature signed receipt, stamped.
const SPECIMEN_ROWS: ReadonlyArray<[string, string]> = [
  ['Target agent', 'prior-auth · Google ADK'],
  ['Regulatory framework', 'EU AI Act · high-risk'],
  ['Adversarial tests', '6 · HarmBench / OWASP / ATLAS'],
  ['Verdict', '3 pass · 3 fail'],
  ['Root cause clusters', '1'],
  ['Hardening recipe', 'patched in 4.1 s'],
  ['Wall-clock', '87.3 s'],
]

function HeroSpecimen() {
  return (
    <div className="rise rise-3 hero-specimen" style={{ position: 'relative', width: 372 }}>
      <div
        style={{
          background: '#fff',
          border: '1px solid var(--hairline)',
          borderRadius: 'var(--r-lg)',
          boxShadow: '0 24px 60px rgba(28,23,18,0.14), 0 2px 6px rgba(28,23,18,0.06)',
          transform: 'rotate(1.2deg)',
          padding: '26px 26px 20px',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            borderBottom: '1px solid var(--ink)',
            paddingBottom: 10,
            marginBottom: 14,
          }}
        >
          <span className="mono" style={{ fontSize: 10, letterSpacing: '0.2em' }}>
            SIGNED AUDIT REPORT
          </span>
          <span className="mono muted" style={{ fontSize: 10 }}>
            run_9f3c2ab81d4e
          </span>
        </div>
        {SPECIMEN_ROWS.map(([k, v]) => (
          <div key={k} className="leader-row" style={{ padding: '5px 0' }}>
            <span className="mono muted" style={{ fontSize: 10.5, letterSpacing: '0.04em' }}>
              {k}
            </span>
            <span className="leader-fill"></span>
            <span className="mono" style={{ fontSize: 10.5 }}>
              {v}
            </span>
          </div>
        ))}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: 16,
          }}
        >
          <span className="mono muted" style={{ fontSize: 9.5, letterSpacing: '0.06em' }}>
            KMS 4B:9E:F1:0A
          </span>
          <span className="stamp pass">Filed</span>
        </div>
      </div>
      <div
        className="hero-seal"
        style={{
          position: 'absolute',
          right: -42,
          bottom: -38,
          filter: 'drop-shadow(0 8px 18px rgba(28,23,18,0.18))',
        }}
      >
        <Seal size={132} />
      </div>
    </div>
  )
}

export function Hero() {
  return (
    <section className="shell hero-grid" style={{ padding: '84px 40px 90px' }}>
      <div>
        <div className="kicker rise rise-1" style={{ marginBottom: 22 }}>
          Regulator-ready audits of production AI agents
        </div>
        <h1
          className="display rise rise-1"
          style={{ fontSize: 'clamp(44px, 5.4vw, 68px)', marginBottom: 26 }}
        >
          The AI agent that <em>audits</em> your other AI&nbsp;agents.
        </h1>
        <p
          className="rise rise-2"
          style={{
            fontSize: 17,
            lineHeight: 1.65,
            color: 'var(--ink-2)',
            maxWidth: 540,
            marginBottom: 34,
            textWrap: 'pretty',
          }}
        >
          Point Phoenix Audit at any production AI agent. It runs an adversarial test battery drawn
          from HarmBench, OWASP LLM Top 10, MITRE ATLAS and CARES, clusters the failures into root
          causes, generates a hardening recipe — and delivers a cryptographically signed audit
          report. In roughly <strong style={{ color: 'var(--ink)' }}>90 seconds</strong>.
        </p>
        <div
          className="rise rise-2"
          style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}
        >
          <A to="new" className="btn ember">
            Run audit
          </A>
          <A to="replay" className="btn">
            Watch a sample audit · 22 s
          </A>
        </div>
        <div
          className="rise rise-3 mono muted"
          style={{
            fontSize: 11,
            letterSpacing: '0.08em',
            marginTop: 26,
            display: 'flex',
            gap: 18,
            flexWrap: 'wrap',
          }}
        >
          <span>EU AI ACT</span>
          <span>·</span>
          <span>NIST AI RMF</span>
          <span>·</span>
          <span>HIPAA</span>
          <span>·</span>
          <span>SOC 2</span>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <HeroSpecimen />
      </div>
    </section>
  )
}
