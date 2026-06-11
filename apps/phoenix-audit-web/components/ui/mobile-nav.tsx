'use client'

// Story-9.19 Surface M — hamburger + right-sheet drawer for ≤768px.
// Visibility is CSS-only (.nav-mobile/.nav-desktop media classes) so SSR
// markup is stable; no JS width sniffing. Motion is CSS transitions —
// framer-motion isn't in the workspace and a one-component dep isn't
// worth the bundle weight.
//
// A11y (PR #115 review): this is a real aria-modal dialog, so it ships the
// full contract — initial focus to the first link, focus restored to the
// burger on close, Tab/Shift+Tab cycled inside, body scroll locked while
// open, and `inert` on the closed drawer + backdrop.

import { useEffect, useReducer, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { UserMenu } from '@/components/auth/user-menu'
import { NAV_ITEMS, drawerReducer, isNavActive } from '@/lib/mobile-nav'
import { A } from './link'

const DRAWER_ID = 'phoenix-audit-mobile-drawer'

export function MobileNav() {
  const [open, dispatch] = useReducer(drawerReducer, false)
  const pathname = usePathname() ?? ''
  const burgerRef = useRef<HTMLButtonElement>(null)
  const drawerRef = useRef<HTMLElement>(null)

  // Route change = a nav happened — the drawer must never outlive it.
  useEffect(() => {
    dispatch({ type: 'navigate' })
  }, [pathname])

  useEffect(() => {
    if (!open) return
    // Initial focus: first nav link. Restore to the burger on close.
    const links = drawerRef.current?.querySelectorAll<HTMLElement>('a, button')
    links?.[0]?.focus()
    // Scroll lock while modal (iOS background-scroll included).
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        dispatch({ type: 'escape' })
        return
      }
      if (e.key !== 'Tab') return
      // Cycle focus inside the drawer (aria-modal contract).
      const focusables = drawerRef.current?.querySelectorAll<HTMLElement>('a, button')
      const first = focusables?.[0]
      const last = focusables?.[focusables.length - 1]
      if (!first || !last) return
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
      burgerRef.current?.focus()
    }
  }, [open])

  return (
    <div className="nav-mobile">
      <button
        ref={burgerRef}
        type="button"
        className="nav-burger mono"
        aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open}
        aria-controls={DRAWER_ID}
        onClick={() => dispatch({ type: 'toggle' })}
      >
        {open ? '✕' : '☰'}
      </button>
      <div
        className={`nav-drawer-backdrop ${open ? 'open' : ''}`}
        onClick={() => dispatch({ type: 'backdrop' })}
        aria-hidden="true"
        inert={!open}
      />
      <aside
        ref={drawerRef}
        id={DRAWER_ID}
        className={`nav-drawer ${open ? 'open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        inert={!open}
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
