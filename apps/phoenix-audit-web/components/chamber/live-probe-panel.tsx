import { FaultClass, SpanLink, Verdict } from '@/components/ui/stamps'
import { phoenixSpanUrl } from '@/lib/phoenix-links'
import type { LiveCluster, LiveProbe, LiveRecipe, LiveReport } from '@/lib/sse-bridge'

// Renders REAL backend per-probe events. Deliberately leaner than the
// fixture-driven ProbeLedger: no citations / session-mode / honored chips,
// because the backend doesn't report those yet — showing them would be
// invention, not telemetry. Rows carry exactly what the wire carries.

function LiveProbeRow({
  probe,
  phoenixUiBase,
  phoenixProject,
}: {
  probe: LiveProbe
  phoenixUiBase: string | null
  phoenixProject: string | null
}) {
  const landed = probe.state === 'done'
  const spanHref = phoenixSpanUrl(phoenixUiBase, phoenixProject, probe.spanId)
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
          {probe.rubricError ? (
            <span className="fallback-flag" style={{ fontSize: 9.5 }}>
              ◌ RUBRIC ERROR — judge call failed; no verdict scored
            </span>
          ) : null}
        </div>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          {probe.spanId ? (
            <SpanLink id={probe.spanId} href={spanHref} />
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
  /** Authoritative tally from the backend's complete frame — preferred over
   *  frontend-derived counts (which undercount on late join). */
  summary?: { passed: number; failed: number; errored: number } | null
  /** Story-9.21: Phoenix UI deep-link config from RunDetailResponse. Null
   *  ⇒ no link on any span (handled by phoenixSpanUrl + SpanLink). */
  phoenixUiBase?: string | null
  phoenixProject?: string | null
}

export function LiveProbeLedger({
  probes,
  summary,
  phoenixUiBase = null,
  phoenixProject = null,
}: LiveProbeLedgerProps) {
  const done = probes.filter((p) => p.state === 'done').length
  const pass = summary?.passed ?? probes.filter((p) => p.verdict === 'pass').length
  const fail = summary?.failed ?? probes.filter((p) => p.verdict === 'fail').length
  const errored = summary?.errored ?? probes.filter((p) => p.verdict === 'error').length
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
        {errored > 0 ? (
          <span className="mono num" style={{ fontSize: 11, color: 'var(--warn)' }}>
            {errored} error
          </span>
        ) : null}
        <span className="mono num" style={{ fontSize: 11, color: 'var(--chamber-ink-3)' }}>
          {done}/{probes.length}
        </span>
      </div>
      {probes.map((p) => (
        <LiveProbeRow
          key={p.n}
          probe={p}
          phoenixUiBase={phoenixUiBase}
          phoenixProject={phoenixProject}
        />
      ))}
    </div>
  )
}

export function LiveReportRow({ report }: { report: LiveReport | null }) {
  if (!report) return null
  // A malformed `report` frame (all URLs null) must not render success chrome.
  if (!report.skippedReason && !report.pdfUrl && !report.signatureUrl) {
    return null
  }
  if (report.skippedReason) {
    return (
      <div
        style={{
          border: '1px dashed var(--warn)',
          borderRadius: 4,
          padding: '12px 16px',
          background: 'rgba(190,150,40,0.07)',
        }}
      >
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--warn)' }}>
          ⚠ SIGNED REPORT NOT GENERATED — {report.skippedReason.replace(/_/g, ' ')}. The audit ran;
          nothing was signed or filed.
        </span>
      </div>
    )
  }
  return (
    <div
      style={{
        border: '1px solid var(--pass-glow)',
        borderRadius: 4,
        padding: '12px 16px',
        background: 'rgba(76,175,125,0.06)',
        display: 'flex',
        gap: 18,
        alignItems: 'baseline',
        flexWrap: 'wrap',
      }}
    >
      <span
        className="mono"
        style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--pass-glow)' }}
      >
        SIGNED AUDIT REPORT · ED25519 · CLOUD KMS
      </span>
      <span style={{ flex: 1 }}></span>
      {report.pdfUrl ? (
        <a className="span-link" href={report.pdfUrl} target="_blank" rel="noreferrer noopener">
          report.pdf ↗
        </a>
      ) : null}
      {report.jsonUrl ? (
        <a className="span-link" href={report.jsonUrl} target="_blank" rel="noreferrer noopener">
          report.json ↗
        </a>
      ) : null}
      {report.signatureUrl ? (
        <a
          className="span-link"
          href={report.signatureUrl}
          target="_blank"
          rel="noreferrer noopener"
        >
          signature.json ↗
        </a>
      ) : null}
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
        {settled && !cluster.skipped ? (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--ember-glow)' }}>
            {cluster.totalFailures} failures → {cluster.clusters}{' '}
            {cluster.clusters === 1 ? 'cause' : 'causes'}
          </span>
        ) : settled ? (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--warn)' }}>
            SKIPPED
          </span>
        ) : null}
      </div>
      {settled && cluster.skipped ? (
        <div>
          <div style={{ fontSize: 13, color: 'var(--chamber-ink-2)', lineHeight: 1.6 }}>
            Failures occurred, but none produced usable span evidence
            {cluster.excludedTransportFailures > 0
              ? ` (${cluster.excludedTransportFailures} transport-level)`
              : ''}
            {cluster.rubricErrors > 0 ? ` (${cluster.rubricErrors} rubric errors)` : ''} —
            root-cause clustering was skipped. The signed report will state this explicitly.
          </div>
        </div>
      ) : settled ? (
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
            {cluster.excludedTransportFailures > 0
              ? ` · ${cluster.excludedTransportFailures} transport failures excluded`
              : ''}
          </div>
          {cluster.annotationWritebackFailed ? (
            <div className="fallback-flag" style={{ marginTop: 8, fontSize: 9.5 }}>
              ⚠ PHOENIX ANNOTATION WRITE-BACK FAILED — clustering result is valid; span annotations
              were not persisted
            </div>
          ) : null}
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
