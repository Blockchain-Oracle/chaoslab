'use client'

import { useCallback, useEffect, useRef } from 'react'

/** setTimeout that is cleared on unmount (and on re-schedule), so UI flash
 *  timers can't fire into an unmounted component. */
export function useSafeTimeout() {
  const idRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(
    () => () => {
      if (idRef.current) clearTimeout(idRef.current)
    },
    [],
  )
  return useCallback((fn: () => void, ms: number) => {
    if (idRef.current) clearTimeout(idRef.current)
    idRef.current = setTimeout(fn, ms)
  }, [])
}
