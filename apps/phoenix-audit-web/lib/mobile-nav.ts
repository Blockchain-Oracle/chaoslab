// Story-9.19 — the nav model + drawer logic shared by the inline topbar and
// the mobile drawer. Pure module (node-env vitest); the components are thin
// shells over this.

// Single source of truth for the product nav. topbar.tsx and mobile-nav.tsx
// BOTH render from this — a second copy would drift.
export const NAV_ITEMS: ReadonlyArray<[string, string]> = [
  ['audits', 'Audits'],
  ['agents', 'Target agents'],
  // story-9.15 follow-up: surface the dataset feature in the global nav. Sits
  // between Target agents and Monitoring so the natural read is "what I'm
  // auditing → what data I'm auditing it with → how it's going."
  ['datasets', 'Datasets'],
  ['monitoring', 'Monitoring'],
  ['settings', 'Settings'],
]

// Mirrored by the `@media (max-width: 768px)` rules in app/globals.css —
// the stylesheet pin in tests/mobile-nav.test.ts keeps them from drifting.
export const MOBILE_BREAKPOINT_PX = 768

export function isNavActive(pathname: string, slug: string): boolean {
  const route = pathname.replace(/^\//, '')
  return route === slug || route.startsWith(`${slug}/`)
}

export type DrawerAction = { type: 'toggle' | 'backdrop' | 'escape' | 'navigate' }

export function drawerReducer(open: boolean, action: DrawerAction): boolean {
  // backdrop/escape/navigate only ever CLOSE — a navigation that re-opened
  // the drawer would trap the user behind it on every route change.
  return action.type === 'toggle' ? !open : false
}
