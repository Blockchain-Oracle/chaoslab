'use client'

interface TransportProps {
  t: number
  /** Real recorded duration of the replayed run, from events.json. */
  duration: number
  playing: boolean
  setPlaying: (next: boolean) => void
  seek: (t: number) => void
  restart: () => void
}

export function Transport({ t, duration, playing, setPlaying, seek, restart }: TransportProps) {
  const label = playing ? 'Pause' : t >= duration ? 'Replay' : 'Play'
  return (
    <div
      style={{
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 70,
        borderTop: '1px solid var(--chamber-line)',
        background: 'rgba(16,12,7,0.92)',
        backdropFilter: 'blur(8px)',
      }}
    >
      <div
        className="replay-transport"
        style={{
          maxWidth: 1180,
          margin: '0 auto',
          padding: '12px 40px',
          display: 'flex',
          alignItems: 'center',
          gap: 18,
        }}
      >
        <button className="btn small" style={{ minWidth: 86 }} onClick={() => setPlaying(!playing)}>
          {label}
        </button>
        <button className="btn small ghost" onClick={restart}>
          Restart
        </button>
        <input
          type="range"
          min={0}
          max={duration}
          step={0.05}
          value={t}
          onChange={(e) => seek(parseFloat(e.target.value))}
          style={{ flex: 1, accentColor: 'var(--ember)' }}
          aria-label="Scrub audit playback"
        />
        <span
          className="mono num"
          style={{
            fontSize: 11,
            color: 'var(--chamber-ink-2)',
            width: 130,
            textAlign: 'right',
          }}
        >
          {t.toFixed(1)}s / {duration.toFixed(0)}s · replay
        </span>
      </div>
    </div>
  )
}
