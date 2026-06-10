import Link from 'next/link'
import { PageFoot } from '@/components/ui/page-foot'
import { EmptyState } from '@/components/ui/empty-state'
import { TopBar } from '@/components/ui/topbar'

export default function NotFound() {
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '80px 40px 40px', maxWidth: 720 }}>
        <EmptyState
          kicker="404"
          title="Nothing filed under that address."
          body="The run, recipe, or page you asked for is not in the registry. It may have been swept, or the link may be mistyped."
          action={
            <Link href="/audits" className="btn ghost">
              Back to the audit registry
            </Link>
          }
        />
      </div>
      <PageFoot />
    </div>
  )
}
