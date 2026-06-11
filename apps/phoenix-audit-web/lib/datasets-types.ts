// Story-9.15 — pure wire types for the /datasets surface. NO imports of
// server modules: client components import from here; pulling next/headers
// or google-auth-library into the client bundle breaks the production build
// (the bug that held staging web back from PR #110 to #113).

export type DatasetKind = 'battery' | 'regression' | 'uploaded'

export interface DatasetListRowDto {
  dataset_id: string
  name: string
  kind: DatasetKind
  row_count: number
  source_url: string | null
  agent_id: string | null
  created_at: string
  updated_at: string
}

export interface DatasetItemDto {
  case_id: string
  fault_class: string
  prompt: string
  expected: string
  source: string
  severity: string | null
  notes: string | null
}

export interface DatasetDetailDto extends DatasetListRowDto {
  items: DatasetItemDto[]
}

/** 503 body when Phoenix is down: index header rides through so the
 *  detail page can render a banner instead of failing. */
export interface DatasetUnavailableDto extends DatasetListRowDto {
  reason: string
}

export interface UploadValidationErrorDto {
  /** Whole-file failure (malformed JSON, missing CSV column, ...). */
  parse_error: string | null
  /** Per-row failures (unknown fault_class, duplicate case_id, ...). */
  row_errors: { row: number; reason: string }[]
}

export type DatasetDetailResult =
  | { kind: 'ok'; data: DatasetDetailDto }
  | { kind: 'phoenix_outage'; header: DatasetUnavailableDto }
  | { kind: 'not_found' }
  | { kind: 'error'; message: string }

export type UploadResult =
  | { kind: 'ok'; row: DatasetListRowDto }
  | { kind: 'validation_error'; error: UploadValidationErrorDto }
  | { kind: 'error'; message: string }

export type DeleteResult =
  | { kind: 'ok' }
  | { kind: 'conflict'; detail: string }
  | { kind: 'not_found' }
  | { kind: 'error'; message: string }

export interface UploadRequest {
  name: string
  format: 'jsonl' | 'csv'
  /** base64-encoded raw bytes of the JSONL or CSV file. */
  bodyBase64: string
}
