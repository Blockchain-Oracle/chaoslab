'use client'

// Story-9.15 — /datasets listing client (Surface S). Three sections in the
// reading order from the designer brief (battery / regression / uploaded).
// Each section always renders; empty sections show their "where these
// come from" affordance. liveError surfaces as a banner so an outage
// never displays a silent empty page.

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import { groupDatasetsByKind, type DatasetSection } from '@/lib/datasets-grouping'
import type { DatasetKind, DatasetListRowDto } from '@/lib/datasets'
import { DatasetUploadCard } from './dataset-upload-card'

function KindChip({ kind }: { kind: DatasetKind }) {
  return (
    <span className="tag" style={{ fontSize: 9.5, letterSpacing: '0.04em' }}>
      {kind.toUpperCase()}
    </span>
  )
}

function DatasetRow({ row }: { row: DatasetListRowDto }) {
  return (
    <li
      className="clickable"
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 16,
        padding: '12px 0',
        borderBottom: '1px solid var(--hairline-soft)',
      }}
    >
      <KindChip kind={row.kind} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <A to={`datasets/${row.dataset_id}`} style={{ fontSize: 14 }}>
          {row.name}
        </A>
        <div className="mono muted" style={{ fontSize: 10.5 }}>
          {row.dataset_id}
          {row.source_url ? ` · ${row.source_url.replace('https://', '')}` : ''}
        </div>
      </div>
      <span className="mono muted" style={{ fontSize: 11 }}>
        {row.row_count} rows
      </span>
      <span className="mono muted" style={{ fontSize: 11, minWidth: 80, textAlign: 'right' }}>
        {fmtDate(row.updated_at)}
      </span>
    </li>
  )
}

function SectionPanel({ section }: { section: DatasetSection }) {
  return (
    <section style={{ marginBottom: 36 }}>
      <h2 className="serif" style={{ fontSize: 18, marginBottom: 6 }}>
        {section.label}
      </h2>
      {section.rows.length === 0 ? (
        <p className="muted" style={{ fontSize: 12.5, fontStyle: 'italic' }}>
          {section.emptyCaption}
        </p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {section.rows.map((row) => (
            <DatasetRow key={row.dataset_id} row={row} />
          ))}
        </ul>
      )}
    </section>
  )
}

export interface DatasetsListingClientProps {
  rows: DatasetListRowDto[]
  liveError: string | null
}

export function DatasetsListingClient({ rows, liveError }: DatasetsListingClientProps) {
  // Optimistic insert state — when the upload card returns a new row, we
  // prepend it so the user sees it appear without a page reload. The
  // authoritative store still reflects on next navigation.
  const [optimistic, setOptimistic] = useState<DatasetListRowDto[]>([])
  const all = [...optimistic, ...rows]
  const sections = groupDatasetsByKind(all)

  return (
    <>
      <TopBar />
      <div className="shell" style={{ padding: '40px 32px 60px', maxWidth: 900 }}>
        <div className="kicker" style={{ marginBottom: 12 }}>
          Datasets
        </div>
        <h1 className="display" style={{ fontSize: 32, marginBottom: 28 }}>
          Test-case corpora
        </h1>
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

        <DatasetUploadCard onUploaded={(row) => setOptimistic((prev) => [row, ...prev])} />

        {sections.map((section) => (
          <SectionPanel key={section.kind} section={section} />
        ))}
      </div>
      <PageFoot />
    </>
  )
}
