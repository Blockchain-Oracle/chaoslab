export const fmtDate = (iso: string): string => {
  const d = new Date(iso)
  // timeZone pinned to UTC: the label says UTC, so the value must BE UTC —
  // and server (UTC) vs browser (local) otherwise render different strings,
  // which was the React #418 hydration error on every dated surface
  // (story-9.10).
  return (
    d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    }) +
    ' · ' +
    d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) +
    ' UTC'
  )
}
