'use client'

// Story-9.15 — /datasets listing (Surface S). Ported from the designer
// prototype (Phoenix Audit(4)/js/datasets.jsx, /shots/{01,02}-ds-listing.jpg)
// to TSX with our real wire types.
//
// Three sections in reading order: §S.1 Standing battery (read-only,
// ships with the product), §S.2 Regression sets (auto-populated from
// the operator's own audits), §S.3 Your uploads (operator's corpus).
// Every section always renders so the empty-state editorial copy has
// a home — that's how an empty regression section teaches the operator
// what regression sets ARE.
//
// liveError surfaces as a banner so an outage never displays a silent
// empty page.

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import { groupDatasetsByKind, type DatasetSection } from '@/lib/datasets-grouping'
import type { DatasetKind, DatasetListRowDto } from '@/lib/datasets-types'
import { DatasetUploadModal } from './dataset-upload-modal'
import { DeleteDatasetModal } from './delete-dataset-modal'

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

interface RowProps {
  row: DatasetListRowDto
  landed: boolean
  onDelete?: (row: DatasetListRowDto) => void
}

function DsRow({ row, landed, onDelete }: RowProps) {
  const detailHref = `datasets/${row.dataset_id}`
  const sublabel =
    row.kind === 'regression' && row.agent_id
      ? `tracks ${row.agent_id}`
      : row.kind === 'uploaded'
        ? `${row.dataset_id} · only you can see this`
        : row.dataset_id
  const newAuditHref =
    row.kind === 'regression' && row.agent_id
      ? `new?dataset=${encodeURIComponent(row.dataset_id)}&agent=${encodeURIComponent(row.agent_id)}`
      : `new?dataset=${encodeURIComponent(row.dataset_id)}`
  return (
    <tr className={landed ? 'clickable ds-landed' : 'clickable'}>
      <td data-label="Dataset" style={{ minWidth: 230 }}>
        <A to={detailHref} style={{ display: 'block', textDecoration: 'none' }}>
          <span className="serif" style={{ fontSize: 15.5, lineHeight: 1.25, color: 'var(--ink)' }}>
            {row.name}
          </span>
        </A>
        <div className="mono muted" style={{ fontSize: 10, marginTop: 4, lineHeight: 1.4 }}>
          {sublabel}
        </div>
      </td>
      <td data-label="Kind">
        <KindChip kind={row.kind} />
      </td>
      <td className="mono num" data-label="Rows" style={{ whiteSpace: 'nowrap' }}>
        {row.row_count}
        {row.kind === 'regression' ? (
          <span className="muted" style={{ fontSize: 10 }}>
            {' '}
            / 200
          </span>
        ) : null}
      </td>
      <td
        className="mono muted"
        data-label="Updated"
        style={{ fontSize: 11, whiteSpace: 'nowrap' }}
      >
        {fmtDate(row.updated_at)}
      </td>
      <td data-label="Actions" style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
        <A to={newAuditHref} className="span-link" style={{ marginRight: 12 }}>
          {row.kind === 'regression' ? 'Re-audit →' : 'Use in audit →'}
        </A>
        {row.kind === 'uploaded' && onDelete ? (
          <button
            onClick={() => onDelete(row)}
            title={`Delete ${row.name}`}
            aria-label={`Delete ${row.name}`}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--ink-3)',
              fontSize: 13,
              lineHeight: 1,
              padding: '0 2px',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        ) : null}
      </td>
    </tr>
  )
}

function DsEmptyRow({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        border: '1px dashed var(--hairline)',
        borderRadius: 'var(--r-lg)',
        padding: '16px 20px',
        display: 'flex',
        gap: 12,
        alignItems: 'baseline',
      }}
    >
      <span className="mono" style={{ fontSize: 10, color: 'var(--ember-deep)' }}>
        ◇
      </span>
      <span
        style={{
          fontSize: 13,
          color: 'var(--ink-2)',
          lineHeight: 1.6,
          flex: 1,
        }}
      >
        {children}
      </span>
    </div>
  )
}

const TABLE_HEAD = (
  <thead>
    <tr>
      <th>Dataset</th>
      <th>Kind</th>
      <th>Rows</th>
      <th>Updated</th>
      <th style={{ textAlign: 'right' }}>Actions</th>
    </tr>
  </thead>
)

