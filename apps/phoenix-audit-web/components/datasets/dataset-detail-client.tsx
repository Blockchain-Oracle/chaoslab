'use client'

// Story-9.15 Surface S — dataset detail page. Handles every result branch
// from fetchDatasetDetail: ok (rows table), phoenix_outage (header + banner,
// brief BDD), error (full disclosure). Pagination is client-side over the
// already-loaded payload (no infinite scroll — the server caps regression
// sets at 200 + uploaded at 500).

import { useMemo, useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import type {
  DatasetDetailDto,
  DatasetDetailResult,
  DatasetItemDto,
  DatasetKind,
  DatasetUnavailableDto,
} from '@/lib/datasets'

const PAGE_SIZE = 50

function KindChip({ kind }: { kind: DatasetKind }) {
  return (
    <span className="tag" style={{ fontSize: 10, letterSpacing: '0.06em' }}>
      {kind.toUpperCase()}
    </span>
  )
}

function DetailHeader({ data }: { data: DatasetDetailDto | DatasetUnavailableDto }) {
  return (
    <header style={{ marginBottom: 28 }}>
      <div className="kicker" style={{ marginBottom: 10 }}>
        Dataset
      </div>
      <h1 className="display" style={{ fontSize: 30, marginBottom: 8 }}>
        {data.name}
      </h1>
      <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap' }}>
        <KindChip kind={data.kind} />
        <span className="mono muted" style={{ fontSize: 11 }}>
          {data.dataset_id}
        </span>
        <span className="mono muted" style={{ fontSize: 11 }}>
          · {data.row_count} rows
        </span>
        <span className="mono muted" style={{ fontSize: 11 }}>
          · updated {fmtDate(data.updated_at)}
        </span>
        {data.source_url ? (
          <a
            className="span-link"
            href={data.source_url}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 11.5 }}
          >
            source ↗
          </a>
        ) : null}
      </div>
    </header>
  )
}

function CTACluster({
  slug,
  kind,
  agentId,
}: {
  slug: string
  kind: DatasetKind
  agentId: string | null
}) {
  const newAuditHref =
    kind === 'regression' && agentId
      ? `/new?dataset=${encodeURIComponent(slug)}&agent=${encodeURIComponent(agentId)}`
      : `/new?dataset=${encodeURIComponent(slug)}`
  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
      <A to={newAuditHref.slice(1)} className="btn primary small">
        {kind === 'regression' ? 'Re-audit with this set' : 'Use in new audit'}
      </A>
    </div>
  )
}

function ItemsTable({ items }: { items: DatasetItemDto[] }) {
  const [page, setPage] = useState(0)
  const pages = useMemo(() => Math.max(1, Math.ceil(items.length / PAGE_SIZE)), [items.length])
  const slice = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  return (
    <div>
      <table className="reg-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left' }}>
            <th className="mono" style={{ fontSize: 10.5, padding: '8px 0' }}>
              CASE
            </th>
            <th className="mono" style={{ fontSize: 10.5, padding: '8px 0' }}>
              FAULT
            </th>
            <th className="mono" style={{ fontSize: 10.5, padding: '8px 0' }}>
              PROMPT
            </th>
            <th className="mono" style={{ fontSize: 10.5, padding: '8px 0' }}>
              EXPECTED
            </th>
            <th className="mono" style={{ fontSize: 10.5, padding: '8px 0' }}>
              SOURCE
            </th>
          </tr>
        </thead>
        <tbody>
          {slice.map((item) => (
            <tr key={item.case_id} style={{ borderTop: '1px solid var(--hairline-soft)' }}>
              <td className="mono" style={{ fontSize: 11.5, padding: '8px 12px 8px 0' }}>
                {item.case_id}
              </td>
              <td>
                <span className="tag" style={{ fontSize: 10 }}>
                  {item.fault_class}
                </span>
              </td>
              <td style={{ fontSize: 12.5, padding: '8px 12px 8px 0', maxWidth: 420 }}>
                {item.prompt.length > 140 ? `${item.prompt.slice(0, 140)}…` : item.prompt}
              </td>
              <td className="muted" style={{ fontSize: 11.5, padding: '8px 12px 8px 0' }}>
                {item.expected}
              </td>
              <td className="mono muted" style={{ fontSize: 11, padding: '8px 0' }}>
                {item.source}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {pages > 1 ? (
        <div
          className="mono"
          style={{ marginTop: 16, fontSize: 11, display: 'flex', gap: 10, alignItems: 'center' }}
        >
          <button
            className="btn small ghost"
            onClick={() => setPage((p) => Math.max(p - 1, 0))}
            disabled={page === 0}
          >
            Prev
          </button>
          <span>
            Page {page + 1} of {pages}
          </span>
          <button
            className="btn small ghost"
            onClick={() => setPage((p) => Math.min(p + 1, pages - 1))}
            disabled={page === pages - 1}
          >
            Next
          </button>
        </div>
      ) : null}
    </div>
  )
}

function OutageBanner({ reason }: { reason: string }) {
  return (
    <div className="auth-notice warn" role="status" style={{ marginBottom: 24, fontSize: 13 }}>
      <strong>{reason}</strong>
      <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
        Dataset rows live in Phoenix; the registry is reachable but Phoenix is not. The header above
        renders from our local index. Refresh in a moment to load the rows.
      </div>
    </div>
  )
}

export interface DatasetDetailClientProps {
  slug: string
  result: Exclude<DatasetDetailResult, { kind: 'not_found' }>
}

export function DatasetDetailClient({ slug, result }: DatasetDetailClientProps) {
  if (result.kind === 'error') {
    return (
      <>
        <TopBar />
        <div className="shell" style={{ padding: '40px 32px 60px', maxWidth: 720 }}>
          <h1 className="serif" style={{ fontSize: 22, marginBottom: 12 }}>
            Couldn&rsquo;t load the dataset
          </h1>
          <p className="muted" style={{ fontSize: 13 }}>
            {result.message}
          </p>
          <A to="datasets" className="btn small ghost" style={{ marginTop: 18 }}>
            ← Back to all datasets
          </A>
        </div>
        <PageFoot />
      </>
    )
  }

  if (result.kind === 'phoenix_outage') {
    return (
      <>
        <TopBar />
        <div className="shell" style={{ padding: '40px 32px 60px', maxWidth: 900 }}>
          <DetailHeader data={result.header} />
          <OutageBanner reason={result.header.reason} />
        </div>
        <PageFoot />
      </>
    )
  }

  const data = result.data
  return (
    <>
      <TopBar />
      <div className="shell" style={{ padding: '40px 32px 60px', maxWidth: 900 }}>
        <DetailHeader data={data} />
        <CTACluster slug={slug} kind={data.kind} agentId={data.agent_id} />
        <ItemsTable items={data.items} />
      </div>
      <PageFoot />
    </>
  )
}
