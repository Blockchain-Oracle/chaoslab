'use client'

// Story-9.15 Surface S — dataset detail page. Ported from the designer
// prototype (Phoenix Audit(4)/js/dataset-detail.jsx) to TSX with our
// real wire types. The page has three result branches from the
// fetchDatasetDetail discriminated union:
//
//   - ok            → header + per-kind banner + paginated evidence table
//   - phoenix_outage → header from the index + banner ("rows live in
//                      Phoenix; refresh once it's back"). No table.
//   - error         → minimal recovery surface.
//
// Provenance banner (S-8): for regression sets, the designer renders a
// rich auto-populated treatment listing contributing audit runs +
// per-run row counts. Our wire DTO doesn't carry that yet (would need
// a backend extension to emit `audit_count` and `contributing[]`), so
// we render a degraded provenance treatment that still teaches the
// operator what regression sets ARE.

import { useMemo, useState, type ReactNode } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import type {
  DatasetDetailDto,
  DatasetDetailResult,
  DatasetItemDto,
  DatasetKind,
  DatasetUnavailableDto,
} from '@/lib/datasets'
import { DeleteDatasetModal } from './delete-dataset-modal'
import { DsCaseRow } from './dataset-case-row'

const PAGE_SIZE = 50

const KIND_GLYPH: Record<DatasetKind, string> = {
  battery: '▣',
  regression: '↻',
  uploaded: '▲',
}

function KindChip({ kind }: { kind: DatasetKind }) {
  return (
    <span className={`kind-chip ${kind}`}>
      <span className="k-glyph">{KIND_GLYPH[kind]}</span>
      {kind}
    </span>
  )
}

function ProvenanceBanner({ data }: { data: DatasetDetailDto }) {
  // Designer's S-8 banner — degraded for slice 8: contributing audit
  // runs aren't in the wire DTO yet (backend follow-up). We still teach
  // the operator what auto-population means.
  return (
    <div className="ds-provenance" style={{ marginBottom: 36 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.18em',
            color: 'var(--ember-deep)',
            whiteSpace: 'nowrap',
          }}
        >
          ↻ AUTO-POPULATED
        </span>
        <span style={{ fontSize: 13.5, lineHeight: 1.6, flex: 1, minWidth: 260 }}>
          Built from finished audits of{' '}
          {data.agent_id ? <strong>{data.agent_id}</strong> : <span>a target agent</span>}. Every
          failing probe upserts here — one row per probe, capped at the most-recent 200. You
          can&rsquo;t edit these rows; they are evidence your audits produced.
        </span>
      </div>
    </div>
  )
}

function CtaCluster({ data, onDelete }: { data: DatasetDetailDto; onDelete: () => void }) {
  const slug = data.dataset_id
  const newAuditHref =
    data.kind === 'regression' && data.agent_id
      ? `new?dataset=${encodeURIComponent(slug)}&agent=${encodeURIComponent(data.agent_id)}`
      : `new?dataset=${encodeURIComponent(slug)}`
  return (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
      <A to={newAuditHref} className="btn ember">
        {data.kind === 'regression' ? 'Re-audit with this set' : 'Use in new audit'}
      </A>
      {data.kind === 'uploaded' ? (
        <button className="btn ghost danger" onClick={onDelete}>
          Delete
        </button>
      ) : null}
    </div>
  )
}

function DetailHeader({
  data,
  cta,
}: {
  data: DatasetDetailDto | DatasetUnavailableDto
  cta?: ReactNode
}) {
  return (
    <>
      <div className="mono muted" style={{ fontSize: 11, marginBottom: 16 }}>
        <A to="datasets" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
          DATASETS
        </A>{' '}
        / {data.dataset_id}
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 18,
          marginBottom: 12,
          flexWrap: 'wrap',
        }}
      >
        <h1
          className="display"
          style={{ fontSize: 36, flex: 1, minWidth: 280, overflowWrap: 'anywhere' }}
        >
          {data.name}
        </h1>
        {cta}
      </div>
      <div
        style={{
          display: 'flex',
          gap: 12,
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: data.kind === 'regression' ? 22 : 34,
        }}
      >
        <KindChip kind={data.kind} />
        <span className="mono muted" style={{ fontSize: 11.5 }}>
          {data.row_count} rows
          {data.kind === 'regression' ? ' of 200 cap' : ''}
        </span>
        <span className="mono muted" style={{ fontSize: 11.5 }}>
          · updated {fmtDate(data.updated_at)}
        </span>
        {data.source_url ? (
          <a
            className="span-link"
            href={data.source_url}
            target="_blank"
            rel="noreferrer"
            title="Open the upstream source corpus"
          >
            View source ↗
          </a>
        ) : null}
      </div>
    </>
  )
}

