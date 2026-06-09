'use client'

import { usePathname } from 'next/navigation'
import { A } from './link'
import { Wordmark } from './wordmark'

const NAV: ReadonlyArray<[string, string]> = [
  ['audits', 'Audits'],
  ['agents', 'Target agents'],
  ['monitoring', 'Monitoring'],
  ['settings', 'Settings'],
]

export function TopBar() {
  const pathname = usePathname() ?? ''
  // Strip the leading slash so 'audits' matches /audits and /audits/...
  const route = pathname.replace(/^\//, '')
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <A to="" style={{ textDecoration: 'none', color: 'inherit', display: 'flex' }}>
          <Wordmark size={16} glyph={18} />
        </A>
        <nav>
          {NAV.map(([slug, label]) => (
            <A key={slug} to={slug} className={route.startsWith(slug) ? 'active' : ''}>
              {label}
            </A>
          ))}
        </nav>
        <span
          className="mono muted"
          style={{ fontSize: 11, letterSpacing: '0.06em', whiteSpace: 'nowrap' }}
        >
          Meridian Mutual Health
        </span>
        <A to="new" className="btn ember small">
          Run audit
        </A>
      </div>
    </header>
  )
}
