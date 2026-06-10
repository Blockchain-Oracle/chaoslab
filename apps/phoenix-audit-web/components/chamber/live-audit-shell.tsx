'use client'

import { useEffect, useRef, useState } from 'react'
import { useAuditStream } from '@/lib/sse-bridge'
import { AuditChamber } from './audit-chamber'

interface LiveAuditShellProps {
  runId: string
}

const TERMINAL = new Set(['succeeded', 'failed'])

export function LiveAuditShell({ runId }: LiveAuditShellProps) {
  const stream = useAuditStream(runId)
  const [elapsed, setElapsed] = useState(0)
  const startedRef = useRef<number | null>(null)
  const terminal = TERMINAL.has(stream.phase) || stream.error !== null

  useEffect(() => {
    if (terminal) return
    startedRef.current ??= performance.now()
    const id = setInterval(() => {
      if (startedRef.current !== null) {
        setElapsed((performance.now() - startedRef.current) / 1000)
      }
    }, 250)
    return () => clearInterval(id)
  }, [terminal])

  return (
    <AuditChamber
      mode="live"
      runLabel={`${runId} · live audit`}
      stream={stream}
      elapsed={elapsed}
    />
  )
}
