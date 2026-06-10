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
  if (!featured.data) {
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
  const eventsUrl = featured.data.artifact_urls['events.json']
  const events = eventsUrl ? await fetchEventsDocument(eventsUrl) : null
  if (!events?.doc) {
    // The sample run EXISTS — claiming "not seeded" here would be a false
    // statement. Disclose the load failure instead.
    return (
      <PageShell label="replay">
        <div className="shell" style={{ padding: '80px 40px' }}>
          <EmptyState
            kicker="REPLAY UNAVAILABLE"
            title="The sample replay couldn't load."
            body={`A seeded sample audit exists, but its recorded timeline could not be loaded right now${events?.error ? ` (${events.error})` : ' (signed timeline link unavailable)'}. Reload to retry.`}
            action={
              <A to="" className="btn small ghost">
                Back to the landing page
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
      <ReplayShell doc={events.doc} runLabel={`${run.run_id} · ${host} · sample replay`} />
    </PageShell>
  )
}
