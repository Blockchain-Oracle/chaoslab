// Story-9.15 slice 8 — upload-card pure helpers. Lifting these out of
// the component shape lets the file-format detection + row-count
// heuristic stay testable; an `.JSONL` regression or an empty-file
// divide-by-zero used to be a silent route into the wrong error branch.

import { describe, expect, it } from 'vitest'
import { approxRowCount, detectFormat } from '@/lib/dataset-upload'

describe('detectFormat', () => {
  it('detects the three accepted extensions', () => {
    expect(detectFormat('cases.jsonl')).toBe('jsonl')
    expect(detectFormat('cases.json')).toBe('jsonl')
    expect(detectFormat('cases.csv')).toBe('csv')
  })

  it('is case-insensitive (uppercase + mixed)', () => {
    expect(detectFormat('CASES.JSONL')).toBe('jsonl')
    expect(detectFormat('Cases.Json')).toBe('jsonl')
    expect(detectFormat('Cases.CSV')).toBe('csv')
  })

  it('returns null for unknown / missing extensions', () => {
    expect(detectFormat('cases.txt')).toBeNull()
    expect(detectFormat('cases')).toBeNull()
    expect(detectFormat('')).toBeNull()
  })
})

describe('approxRowCount', () => {
  it('counts non-blank lines', () => {
    expect(approxRowCount('a\nb\nc')).toBe(3)
    expect(approxRowCount('a\n\nb')).toBe(2)
  })

  it('never returns zero (would divide-by-zero in the scan animation)', () => {
    // Critical: the scan-progress bar computes width as scanned/total
    // — total=0 would NaN the inline style and break the affordance.
    expect(approxRowCount('')).toBe(1)
    expect(approxRowCount('\n\n\n')).toBe(1)
    expect(approxRowCount('   ')).toBe(1)
  })
})
