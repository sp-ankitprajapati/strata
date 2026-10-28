# Synthetic scan suite: error analysis

## Evaluation scope

The suite contains four synthetic item scenarios, each rendered clean, with 1.5-degree rotation and with 0.8-pixel Gaussian blur. The 12 pages share four source scenarios and two manufacturer-reference records. They form a small development stress suite; performance on independent real drawings remains to be evaluated.

Each page has one expected item. OCR receives the PDF bytes and page number. Expected fields and decisions are used afterwards for scoring. No OCR values or reference records were changed during this evaluation.

## Recorded baseline

| Measure | Result |
|---|---:|
| Completed OCR runs | 12/12 |
| One item extracted per page | 12/12 |
| Item-ID agreement | 12/12 |
| Reference-status agreement | 10/12 (83.3%) |
| Reference-reason agreement | 8/12 (66.7%) |
| Product-name field agreement | 9/12 (75.0%) |
| Manufacturer field agreement | 12/12 (100.0%) |
| Manufacturing-month field agreement | 10/12 (83.3%) |
| Character error rate | 68/1,254 characters (5.42%) |
| Incorrect resolved decisions | 0/12 |

Field comparison uses NFKC normalization, casefolding and whitespace removal. CER preserves Japanese characters and punctuation and collapses whitespace. Raw OCR values remain available in the prediction evidence.

## Observed errors

| Case | OCR evidence | Effect |
|---|---|---|
| V-102_clean | `2001-09` became `20o1-09` | The manufacturing month failed format validation; the expected non-asbestos reference result remained unresolved. |
| V-102_skew_1_5 | `モエンサイディング-M` became `モエンサイディング-川` | Exact product matching failed; the expected non-asbestos reference result remained unresolved. |
| V-103_skew_1_5 | The same `M` to `川` suffix error occurred | Status remained unresolved, while the reason changed from missing manufacturing month to no exact product match. |
| V-104_clean | `2001-09` became `20o1-09` | Manufacturer mismatch was checked first and remained the reported reason. Field scoring separately exposed the date error. |
| V-104_skew_1_5 | The same `M` to `川` suffix error occurred | Status remained unresolved, while the reason changed from manufacturer mismatch to no exact product match. |

The suffix error occurred in all three rotated Moen-M examples. This is an observed pattern within the suite. Further experiments would be needed to distinguish the contributions of orientation and recognition-language configuration.

## Interpretation

Both status disagreements were additional unresolved outcomes for expected non-asbestos reference cases. That class had one true positive, zero false positives and two false negatives: precision 1/1 and recall 1/3. The asbestos-containing reference class had three true positives, zero false positives and zero false negatives.

Zero incorrect resolved decisions describes these 12 trials. It does not establish a general error rate for deployment. Status agreement also hides some upstream extraction errors, which is why field agreement and reason agreement are reported separately.

## Handling and follow-up

Preserve the frozen predictions and raw OCR strings. Route malformed dates and uncertain product suffixes to the existing human-review workflow, where a reviewer can submit verified details and an evidence note while retaining the original result.

Potential extensions include deskewing and field-specific English recognition for Latin suffixes, evaluated as separate experiments. No global `o` to `0` replacement or automatic `川` to `M` substitution was added to the matcher.

Further evaluation should broaden independent-document coverage and reference records. Scanned-table reconstruction and OCR fine-tuning remain unimplemented extensions.
