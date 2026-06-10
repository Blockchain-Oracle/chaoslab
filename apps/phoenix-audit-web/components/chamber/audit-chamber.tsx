'use client'

// Wire-truth chamber (story-9.11): ONE render path for live and replay.
// Live mode is fed by the SSE bridge; replay mode is fed by the persisted
// timeline folded through the same reducer. No fixture canvases exist.

import type { AuditStreamState } from '@/lib/sse-bridge'
import { ChamberHeader } from './chamber-header'
import { EventFeed } from './event-feed'
import { LiveClusterCard, LiveProbeLedger, LiveRecipeCard, LiveReportRow } from './live-probe-panel'
import { Pipeline } from './pipeline'
import { Transport } from './transport'

export interface ReplayControls {
  t: number
  duration: number
  playing: boolean
  setPlaying: (next: boolean) => void
  seek: (next: number) => void
  restart: () => void
}

interface AuditChamberProps {
  mode: 'replay' | 'live'
  /** Header line, e.g. "run_x · target.example · EU AI Act (sample replay)". */
  runLabel: string
  stream: AuditStreamState
  /** Displayed elapsed seconds — live wall-clock or the replay scrub time. */
  elapsed: number
  /** Replay-only transport controls. */
  replay?: ReplayControls
}

export function AuditChamber({ mode, runLabel, stream, elapsed, replay }: AuditChamberProps) {
  return (
    <div className="chamber-scope" style={{ paddingBottom: 90 }}>
      <div className="grain"></div>
      <ChamberHeader
        phase={stream.phase}
        elapsedDisplay={elapsed}
        mode={mode}
        connected={stream.connected}
        runLabel={runLabel}
      />

      {stream.error ? (
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
              {stream.error}. Nothing was signed or filed. Completed probes are preserved in the
              Phoenix trace.
            </div>
          </div>
        </div>
      ) : null}

      <div
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
        {/* left rail: pipeline + event feed */}
        <div style={{ display: 'grid', gap: 30, alignContent: 'start' }}>
          <Pipeline phase={stream.phase} />
          <EventFeed lines={stream.wireLines} />
        </div>

        {/* right canvas: wire-truth ledger + cluster + recipe + report */}
        <div style={{ display: 'grid', gap: 22, alignContent: 'start' }}>
          <LiveProbeLedger probes={stream.probes} summary={stream.summary} />
          <LiveReportRow report={stream.report} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 22 }}>
            <LiveClusterCard cluster={stream.cluster} phase={stream.phase} />
            <LiveRecipeCard recipe={stream.recipe} phase={stream.phase} />
          </div>
        </div>
      </div>

      {mode === 'replay' && replay ? (
        <Transport
          t={replay.t}
          duration={replay.duration}
          playing={replay.playing}
          setPlaying={replay.setPlaying}
          seek={replay.seek}
          restart={replay.restart}
        />
      ) : null}
    </div>
  )
}