function DsSection({
  no,
  title,
  note,
  rows,
  landedId,
  onDelete,
  emptyState,
  closer,
}: {
  no: string
  title: string
  note: string
  rows: DatasetListRowDto[]
  landedId: string | null
  onDelete?: (row: DatasetListRowDto) => void
  emptyState: React.ReactNode
  closer?: React.ReactNode
}) {
  return (
    <div style={{ marginBottom: 52 }}>
      <SectionHead
        no={no}
        title={title}
        right={
          <span className="mono muted" style={{ fontSize: 10.5 }}>
            {note}
          </span>
        }
      />
      {rows.length === 0 ? (
        emptyState
      ) : (
        <div className="ledger-wrap">
          <table className="ledger">
            {TABLE_HEAD}
            <tbody>
              {rows.map((row) => (
                <DsRow
                  key={row.dataset_id}
                  row={row}
                  landed={row.dataset_id === landedId}
                  onDelete={onDelete}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {closer}
    </div>
  )
}

export interface DatasetsListingClientProps {
  rows: DatasetListRowDto[]
  liveError: string | null
}

export function DatasetsListingClient({ rows, liveError }: DatasetsListingClientProps) {
  const [optimistic, setOptimistic] = useState<DatasetListRowDto[]>([])
  const [landedId, setLandedId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<DatasetListRowDto | null>(null)
  // story-9.15 follow-up: upload UX moved from inline-at-page-bottom (+
  // scroll-to-anchor) to a centered modal. The CTA opens the modal; the
  // modal closes itself on successful upload via onUploaded.
  const [uploadOpen, setUploadOpen] = useState(false)

  const all = [...optimistic, ...rows]
  const sections = groupDatasetsByKind(all)
  const battery = sections.find((s) => s.kind === 'battery') as DatasetSection
  const regression = sections.find((s) => s.kind === 'regression') as DatasetSection
  const uploaded = sections.find((s) => s.kind === 'uploaded') as DatasetSection

  const onUploaded = (row: DatasetListRowDto) => {
    setOptimistic((prev) => [row, ...prev])
    setLandedId(row.dataset_id)
    setUploadOpen(false)
    setTimeout(() => setLandedId(null), 3200)
  }

  // Escape + backdrop + ✕ close are all owned by DatasetUploadModal
  // itself so the busy-guard (refuse close while parsing) lives in one
  // place (PR #122 silent-failure HIGH).

  return (
    <>
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px' }}>
        <div
          className="page-hero-row"
          style={{ display: 'flex', alignItems: 'flex-end', gap: 20, marginBottom: 10 }}
        >
          <div style={{ flex: 1 }}>
            <div className="kicker" style={{ marginBottom: 12 }}>
              Test-case registry
            </div>
            <h1 className="display" style={{ fontSize: 38 }}>
              Datasets.
            </h1>
          </div>
          <button className="btn ghost" onClick={() => setUploadOpen(true)}>
            Upload a dataset
          </button>
        </div>
        <p className="muted" style={{ maxWidth: 620, marginBottom: 44 }}>
          Every dataset is a named, persistent battery of adversarial test cases — run it today, run
          it again after the fix, and the report shows the regulator the{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--ember-deep)' }}>same conditions twice</em>
          .
        </p>

        {liveError ? (
          <div
            className="auth-notice warn"
            role="status"
            style={{ marginBottom: 24, fontSize: 12.5 }}
          >
            Live registry unavailable: {liveError}. Battery sets always render; uploaded +
            regression rows may be stale.
          </div>
        ) : null}

        <DsSection
          no="§S.1"
          title="Standing battery"
          note="ships with Phoenix Audit · read-only · identical for every operator"
          rows={battery.rows}
          landedId={landedId}
          emptyState={
            <DsEmptyRow>
              No battery datasets have been seeded yet — run the seed script. Battery sets ship with
              Phoenix Audit and are identical for every operator.
            </DsEmptyRow>
          }
          closer={
            <p
              className="mono muted"
              style={{ fontSize: 10, letterSpacing: '0.06em', marginTop: 10 }}
            >
              CURATED FROM PUBLISHED CORPORA — EACH SET LINKS TO ITS SOURCE AND TO PHOENIX&rsquo;S
              OWN DATASET VIEW ↗
            </p>
          }
        />

        <DsSection
          no="§S.2"
          title="Regression sets"
          note="one per target agent · written by your audits, not by you"
          rows={regression.rows}
          landedId={landedId}
          emptyState={
            <DsEmptyRow>
              Regression sets appear after your first finished audit. Every failing probe files
              itself here — one set per agent, one row per failure, capped at the most-recent 200 —
              so tomorrow&rsquo;s audit can re-run <em>the same evidence</em>.{' '}
              <A to="new" className="span-link">
                Run your first audit →
              </A>
            </DsEmptyRow>
          }
        />

        <DsSection
          no="§S.3"
          title="Your uploads"
          note="scoped to you · JSONL or CSV · rename or delete anytime"
          rows={uploaded.rows}
          landedId={landedId}
          onDelete={setDeleting}
          emptyState={
            <DsEmptyRow>
              Your own corpus runs <em>alongside</em> the synthetic battery, not instead of it —
              prior incidents, internal red-team cases, your domain&rsquo;s must-refuse list.{' '}
              <button
                type="button"
                onClick={() => setUploadOpen(true)}
                className="span-link"
                style={{
                  background: 'none',
                  border: 'none',
                  padding: 0,
                  font: 'inherit',
                  cursor: 'pointer',
                }}
              >
                Upload your first one →
              </button>
            </DsEmptyRow>
          }
        />
      </div>
      {uploadOpen ? (
        <DatasetUploadModal onCancel={() => setUploadOpen(false)} onUploaded={onUploaded} />
      ) : null}
      {deleting ? (
        <DeleteDatasetModal
          row={deleting}
          onCancel={() => setDeleting(null)}
          onDeleted={(deletedId) => {
            setOptimistic((prev) => prev.filter((r) => r.dataset_id !== deletedId))
            setDeleting(null)
          }}
        />
      ) : null}
      <PageFoot />
    </>
  )
}
