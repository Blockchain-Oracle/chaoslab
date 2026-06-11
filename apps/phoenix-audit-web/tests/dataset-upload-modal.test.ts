// Source-level pins on the UploadDatasetModal (story-9.15 follow-up): the
// upload UX flipped from inline-at-page-bottom + scroll-to-anchor to a
// centered modal that opens on the "Upload a dataset" CTA. The component
// state machine + DOM render are exercised by the listing component's own
// tests; here we lock the structural invariants the reviewer asked for:
//   - the modal uses the SAME ds-modal-veil/ds-modal shell as the existing
//     delete confirmation (no second visual idiom for modals on /datasets)
//   - the existing DatasetUploadCard body is REUSED (no fork of the
//     scan-animation + validation-panel logic)
//   - the listing client opens the modal on the CTA, not on a scroll anchor

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const modalSrc = readFileSync(
  join(import.meta.dirname, '../components/datasets/dataset-upload-modal.tsx'),
  'utf-8',
)

const listingSrc = readFileSync(
  join(import.meta.dirname, '../components/datasets/datasets-listing-client.tsx'),
  'utf-8',
)

describe('DatasetUploadModal — modal shell + body reuse', () => {
  it('uses the shared ds-modal-veil / ds-modal shell (same as delete confirm)', () => {
    expect(modalSrc).toContain('ds-modal-veil')
    expect(modalSrc).toContain('ds-modal')
  })

  it('reuses the existing DatasetUploadCard body — no fork of the scan/validation logic', () => {
    expect(modalSrc).toMatch(
      /import\s+{[^}]*DatasetUploadCard[^}]*}\s+from\s+['"]\.\/dataset-upload-card['"]/,
    )
    expect(modalSrc).toContain('<DatasetUploadCard')
  })

  it('renders an explicit close affordance + ARIA dialog role', () => {
    expect(modalSrc).toMatch(/role=['"]dialog['"]/)
    expect(modalSrc).toMatch(/aria-label/)
  })
})

describe('DatasetsListingClient — opens the modal on the CTA, not via scroll', () => {
  it('mounts DatasetUploadModal at the page root (not the inline-at-bottom render)', () => {
    expect(listingSrc).toContain('DatasetUploadModal')
  })

  it('the "Upload a dataset" button opens the modal — no scroll-to-anchor', () => {
    // The earlier UX used scrollToUpload + a uploadRef ref. Both must be
    // gone — leaving the scroll handler in would silently route some
    // codepaths back to the inline render.
    expect(listingSrc).not.toContain('scrollToUpload')
    expect(listingSrc).not.toContain('uploadRef')
  })

  it('still renders DatasetUploadCard exactly once — through the modal', () => {
    // The inline render at the page bottom is replaced; the modal is the
    // sole mount point now. A duplicate render would mean the upload
    // state can split across two trees.
    const occurrences = (listingSrc.match(/<DatasetUploadCard/g) || []).length
    expect(occurrences).toBe(0)
  })
})
