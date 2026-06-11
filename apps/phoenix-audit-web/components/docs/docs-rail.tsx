'use client'

// Story-9.20 Surface D — sticky section rail with scroll spy. Renders from
// the shared SECTIONS model; the active state comes from the pure
// activeSection reducer fed by an IntersectionObserver (no scroll listeners).

import { useEffect, useState } from 'react'
import { SECTIONS, activeSection } from '@/lib/docs-sections'

export function DocsRail() {
  const [active, setActive] = useState(SECTIONS[0]?.id ?? '')

  useEffect(() => {
    const crossed = new Set<string>()
    const order = SECTIONS.map((s) => s.id)
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const id = e.target.id
          // "Crossed" = the section heading has scrolled past the upper
          // third of the viewport (rootMargin shifts the trigger line).
          if (e.isIntersecting || e.boundingClientRect.top < 0) crossed.add(id)
          else crossed.delete(id)
        }
        setActive(activeSection(order, crossed))
      },
      { rootMargin: '-20% 0px -65% 0px' },
    )
    for (const s of SECTIONS) {
      const el = document.getElementById(s.id)
      if (el) observer.observe(el)
    }
    return () => observer.disconnect()
  }, [])

  return (
    <nav className="docs-rail" aria-label="Sections">
      {SECTIONS.map((s) => (
        <a key={s.id} href={`#${s.id}`} className={active === s.id ? 'active' : ''}>
          <span className="docs-rail-no">{s.no}</span> {s.title}
        </a>
      ))}
    </nav>
  )
}
