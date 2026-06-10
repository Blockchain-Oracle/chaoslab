'use client'

import { useRef } from 'react'
import type { LiveCluster, LiveProbe, LiveRecipe, LiveReport } from '@/lib/sse-bridge'
import type { Phase } from '@/lib/types'
import { deriveAudit } from '@/lib/timeline'
import { CascadeOverlay } from './cascade-overlay'
import { ChamberHeader } from './chamber-header'
import { ClusterCard } from './cluster-card'
import { EventFeed } from './event-feed'
import { LiveClusterCard, LiveProbeLedger, LiveRecipeCard, LiveReportRow } from './live-probe-panel'
import { Pipeline } from './pipeline'
import { ProbeLedger } from './probe-ledger'
import { Receipt } from './receipt'
import { RecipeCard } from './recipe-card'
import { Transport } from './transport'
import { useAuditClock } from './use-audit-clock'

interface AuditChamberProps {
  mode: 'replay' | 'live'
  /** Live-mode: the REAL run id for the header label. */
  runId?: string
  /** Live-mode only: surface the "demo pacing" disclosure (per-probe ticker
   *  derives from the timeline because the backend doesn't emit per-probe
   *  SSE events yet). Wired in via the SSE bridge. */
  demoPacing?: boolean
  /** Live-mode only: real phase reported by the SSE stream. Overrides the
   *  phase displayed in the header + pipeline + cluster placeholder. The
   *  per-probe ticker still derives from the local timeline clock; the
   *  clock is capped by `clockCeiling` so it can't drift ahead of the
   *  real backend phase. */
  livePhase?: Phase
  /** Live-mode only: upper bound on the local clock, derived from livePhase
   *  by the SSE bridge. */
  clockCeiling?: number
  /** Live-mode only: raw SSE wire lines for the event feed. */
  liveLines?: string[]
  /** Live-mode only: whether the EventSource is currently open. Drives the
   *  truthfulness of the header's LIVE indicator. */
  liveConnected?: boolean
  /** Live-mode only: terminal stream error detail; renders the failure
   *  banner so a dead run is never visually indistinguishable from a
   *  running one. */
  liveError?: string | null
  /** Live-mode only: REAL per-probe events. Non-empty switches the right
   *  canvas from the timeline fixtures to wire-truth rendering and hides
   *  the DEMO PACING disclosure. */
  liveProbes?: LiveProbe[]
  liveCluster?: LiveCluster | null
  liveRecipe?: LiveRecipe | null
  /** Live-mode only: authoritative tally from the complete frame. */
  liveSummary?: { passed: number; failed: number; errored: number } | null
  /** Live-mode only: signed-report artifact URLs (or the loud skip reason). */
  liveReport?: LiveReport | null
}

