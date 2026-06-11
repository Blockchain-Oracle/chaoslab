// Story-9.15 — groupDatasetsByKind pure helper.
//
// The listing page renders three sections (battery / regression / uploaded)
// in that reading order per the Surface S brief. The grouping happens in a
// pure helper so the contract is testable without rendering React.

import { describe, expect, it } from 'vitest'
import { groupDatasetsByKind } from '@/lib/datasets-grouping'
import type { DatasetListRowDto } from '@/lib/datasets'

const battery: DatasetListRowDto = {
  dataset_id: 'harmbench-v1-sample',
  name: 'HarmBench v1 (sample)',
  kind: 'battery',
  row_count: 10,
  source_url: null,
  agent_id: null,
  created_at: '2026-06-11T07:00:00+00:00',
  updated_at: '2026-06-11T07:00:00+00:00',
}

const battery2: DatasetListRowDto = { ...battery, dataset_id: 'owasp-llm-top10', name: 'OWASP' }

const regression: DatasetListRowDto = {
  ...battery,
  dataset_id: 'regression-agt_a',
  name: 'Regression — agt_a',
  kind: 'regression',
  agent_id: 'agt_a',
}

const uploaded: DatasetListRowDto = {
  ...battery,
  dataset_id: 'ds_a1b2c3',
  name: 'My corpus',
  kind: 'uploaded',
}

describe('groupDatasetsByKind', () => {
  it('returns sections in reading order: battery, regression, uploaded', () => {
    const sections = groupDatasetsByKind([uploaded, regression, battery])
    expect(sections.map((s) => s.kind)).toEqual(['battery', 'regression', 'uploaded'])
  })

  it('preserves row order within each section', () => {
    const sections = groupDatasetsByKind([battery, battery2])
    const batterySection = sections.find((s) => s.kind === 'battery')
    expect(batterySection?.rows.map((r) => r.dataset_id)).toEqual([
      'harmbench-v1-sample',
      'owasp-llm-top10',
    ])
  })

  it('emits an empty rows array (NOT omitting the section) when a kind has no rows', () => {
    const sections = groupDatasetsByKind([battery])
    expect(sections).toHaveLength(3)
    expect(sections.find((s) => s.kind === 'regression')?.rows).toEqual([])
    expect(sections.find((s) => s.kind === 'uploaded')?.rows).toEqual([])
  })

  it('each section carries an empty-state caption per the brief', () => {
    const sections = groupDatasetsByKind([])
    const captions = Object.fromEntries(sections.map((s) => [s.kind, s.emptyCaption]))
    // Battery never empty (3 launch sets always seed), but the helper still
    // surfaces a sensible caption for symmetry.
    expect(captions.battery).toMatch(/seed|shipped|battery/i)
    // Regression caption tells the operator WHERE regression sets come from.
    expect(captions.regression).toMatch(/finished audit|regression set/i)
    // Uploaded caption invites the operator to upload.
    expect(captions.uploaded).toMatch(/upload/i)
  })
})
