import type { Metadata } from 'next'
import { Newsreader, Source_Serif_4, Instrument_Sans, IBM_Plex_Mono } from 'next/font/google'
import './globals.css'

const newsreader = Newsreader({
  subsets: ['latin'],
  variable: '--font-newsreader',
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
  display: 'swap',
})

const sourceSerif = Source_Serif_4({
  subsets: ['latin'],
  variable: '--font-source-serif',
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
  display: 'swap',
})

const instrumentSans = Instrument_Sans({
  subsets: ['latin'],
  variable: '--font-instrument-sans',
  weight: ['400', '500', '600'],
  display: 'swap',
})

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  variable: '--font-ibm-plex-mono',
  weight: ['400', '500', '600'],
  display: 'swap',
})

export const metadata: Metadata = {
  metadataBase: new URL('https://phoenix-audit.example'),
  title: 'Phoenix Audit — the AI agent that audits your other AI agents',
  description:
    'Three failures. One root cause. Patch in four seconds. Regulator-ready signed audit reports in ~90 seconds.',
  openGraph: {
    title: 'Phoenix Audit — the AI agent that audits your other AI agents',
    description:
      'Three failures. One root cause. Patch in four seconds. Regulator-ready signed audit reports in ~90 seconds.',
    type: 'website',
  },
  twitter: { card: 'summary_large_image' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const fontClass = [
    newsreader.variable,
    sourceSerif.variable,
    instrumentSans.variable,
    ibmPlexMono.variable,
  ].join(' ')
  return (
    <html lang="en" className={fontClass}>
      <body>{children}</body>
    </html>
  )
}
