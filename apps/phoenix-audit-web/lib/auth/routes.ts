// Public/private route matrix. Unknown routes default to GATED — a new page
// added without touching this file is private, never accidentally open.

const PUBLIC_EXACT = new Set([
  '/',
  '/login',
  '/replay',
  '/docs',
  '/api/health',
  '/api/login',
  '/api/logout',
])

const PUBLIC_PREFIXES = ['/replay/', '/docs/']

export function isPublicPath(pathname: string): boolean {
  if (PUBLIC_EXACT.has(pathname)) return true
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

// Post-login destination from the ?redirect= param. Only same-origin
// relative paths survive — anything else (absolute URLs, scheme-relative
// `//host`, a loop back to /login) falls back to the registry.
export function safeRedirectTarget(raw: string | null): string {
  if (raw && raw.startsWith('/') && !raw.startsWith('//') && raw !== '/login') return raw
  return '/audits'
}
