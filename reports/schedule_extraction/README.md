# English–Japanese schedule extraction experiment

## Objective

Extract product names, manufacturers and manufacture months from a controlled synthetic schedule image, then match those fields against manufacturer references.

## Workflow

1. Created three synthetic material entries.
2. Rendered the entries into an image using a Japanese font.
3. Ran pretrained EasyOCR with Japanese and English enabled on CPU.
4. Reconstructed text lines using detection coordinates.
5. Extracted labelled fields and passed them to the existing matcher.

Ground truth was used for evaluation, not supplied to OCR or field extraction.

## Results

- OCR inference time: 22.5 seconds.
- Text detections: 13.
- Reconstructed lines: 13.
- Extracted items: 3.
- Character error rate including spaces: 6.4%.
- Character error rate ignoring spaces: 2.5%.

CER used Unicode NFKC normalization, case folding and collapsed whitespace, with punctuation retained.

## Extraction improvement

OCR read `Manufacture month` as `Manufacturemonth`. The original parser therefore missed both supplied manufacturing dates.

Removing whitespace and folding case in field labels recovered those dates.

| Item as read by OCR | Before label normalization | After label normalization |
|---|---|---|
| S-OO1 | Unresolved | Asbestos-containing reference match |
| S-OO2 | Unresolved | Non-asbestos-containing reference match |
| S-0O3 | Unresolved | Unresolved: manufacture month missing |

OCR CER remained unchanged because this improvement affected field interpretation, not recognition.

## Evidence and validation

Original OCR text, product values and item identifiers were preserved. Conflicting fields remained flagged, and installation dates were not substituted for manufacturing dates.

All 14 automated tests passed across extraction, matching, review suggestions and history storage.

## Limits and lessons

This experiment uses one clean synthetic image and a known labelled format. It does not establish accuracy on unseen drawings, general tables or degraded scans. No model fine-tuning was performed.

A small OCR error in a field label can prevent a valid reference match. Evaluating the complete pipeline reveals failures that character accuracy alone does not explain.