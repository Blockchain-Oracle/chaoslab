import { BuiltOn } from '@/components/landing/built-on'
import { CascadeStory } from '@/components/landing/cascade-story'
import { ClosingCta } from '@/components/landing/closing-cta'
import { Compare } from '@/components/landing/compare'
import { EnforcementStrip } from '@/components/landing/enforcement-strip'
import { Frameworks } from '@/components/landing/frameworks'
import { Hero } from '@/components/landing/hero'
import { LandingNav } from '@/components/landing/landing-nav'
import { Procedure } from '@/components/landing/procedure'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'

export default function HomePage() {
  return (
    <PageShell label="landing">
      <div className="page-enter">
        <EnforcementStrip />
        <LandingNav />
        <Hero />
        <CascadeStory />
        <Procedure />
        <Frameworks />
        <Compare />
        <BuiltOn />
        <ClosingCta />
        <PageFoot />
      </div>
    </PageShell>
  )
}
