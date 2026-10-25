# Additional table and recognition-language experiments

## Purpose

Evaluate whether the enlargement setting transfers to additional table layouts, then investigate recognition failures in Latin series identifiers.

## GPU table comparison

Both input sizes were evaluated within the same Kaggle GPU environment.

| Table | Original input | 2× input |
|---|---|---|
| Roofing | 6/16 — 37.5% | 10/16 — 62.5% |
| SOLIDO | 0/2 — 0% | 0/2 — 0% |

Enlargement improved roofing recovery by 25 percentage points. SOLIDO required a different recognition configuration.

## SOLIDO language comparison

Two pretrained recognition configurations were evaluated on the same enlarged crop within the same CPU environment.

| Configuration | Exact names recovered | Inference time |
|---|---|---|
| Japanese–English | 0/2 | 9.1 seconds |
| English-only | 2/2 | 5.7 seconds |

Japanese–English OCR produced `tpeF` and `tpel` for the reference identifiers `typeF` and `typeM`. English-only recognition recovered both identifiers.

English-only recognition performed poorly on the Japanese headers. This supports investigating field-specific language selection rather than selecting one recognizer for every field.

## Evaluation and evidence

Recovery requires an exact match within an individual OCR box after Unicode NFKC normalization, whitespace removal and case folding. Punctuation is retained.

Original detections, confidence scores, source fingerprints, crop coordinates and runtime versions are preserved in the JSON reports.

High recognition confidence occurred on incorrect identifiers. Confidence therefore remains supplementary evidence rather than verification of product identity.

## Limits

These experiments use additional regions from the same digitally rendered PDF. References come from native extraction, and table coordinates assist region selection.

The English recognition configuration was investigated after observing SOLIDO failures. Its success on two identifiers is a development finding, not an independent benchmark.

Independent documents, degraded scans and automatic layout detection require further evaluation. No model fine-tuning was performed.