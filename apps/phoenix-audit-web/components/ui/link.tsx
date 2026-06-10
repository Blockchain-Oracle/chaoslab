import NextLink from 'next/link'
import type { CSSProperties, MouseEvent, ReactNode } from 'react'

// Tiny adapter that lets us mirror the designer's <A to="…"> API while routing
// through Next.js's <Link>. `to` is a route slug (without the leading slash);
// the empty string means home.
interface AProps {
  to: string
  children: ReactNode
  className?: string
  style?: CSSProperties
  title?: string
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void
}

export function A({ to, children, className, style, title, onClick }: AProps) {
  const href = to === '' ? '/' : `/${to}`
  return (
    <NextLink href={href} className={className} style={style} title={title} onClick={onClick}>
      {children}
    </NextLink>
  )
}
