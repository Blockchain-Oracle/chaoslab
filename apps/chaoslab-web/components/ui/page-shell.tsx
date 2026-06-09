'use client'

import { useEffect, useState, type ReactNode } from 'react'

// Wraps each route's content so the designer's entrance animations
// (.entering .page-enter, .entering .rise) play on mount and then settle.
// Mirrors the gate in app.jsx where the App component toggles `entering`
// for ~1s after every navigation.
interface PageShellProps {
  label?: string
  children: ReactNode
}

export function PageShell({ label, children }: PageShellProps) {
  const [entering, setEntering] = useState(true)
  useEffect(() => {
    const id = setTimeout(() => setEntering(false), 1000)
    return () => clearTimeout(id)
  }, [])
  return (
    <div data-screen-label={label ?? 'page'} className={entering ? 'entering' : ''}>
      {children}
    </div>
  )
}
