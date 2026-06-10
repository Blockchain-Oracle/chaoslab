// Honest terminal state for a FINISHED run (story-9.10): the live stream is
// gone (in-process queues sweep after the run), so the registry record is
// the truth — phase, counts, artifacts. Never a fake "connection lost".

import type { RunDetailDto } from '@/lib/api'
import { fmtDate } from '@/lib/format'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'

export function FinishedRunSummary({ detail }: { detail: RunDetailDto }) {
  const run = detail.run
  const failed = run.phase === 'failed'
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px', maxWidth: 760 }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 14 }}>
          <A to="audits" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            AUDIT REGISTRY
          </A>{' '}
          / {run.run_id}
        </div>
        <h1 className="display" style={{ fontSize: 36, marginBottom: 8 }}>
          {failed ? 'This audit failed.' : 'This audit finished.'}
        </h1>
        <p className="muted" style={{ fontSize: 13.5, marginBottom: 28 }}>
          The live stream exists only while a run is in flight — this is the registry record of what
          happened.
        </p>
        <div className="card" style={{ padding: '20px 24px', marginBottom: 22 }}>
          <div className="leader-row" style={{ padding: '5px 0' }}>
            <span style={{ fontSize: 13 }}>Target</span>
            <span className="leader-fill"></span>
            <span className="mono" style={{ fontSize: 12 }}>
              {run.target_url}
            </span>
          </div>
          <div className="leader-row" style={{ padding: '5px 0' }}>
            <span style={{ fontSize: 13 }}>Outcome</span>
            <span className="leader-fill"></span>
            <span className="mono" style={{ fontSize: 12 }}>
              <span style={{ color: 'var(--pass)' }}>{run.passed}✓</span> /{' '}
              <span style={{ color: run.failed ? 'var(--fail)' : 'inherit' }}>{run.failed}✕</span>
              {run.errored ? ` · ${run.errored} errored` : ''}
              {run.transport_failed ? ` · ${run.transport_failed} unreachable` : ''}
            </span>
          </div>
          <div className="leader-row" style={{ padding: '5px 0' }}>
            <span style={{ fontSize: 13 }}>Started</span>
            <span className="leader-fill"></span>
            <span className="mono" style={{ fontSize: 12 }}>
              {fmtDate(run.created_at)}
            </span>
          </div>
          {run.finished_at ? (
            <div className="leader-row" style={{ padding: '5px 0' }}>
              <span style={{ fontSize: 13 }}>Finished</span>
              <span className="leader-fill"></span>
              <span className="mono" style={{ fontSize: 12 }}>
                {fmtDate(run.finished_at)}
              </span>
            </div>
          ) : null}
        </div>
        {failed && !run.report_available ? (
          <p className="mono muted" style={{ fontSize: 11.5, lineHeight: 1.7, marginBottom: 22 }}>
            ✕ Nothing was signed or filed for this run — completed probes are preserved in the
            Phoenix trace.
          </p>
        ) : null}
        <div style={{ display: 'flex', gap: 10 }}>
          {run.report_available ? (
            <A to={`report/${run.run_id}`} className="btn primary">
              Open the signed report
            </A>
          ) : null}
          <A to="new" className="btn ghost">
            Run a new audit
          </A>
        </div>
      </div>
      <PageFoot />
    </div>
  )
}