export function AuditChamber({
  mode,
  runId,
  demoPacing,
  livePhase,
  clockCeiling,
  liveLines,
  liveConnected,
  liveError,
  liveProbes,
  liveCluster,
  liveRecipe,
  liveSummary,
  liveReport,
}: AuditChamberProps) {
  const ceiling = clockCeiling
  const { t, playing, setPlaying, seek, restart } = useAuditClock(
    mode,
    ceiling !== undefined ? { ceiling } : {},
  )
  const baseState = deriveAudit(t)
  const s = livePhase ? { ...baseState, phase: livePhase } : baseState
  const hasRealProbes = (liveProbes?.length ?? 0) > 0
  // Live runs NEVER render the fixture canvases — before the first real
  // probe event the live components show their own pending states. A real
  // failed run animating fake verdicts was story-9.10's worst finding.
  const fixtureCanvas = mode !== 'live'

  const arenaRef = useRef<HTMLDivElement | null>(null)
  const clusterRef = useRef<HTMLDivElement | null>(null)
  const failRefs = [
    useRef<HTMLSpanElement | null>(null),
    useRef<HTMLSpanElement | null>(null),
    useRef<HTMLSpanElement | null>(null),
  ]

  // Replay multiplies t by ~3.36 to display the projected 87s wall-clock the
  // audit really takes. Live uses real t directly.
  const elapsedDisplay = mode === 'replay' ? t * 3.36 : t

  return (
    <div className="chamber-scope" style={{ paddingBottom: 90 }}>
      <div className="grain"></div>
      <ChamberHeader
        s={s}
        elapsedDisplay={elapsedDisplay}
        mode={mode}
        demoPacing={demoPacing && !hasRealProbes}
        connected={liveConnected}
        runLabel={runId}
      />

      {liveError ? (
        <div
          style={{
            maxWidth: 1180,
            margin: '20px auto 0',
            padding: '0 40px',
            position: 'relative',
            zIndex: 2,
          }}
        >
          <div
            style={{
              border: '1px solid var(--fail-glow)',
              borderRadius: 4,
              padding: '14px 18px',
              background: 'rgba(220,90,60,0.08)',
            }}
          >
            <div
              className="mono"
              style={{
                fontSize: 10.5,
                letterSpacing: '0.14em',
                color: 'var(--fail-glow)',
                marginBottom: 6,
              }}
            >
              ✕ AUDIT STREAM ERROR
            </div>
            <div style={{ fontSize: 13, color: 'var(--chamber-ink-2)', lineHeight: 1.6 }}>
              {liveError}. Nothing was signed or filed. Completed probes are preserved in the
              Phoenix trace.
            </div>
          </div>
        </div>
      ) : null}

      <div
        ref={arenaRef}
        style={{
          maxWidth: 1180,
          margin: '0 auto',
          padding: '30px 40px 0',
          display: 'grid',
          gridTemplateColumns: '390px 1fr',
          gap: 36,
          position: 'relative',
          zIndex: 2,
        }}
      >
        {fixtureCanvas ? (
          <CascadeOverlay s={s} arenaRef={arenaRef} failRefs={failRefs} clusterRef={clusterRef} />
        ) : null}

        {/* left rail: pipeline + event feed + header warning */}
        <div style={{ display: 'grid', gap: 30, alignContent: 'start' }}>
          <Pipeline s={s} />
          <EventFeed t={t} liveLines={liveLines} />

          {s.headerWarn && fixtureCanvas ? (
            <div
              style={{
                border: '1px dashed var(--warn)',
                borderRadius: 4,
                padding: '12px 14px',
                background: 'rgba(190,150,40,0.07)',
              }}
            >
              <div
                className="mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: '0.12em',
                  color: 'oklch(0.78 0.12 90)',
                  marginBottom: 6,
                }}
              >
                ⚠ HEADER CONVENTION
              </div>
              <div
                style={{
                  fontSize: 12.5,
                  color: 'var(--chamber-ink-2)',
                  lineHeight: 1.6,
                }}
              >
                Probe 06 did not confirm audit-mode headers. Side-effecting tool calls during this
                audit may have executed for real. The signed report will include the locked warning
                paragraph.
              </div>
            </div>
          ) : null}
        </div>

        {/* right canvas: ledger + cluster + recipe.
            Real wire events take precedence over the timeline fixtures. */}
        <div style={{ display: 'grid', gap: 22, alignContent: 'start' }}>
          {!fixtureCanvas ? (
            <>
              <LiveProbeLedger probes={liveProbes ?? []} summary={liveSummary ?? null} />
              <LiveReportRow report={liveReport ?? null} />
            </>
          ) : (
            <ProbeLedger s={s} failRefs={failRefs} />
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 22 }}>
            {!fixtureCanvas ? (
              <>
                <LiveClusterCard cluster={liveCluster ?? null} phase={s.phase} />
                <LiveRecipeCard recipe={liveRecipe ?? null} phase={s.phase} />
              </>
            ) : (
              <>
                <ClusterCard s={s} clusterRef={clusterRef} />
                <RecipeCard s={s} />
              </>
            )}
          </div>
        </div>
      </div>

      {/* The receipt hard-codes fixture stats + demo links — it must NEVER
          overlay a real run (late-join with zero probe frames included). */}
      {s.receipt && mode === 'replay' ? <Receipt mode={mode} /> : null}
      {mode === 'replay' ? (
        <Transport
          t={t}
          playing={playing}
          setPlaying={setPlaying}
          seek={seek}
          restart={restart}
          mode={mode}
        />
      ) : null}
    </div>
  )
}
