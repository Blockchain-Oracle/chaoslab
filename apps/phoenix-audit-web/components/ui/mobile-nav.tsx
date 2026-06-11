'use client'

// Story-9.19 Surface M — hamburger + right-sheet drawer for ≤768px.
// Visibility is CSS-only (.nav-mobile/.nav-desktop media classes) so SSR
// markup is stable; no JS width sniffing. Motion is CSS transitions —
// framer-motion isn't in the workspace yet and a one-component dep isn't
// worth the bundle weight.

import { useEffect, useReducer } from 'react'
import { usePathname } from 'next/navigation'
import { UserMenu } from '@/components/auth/user-menu'
import { NAV_ITEMS, drawerReducer, isNavActive } from '@/lib/mobile-nav'
import { A } from './link'

export function MobileNav() {
  const [open, dispatch] = useReducer(drawerReducer, false)
  const pathname = usePathname() ?? ''

  // Route change = a nav happened — the drawer must never outlive it.
  useEffect(() => {
    dispatch({ type: 'navigate' })
  }, [pathname])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dispatch({ type: 'escape' })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <div className="nav-mobile">
      <button
        type="button"
        className="nav-burger mono"
        aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open}
        onClick={() => dispatch({ type: 'toggle' })}
      >
        {open ? '✕' : '☰'}
      </button>
      <div
        className={`nav-drawer-backdrop ${open ? 'open' : ''}`}
        onClick={() => dispatch({ type: 'backdrop' })}
        aria-hidden={!open}
      />
      <aside
        className={`nav-drawer ${open ? 'open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-hidden={!open}
      >
        <nav className="nav-drawer-links">
          {NAV_ITEMS.map(([slug, label]) => (
            <A
              key={slug}
              to={slug}
              className={isNavActive(pathname, slug) ? 'active' : ''}
              onClick={() => dispatch({ type: 'navigate' })}
            >
              {label}
            </A>
          ))}
        </nav>
        <div className="nav-drawer-foot">
          <UserMenu />
        </div>
      </aside>
    </div>
  )
}
