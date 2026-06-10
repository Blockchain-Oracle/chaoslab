'use client'

import { useMemo } from 'react'
import { replayStateAt, type RunEventsDocument } from '@/lib/replay'
import { AuditChamber } from './audit-chamber'
import { useAuditClock } from './use-audit-clock'

interface ReplayShellProps {
  doc: RunEventsDocument
  runLabel: string
}

/** Replays a recorded run's persisted timeline through the live reducer. */
export function ReplayShell({ doc, runLabel }: ReplayShellProps) {
  const { t, playing, setPlaying, seek, restart } = useAuditClock(doc.duration_sec, doc.run_id)
  const stream = useMemo(() => replayStateAt(doc.frames, t), [doc.frames, t])
  return (
    <AuditChamber
      mode="replay"
      runLabel={runLabel}
      stream={stream}
      elapsed={t}
      replay={{ t, duration: doc.duration_sec, playing, setPlaying, seek, restart }}
    />
  )
}
