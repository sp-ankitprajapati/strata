# Real manufacturer PDF extraction

## Objective

Extract reviewable product-reference candidates from a real Japanese manufacturer document.

## Source and method

The source is KMEW’s manufacturer certificate:
https://www.kmew.co.jp/kenkai/syoumeisyo.php

The saved snapshot contains one page. Native PDF extraction produced 1,282 characters, 176 word boxes and three table candidates. OCR was not required for this extraction.

Document-specific rules interpreted the three table layouts.

## Results

| Group | Candidates |
|---|---:|
| Exterior-wall series | 21 |
| Roofing products or series | 16 |
| SOLIDO series | 2 |
| Total | 39 |

One merged roofing rule was preserved separately rather than treated as a product name.

## Traceability

Candidates retain their original cells, PDF fingerprint, source URL, page, table, row and column. Table boundaries and full page text are also preserved.

Thickness values remain in their original form. Parenthetical names have not been automatically split into aliases.

## Matching status

All 39 candidates remain pending review and are excluded from automatic matching.

The certificate wording and its conditions must accompany any approved reference records. Sales-period conditions must not be substituted for manufacturing dates.

The active matching catalogue remains unchanged.

## Validation and limits

All 18 automated tests passed across the project’s extraction, matching and review modules.

The table parser supports this document’s known layouts. These results do not establish accuracy on unseen tables, scans or building drawings.

## Main lesson

Recovering table cells is only the first step. Headers, merged cells, product groups and document conditions determine how those cells should be interpreted.