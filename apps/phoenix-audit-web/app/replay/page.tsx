import { ReplayShell } from '@/components/chamber/replay-shell'
import { EmptyState } from '@/components/ui/empty-state'
import { A } from '@/components/ui/link'
import { PageShell } from '@/components/ui/page-shell'
import { fetchEventsDocument, fetchFeaturedRun } from '@/lib/api'

export const dynamic = 'force-dynamic'

// The public showcase: the newest seeded REAL audit, replayed from its
// persisted wire timeline (story-9.11). No fixtures.
export default async function ReplayPage() {
  const featured = await fetchFeaturedRun()
  const eventsUrl = featured.data?.artifact_urls['events.json']
  const doc = eventsUrl ? await fetchEventsDocument(eventsUrl) : null
  if (!featured.data || !doc) {
    return (
      <PageShell label="replay">
        <div className="shell" style={{ padding: '80px 40px' }}>
          <EmptyState
            kicker="NO SAMPLE AUDIT YET"
            title="The sample replay isn't seeded."
            body={
              featured.liveError
                ? `The registry could not be reached (${featured.liveError}).`
                : 'No seeded sample audit with a replay timeline exists yet — sign in and run a real audit to watch one live.'
            }
            action={
              <A to="new" className="btn small ember">
                Run a real audit
              </A>
            }
          />
        </div>
      </PageShell>
    )
  }
  const run = featured.data.run
  const host = run.target_url.replace(/^https?:\/\//, '')
  return (
    <PageShell label="replay">
      <ReplayShell doc={doc} runLabel={`${run.run_id} · ${host} · sample replay`} />
    </PageShell>
  )
}
