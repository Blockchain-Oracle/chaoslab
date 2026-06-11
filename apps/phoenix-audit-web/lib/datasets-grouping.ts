// Story-9.15 — pure helper that groups datasets by kind for the
// /datasets listing page. Three sections in the brief's reading order
// (battery, regression, uploaded); every section is always present so
// the empty-state affordance always has a place to render.

import type { DatasetKind, DatasetListRowDto } from './datasets'

export interface DatasetSection {
  kind: DatasetKind
  /** Human label shown as the section heading. */
  label: string
  rows: DatasetListRowDto[]
  /** Brief-specified empty-state caption — used when `rows` is empty. */
  emptyCaption: string
}

const SECTION_LABEL: Record<DatasetKind, string> = {
  battery: 'Battery datasets',
  regression: 'Regression sets',
  uploaded: 'Uploaded',
}

const SECTION_EMPTY_CAPTION: Record<DatasetKind, string> = {
  battery: 'Battery datasets are shipped with the product — every user sees these.',
  regression: 'Regression sets appear here after a finished audit produces failures.',
  uploaded: 'Upload a JSONL or CSV of your own test cases to audit your agents against.',
}

const READING_ORDER: DatasetKind[] = ['battery', 'regression', 'uploaded']

/** Group + label rows by kind. Every section is always present, so an
 *  empty section can still render its "where these come from" affordance. */
export function groupDatasetsByKind(rows: DatasetListRowDto[]): DatasetSection[] {
  return READING_ORDER.map((kind) => ({
    kind,
    label: SECTION_LABEL[kind],
    rows: rows.filter((r) => r.kind === kind),
    emptyCaption: SECTION_EMPTY_CAPTION[kind],
  }))
}
