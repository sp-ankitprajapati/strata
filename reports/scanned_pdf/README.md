# Scanned PDF OCR integration checkpoint

## Preserved standalone run

- Input: image-only PDF generated from the project's synthetic Japanese-English schedule.
- OCR text boxes: 15.
- Recorded inference time: 21.792 seconds.
- Extracted item blocks: 3.
- Reference decision counts: {"asbestos_containing": 1, "non_asbestos_containing": 1, "unresolved": 1}.
- Engine and runtime details are preserved in `decisions_cpu.json` and the raw OCR evidence.

## App verification

The user verified the same example through Process PDF using the isolated OCR worker. The app reported 15 text boxes, 21.4 seconds of recorded inference time, three extracted entries and one unresolved result. The first displayed entry matched the asbestos-containing Nichiha reference. The app run and archived standalone run are separate executions.

## What the workflow preserves

PDF page -> raster image -> OCR detections -> reconstructed lines -> labelled fields -> reference matching -> human review.

Raw OCR text, box coordinates, confidence scores, PDF and image hashes, and model settings are retained. Item labels such as `S-OO1` remain as read by OCR. Label-spacing normalization supports compact field labels while preserving their original evidence.

An installation year is retained as context rather than used as a manufacturing month. Missing manufacturing evidence can therefore leave an item unresolved.

## Execution change

The initial in-process integration exited with a native abort; its cause remains unconfirmed. The succeeding worker configuration runs in a separate process, uses one CPU thread, disables dynamic quantization and limits image size. Worker failures and timeouts are reported through the app.

## Scope and remaining work

This is one clean synthetic development fixture matched against two real manufacturer-reference records. Broader document evaluation remains pending. The OCR path currently extracts labelled item blocks; scanned-table cell reconstruction is outside its implemented scope. Existing native PDF table extraction remains available separately.
