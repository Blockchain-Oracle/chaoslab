import { A } from '../ui/link'
import { MobileNav } from '../ui/mobile-nav'
import { Wordmark } from '../ui/wordmark'

const ANCHORS: ReadonlyArray<[string, string]> = [
  ['#how', 'How it works'],
  ['#frameworks', 'Frameworks'],
  ['#compare', 'Versus the Big 4'],
]

export function LandingNav() {
  return (
    <header style={{ borderBottom: '1px solid var(--hairline)' }}>
      <div
        className="shell landing-nav-row"
        style={{ height: 64, display: 'flex', alignItems: 'center', gap: 28 }}
      >
        <Wordmark size={17} glyph={20} />
        <nav
          className="nav-desktop"
          style={{
            display: 'flex',
            gap: 26,
            flex: 1,
            justifyContent: 'center',
          }}
        >
          {ANCHORS.map(([href, label]) => (
            <a
              key={href}
              href={href}
              className="mono"
              style={{
                fontSize: 11,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                textDecoration: 'none',
                color: 'var(--ink-2)',
                whiteSpace: 'nowrap',
              }}
            >
              {label}
            </a>
          ))}
        </nav>
        <A to="replay" className="btn small ghost nav-desktop">
          Watch a sample audit
        </A>
        <A to="new" className="btn small primary">
          Run audit
        </A>
        <MobileNav />
      </div>
    </header>
  )
}
