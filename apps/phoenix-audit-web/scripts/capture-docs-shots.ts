// Capture real-app screenshots for /docs (and reusable for the Devpost
// gallery — assets.md item 4). Run against a LIVE deployment:
//
//   BASE_URL=https://phxaudit.xyz \
//   SHOT_EMAIL=... SHOT_PASSWORD=... \
//   pnpm exec tsx scripts/capture-docs-shots.ts
//
// Output: public/docs-shots/*.png (1280×800 viewport).

import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

const BASE = process.env.BASE_URL ?? 'http://localhost:3000'
const EMAIL = process.env.SHOT_EMAIL
const PASSWORD = process.env.SHOT_PASSWORD

const OUT = join(process.cwd(), 'public', 'docs-shots')

const SHOTS: Array<{ file: string; path: string; authed: boolean; settleMs?: number }> = [
  { file: 'login.png', path: '/login', authed: false },
  { file: 'chamber.png', path: '/replay', authed: false, settleMs: 9000 },
  { file: 'agents.png', path: '/agents', authed: true },
  { file: 'wizard.png', path: '/new', authed: true },
  { file: 'monitoring.png', path: '/monitoring', authed: true },
  { file: 'report.png', path: '/audits', authed: true },
]

async function main(): Promise<void> {
  mkdirSync(OUT, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })

  const needAuth = SHOTS.some((s) => s.authed)
  if (needAuth) {
    if (!EMAIL || !PASSWORD) {
      throw new Error('SHOT_EMAIL / SHOT_PASSWORD are required for authed captures (fail-closed)')
    }
    await page.goto(`${BASE}/login`)
    await page.fill("input[name='auth-email-signin']", EMAIL)
    await page.fill("input[name='auth-pw-signin']", PASSWORD)
    await page.click("button[type='submit']")
    await page.waitForURL(/\/(audits|new|agents)/, { timeout: 30_000 })
  }

  for (const shot of SHOTS) {
    await page.goto(`${BASE}${shot.path}`, { waitUntil: 'networkidle' })
    if (shot.settleMs) await page.waitForTimeout(shot.settleMs)
    await page.screenshot({ path: join(OUT, shot.file) })
    process.stdout.write(`captured ${shot.file}\n`)
  }

  await browser.close()
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
