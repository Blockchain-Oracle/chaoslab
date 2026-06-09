import { FaultClass, SpanLink, Verdict } from '@/components/ui/stamps'
import type { LiveCluster, LiveProbe, LiveRecipe } from '@/lib/sse-bridge'

// Renders REAL backend per-probe events. Deliberately leaner than the
// fixture-driven ProbeLedger: no citations / session-mode / honored chips,
// because the backend doesn't report those yet — showing them would be
// invention, not telemetry. Rows carry exactly what the wire carries.

function LiveProbeRow({ probe }: { probe: LiveProbe }) {
  const landed = probe.state === 'done'
  return (
    <div className={'probe-row ' + (landed ? 'landed' : 'running')}>
      <span className="mono" style={{ fontSize: 11, color: 'var(--chamber-ink-3)' }}>
        {String(probe.n).padStart(2, '0')}
      </span>
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            display: 'flex',
            gap: 9,
            alignItems: 'center',
            flexWrap: 'wrap',
            marginBottom: 3,
          }}
        >
          <span style={{ fontSize: 13.5, color: 'var(--chamber-ink)' }}>
            Adversarial probe {String(probe.n).padStart(2, '0')}
          </span>
          <FaultClass name={probe.faultClass} />
          {probe.transportError ? (
            <span
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--fail-glow)', letterSpacing: '0.06em' }}
            >
              TRANSPORT ERROR
            </span>
          ) : null}
        </div>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          {probe.spanId ? (
            <SpanLink id={probe.spanId} />
          ) : (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--chamber-ink-3)' }}>
              {landed ? (
                (probe.status ?? 'done')
              ) : (
                <span>
                  probing<span className="blink-caret">▌</span>
                </span>
              )}
            </span>
          )}
          {typeof probe.score === 'number' ? (
            <span className="mono num" style={{ fontSize: 10.5, color: 'var(--chamber-ink-3)' }}>
              score {probe.score.toFixed(2)}
            </span>
          ) : null}
        </div>
      </div>
      <span style={{ justifySelf: 'end' }}>
        {probe.verdict ? (
          <span className="verdict-in" style={{ display: 'inline-flex' }}>
            <Verdict v={probe.verdict} />
          </span>
        ) : (
          <span className="stamp neutral">{landed ? 'judging' : '·····'}</span>
        )}
      </span>
    </div>
  )
}

interface LiveProbeLedgerProps {
  probes: LiveProbe[]
}

export function LiveProbeLedger({ probes }: LiveProbeLedgerProps) {
  const done = probes.filter((p) => p.state === 'done').length
  const pass = probes.filter((p) => p.verdict === 'pass').length
  const fail = probes.filter((p) => p.verdict === 'fail').length
  return (
    <div style={{ border: '1px solid var(--chamber-line)', borderRadius: 4 }}>
      <div
        style={{
          padding: '11px 18px',
          borderBottom: '1px solid var(--chamber-line)',
          display: 'flex',
          alignItems: 'baseline',
          gap: 12,
        }}
      >
        <span
          className="mono"
          style={{ fontSize: 10, letterSpacing: '0.2em', color: 'var(--chamber-ink-3)' }}
        >
          ADVERSARIAL TEST BATTERY — LIVE
        </span>
        <span style={{ flex: 1 }}></span>
        <span className="mono num" style={{ fontSize: 11, color: 'var(--pass-glow)' }}>
          {pass} pass
        </span>
        <span className="mono num" style={{ fontSize: 11, color: 'var(--fail-glow)' }}>
          {fail} fail
        </span>
        <span className="mono num" style={{ fontSize: 11, color: 'var(--chamber-ink-3)' }}>
          {done}/{probes.length}
        </span>
      </div>
      {probes.map((p) => (
        <LiveProbeRow key={p.n} probe={p} />
      ))}
    </div>
  )
}

interface LiveClusterCardProps {
  cluster: LiveCluster | null
  phase: string
}

export function LiveClusterCard({ cluster, phase }: LiveClusterCardProps) {
  const settled = cluster !== null
  return (
    <div
      style={{
        border: '1px solid ' + (settled ? 'var(--ember-glow)' : 'var(--chamber-line)'),
        borderRadius: 4,
        padding: '16px 18px',
        background: settled ? 'rgba(228,150,70,0.07)' : 'rgba(255,255,255,0.02)',
        boxShadow: settled ? '0 0 40px rgba(228,150,70,0.14)' : 'none',
        transition: 'border-color 0.6s ease, box-shadow 0.6s ease, background 0.6s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 10,
          marginBottom: 8,
          alignItems: 'baseline',
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.16em',
            color: settled ? 'var(--ember-glow)' : 'var(--chamber-ink-3)',
          }}
        >
          ROOT CAUSE CLUSTER{settled && cluster.clusterIds[0] ? ' · ' + cluster.clusterIds[0] : ''}
        </span>
        {settled ? (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--ember-glow)' }}>
            {cluster.totalFailures} failures → {cluster.clusters}{' '}
            {cluster.clusters === 1 ? 'cause' : 'causes'}
          </span>
        ) : null}
      </div>
      {settled ? (
        <div>
          {cluster.rootCauses.map((rc, i) => (
            <div
              key={i}
              className="serif"
              style={{ fontSize: 16, lineHeight: 1.45, marginBottom: 8 }}
            >
              {rc}
            </div>
          ))}
          <div className="mono" style={{ fontSize: 10, color: 'var(--chamber-ink-3)' }}>
            clustered by gemini-3.5-flash
          </div>
        </div>
      ) : (
        <div className="mono" style={{ fontSize: 11.5, color: 'var(--chamber-ink-3)' }}>
          {phase === 'judge' ? (
            <span>
              clustering failures<span className="blink-caret">▌</span>
            </span>
          ) : (
            'awaiting judge phase'
          )}
        </div>
      )}
    </div>
  )
}

interface LiveRecipeCardProps {
  recipe: LiveRecipe | null
  phase: string
}

export function LiveRecipeCard({ recipe, phase }: LiveRecipeCardProps) {
  const generated = recipe !== null
  const started = generated || phase === 'patcher'
  return (
    <div
      style={{
        border: '1px solid var(--chamber-line)',
        borderRadius: 4,
        opacity: started ? 1 : 0.35,
        transition: 'opacity 0.5s ease',
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          letterSpacing: '0.16em',
          color: 'var(--chamber-ink-3)',
          padding: '10px 16px',
          borderBottom: '1px solid var(--chamber-line-soft)',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>HARDENING RECIPE</span>
        <span style={{ color: generated ? 'var(--pass-glow)' : 'var(--chamber-ink-3)' }}>
          {generated ? 'GENERATED' : started ? 'GENERATING…' : 'AWAITING PATCHER'}
        </span>
      </div>
      <div
        className="mono"
        style={{ fontSize: 11.5, lineHeight: 1.8, padding: '12px 16px', minHeight: 188 }}
      >
        {generated ? (
          <div>
            <div style={{ color: 'var(--chamber-ink-2)' }}>{recipe.recipeId}</div>
            {recipe.markdownUrl ? (
              <a
                className="span-link"
                href={recipe.markdownUrl}
                target="_blank"
                rel="noreferrer noopener"
                style={{ display: 'inline-block', marginTop: 8 }}
              >
                markdown artifact ↗
              </a>
            ) : null}
          </div>
        ) : started ? (
          <span className="blink-caret" style={{ color: 'var(--ember-glow)' }}>
            ▌
          </span>
        ) : null}
      </div>
    </div>
  )
}
