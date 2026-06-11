'use client'

import { usePathname } from 'next/navigation'
import { UserMenu } from '@/components/auth/user-menu'
import { NAV_ITEMS, isNavActive } from '@/lib/mobile-nav'
import { A } from './link'
import { MobileNav } from './mobile-nav'
import { Wordmark } from './wordmark'

export function TopBar() {
  const pathname = usePathname() ?? ''
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <A to="" style={{ textDecoration: 'none', color: 'inherit', display: 'flex' }}>
          <Wordmark size={16} glyph={18} />
        </A>
        <nav className="nav-desktop">
          {NAV_ITEMS.map(([slug, label]) => (
            <A key={slug} to={slug} className={isNavActive(pathname, slug) ? 'active' : ''}>
              {label}
            </A>
          ))}
        </nav>
        <span className="nav-desktop nav-desktop-contents">
          <UserMenu />
        </span>
        <A to="new" className="btn ember small">
          Run audit
        </A>
        <MobileNav />
      </div>
    </header>
  )
}
