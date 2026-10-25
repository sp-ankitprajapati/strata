# PDF extraction, matching and review

## Implemented workflow

Strata accepts a project example or an uploaded PDF and processes a selected page. It previews the page, extracts selectable text and line-based table candidates, and preserves the PDF hash, page number, source cells and coordinates.

Supported labelled item blocks and document-specific table layouts become material queries. These queries pass through the existing manufacturer-reference matcher. The page supports entry selection, evidence inspection and JSON export.

Reviewers can submit corrected product details with their name and an evidence note. Each submission reruns reference matching and is saved separately in the workspace SQLite review history. Saved reviews include the original record, submitted fields, document context, catalogue identifier, catalogue hash, timestamp and result. History is scoped to the PDF, page and entry. Practice submissions are explicitly labelled `synthetic_test`.

## Verified results

- The real KMEW example yielded 39 entries: 21 exterior-wall series, 16 roof names and 2 SOLIDO series.
- All 39 original entries remained unresolved against the active catalogue of two Nichiha records. Missing manufacturer and manufacturing-month facts were retained as missing.
- One conditional table rule was preserved for review.
- Fifteen targeted tests passed across PDF extraction, PDF review, history storage and reference matching.
- A manually verified synthetic form submission used `モエンサイディング-M`, `Nichiha` and `1995-08`. Its submitted reference result was `non_asbestos_containing`.
- The synthetic submission left the original 39 unresolved entries unchanged. Its history remained attached to the selected entry when switching entries.

The synthetic result validates the review workflow using supplied test details; it is not evidence about the material named in the original KMEW entry.

## Learning notes

Extraction and reference matching answer different questions. Extracting a name does not establish its manufacturer, manufacturing date or asbestos status. Sales dates and installation dates cannot substitute for a manufacturing month.

Human review creates a traceable new submission while retaining the original extraction and decision. A name-similarity suggestion remains a review aid rather than an automatic material decision.

## Current limits and next work

The Process PDF page currently uses native PDF extraction and supported layout rules. OCR for scanned uploads is the next integration step. Unknown table layouts remain available as source evidence and are reported as unsupported.

The active reference catalogue remains small. KMEW extraction candidates have not been approved as active matching records. Reviewer names are self-reported, and workspace SQLite storage is not an authenticated or tamper-proof audit service.

Further independent-document evaluation, reproducible setup, the consolidated project report, presentation and CV description remain to be completed. Existing OCR experiments use pretrained models; model fine-tuning has not been performed.
