// Story-9.15 slice 8 — pure helpers for the upload card.
//
// `detectFormat` and `approxRowCount` live in lib so a regression in
// either (e.g. case-sensitive JSONL routing, divide-by-zero in the
// scan-progress width math on empty files) is caught by the test
// suite rather than surfacing only on a real upload.

export type DatasetFormat = 'jsonl' | 'csv'

export function detectFormat(filename: string): DatasetFormat | null {
  const lower = filename.toLowerCase()
  if (lower.endsWith('.csv')) return 'csv'
  if (lower.endsWith('.json') || lower.endsWith('.jsonl')) return 'jsonl'
  return null
}

export function approxRowCount(text: string): number {
  return Math.max(1, text.split('\n').filter((l) => l.trim()).length)
}
