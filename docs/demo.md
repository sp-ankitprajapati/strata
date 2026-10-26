# Five-minute Strata demo

Use the full CPU environment with cached models for the live-OCR part. Open forwarded port 8501 after starting `streamlit_app.py`.

## 1. Native document extraction

Open **Process PDF -> Project example**. Show the KMEW page preview, selectable Japanese text and three detected tables. The supported rules extract 39 names: 21 wall series, 16 roof names and two SOLIDO series.

Select a name and expand its evidence. Show its original table cells, source coordinates and PDF hash. All 39 queries remain unresolved because the active catalogue contains two Nichiha records and the extracted names do not supply the product facts needed for those records. The KMEW candidates have not been approved as active references.

## 2. Real drawing evidence

Open **Saved reviews -> Drawing OCR**. Select a material mention and show its box on the real drawing crop. Explain that generic names such as stucco or concrete provide incomplete product evidence. The saved source result remains available alongside the review controls.

## 3. Live scanned-page OCR

Return to **Process PDF -> Scanned schedule example**. Point out the synthetic-data label and the absence of selectable PDF text. Choose **OCR**, then **Run OCR**. Wait for the worker to finish.

The recorded development run produced 15 text boxes in about 21 seconds. Timing varies by machine and load. Show the raw OCR text, then select each of the three item blocks:

| Item | Supplied evidence | Expected reference result |
|---|---|---|
| Golden Moen | Nichiha, manufacture month 1978-06 | Asbestos-containing reference |
| Moen-M | Nichiha, manufacture month 1995-08 | Non-asbestos-containing reference |
| Moen-M | Nichiha, installation year 1995 | Unresolved: manufacture month missing |

Explain that OCR confidence describes text recognition. The reference decision depends on the supplied product facts and catalogue evidence.

## 4. A separate human-review submission

Select the third item. Keep the review type **Synthetic test**. For this demonstration, enter manufacturing month `1995-08`, a reviewer name and the note: `Synthetic demonstration: supplied a manufacturing month to exercise the review workflow.` Submit the review.

The submitted synthetic query should match the non-asbestos-containing reference. Show that the original item still lacks a manufacturing month and remains unresolved. Switch entries and return to show that the saved history belongs to the selected entry. Export the review history if needed.

This demonstrates a test submission; the added date is not evidence from the original scanned item.

## 5. Evaluation and engineering choices

Open `reports/validation_suite/README.md` and `error_analysis.md`. The 12 correlated synthetic stress cases yielded 10/12 status agreements, 5.42% CER and zero incorrect resolved decisions. Non-asbestos recall was 1/3. Explain the observed malformed dates and rotated suffix errors, and how unresolved results retain evidence for review.

The live integration uses a separate OCR process, a timeout, one CPU thread, bounded raster size and cached completed results. An earlier in-process integration aborted; its exact trigger was not established. The succeeding isolated configuration completed both standalone and app runs.

Close with the implemented scope and extensions: broader independent drawing evaluation, more reference records, scanned-table reconstruction and model fine-tuning. Existing report metrics describe their documented development examples.