function BatteryReadOnlyBanner({ rowCount }: { rowCount: number }) {
  return (
    <div
      className="mono muted"
      style={{
        fontSize: 10.5,
        letterSpacing: '0.06em',
        marginBottom: 26,
        display: 'flex',
        gap: 8,
        alignItems: 'baseline',
      }}
    >
      <span style={{ color: 'var(--ember-deep)' }}>▣</span>
      READ-ONLY — SHIPS WITH THE PRODUCT. EVERY OPERATOR RUNS THESE EXACT {rowCount} ROWS.
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

function CaseTable({
  items,
  hasNotes,
  page,
  pages,
  onPrev,
  onNext,
}: {
  items: DatasetItemDto[]
  hasNotes: boolean
  page: number
  pages: number
  onPrev: () => void
  onNext: () => void
}) {
  return (
    <>
      <div className="ledger-wrap">
        <table className="ledger">
          <thead>
            <tr>
              <th>case_id</th>
              <th>fault_class</th>
              <th>Prompt</th>
              <th>Expected</th>
              <th>Source</th>
              <th>Severity</th>
              {hasNotes ? <th>Notes</th> : null}
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <DsCaseRow key={row.case_id} row={row} hasNotes={hasNotes} />
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 18 }}>
          <button className="btn small ghost" disabled={page === 0} onClick={onPrev}>
            ← Prev {PAGE_SIZE}
          </button>
          <span className="mono muted" style={{ fontSize: 11 }}>
            page {page + 1} / {pages}
          </span>
          <button className="btn small ghost" disabled={page >= pages - 1} onClick={onNext}>
            Next {PAGE_SIZE} →
          </button>
          <span
            className="mono muted"
            style={{ fontSize: 10, marginLeft: 'auto', letterSpacing: '0.06em' }}
          >
            CLIENT-SIDE — ALL {items.length} ROWS ARE IN THIS PAGE&rsquo;S PAYLOAD
          </span>
        </div>
      ) : null}
    </>
  )
}

export interface DatasetDetailClientProps {
  result: Exclude<DatasetDetailResult, { kind: 'not_found' }>
}

export function DatasetDetailClient({ result }: DatasetDetailClientProps) {
  const [page, setPage] = useState(0)
  const [deleting, setDeleting] = useState(false)

  const data = result.kind === 'ok' ? result.data : null
  const pages = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.items.length / PAGE_SIZE)) : 1),
    [data],
  )
  const hasNotes = useMemo(() => Boolean(data && data.items.some((i) => i.notes)), [data])
  const slice = useMemo(
    () => (data ? data.items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE) : []),
    [data, page],
  )

  if (result.kind === 'error') {
    return (
      <>
        <TopBar />
        <div className="shell" style={{ padding: '50px 40px 30px', maxWidth: 720 }}>
          <div className="mono muted" style={{ fontSize: 11, marginBottom: 16 }}>
            <A to="datasets" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
              DATASETS
            </A>
          </div>
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
        <div className="shell" style={{ padding: '50px 40px 30px' }}>
          <DetailHeader data={result.header} />
          <OutageBanner reason={result.header.reason} />
        </div>
        <PageFoot />
      </>
    )
  }

  if (!data) {
    // Discriminated union has exactly ok/phoenix_outage/error today.
    // If a future result kind lands and a branch is missed, throwing
    // surfaces it loudly instead of rendering a blank page.
    throw new Error('unreachable: unhandled DatasetDetailResult kind')
  }

  return (
    <>
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px' }}>
        <DetailHeader
          data={data}
          cta={<CtaCluster data={data} onDelete={() => setDeleting(true)} />}
        />

        {data.kind === 'regression' ? <ProvenanceBanner data={data} /> : null}
        {data.kind === 'battery' ? <BatteryReadOnlyBanner rowCount={data.row_count} /> : null}

        <SectionHead
          no="§1"
          title="Test cases"
          right={
            <span className="mono muted" style={{ fontSize: 10.5 }}>
              rows {page * PAGE_SIZE + 1}–{Math.min(data.items.length, (page + 1) * PAGE_SIZE)} of{' '}
              {data.items.length} · click a row for the full prompt
            </span>
          }
        />
        <CaseTable
          items={slice}
          hasNotes={hasNotes}
          page={page}
          pages={pages}
          onPrev={() => {
            setPage((p) => Math.max(0, p - 1))
            window.scrollTo({ top: 0 })
          }}
          onNext={() => {
            setPage((p) => Math.min(pages - 1, p + 1))
            window.scrollTo({ top: 0 })
          }}
        />
      </div>
      {deleting ? (
        <DeleteDatasetModal
          row={data}
          onCancel={() => setDeleting(false)}
          onDeleted={() => {
            setDeleting(false)
            window.location.href = '/datasets'
          }}
        />
      ) : null}
      <PageFoot />
    </>
  )
}
