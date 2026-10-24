# Strata — Initial OCR Baseline

## Purpose

Compare OCR pipelines on one historical architectural drawing and establish a reproducible development baseline.

## Experiments

The drawing crop was processed using Tesseract PSM 11, overlapping tiled Tesseract, and overlapping tiled EasyOCR. EasyOCR inference also ran successfully on a Kaggle Tesla T4 GPU.

Duplicate material candidates were merged using matching material identity and cross-tile box overlap.

## Results

### Recognition on three manually selected crops

| Engine | Character error rate | Word error rate |
|---|---:|---:|
| Tesseract | 2.6% | 14.3% |
| EasyOCR, CPU | 15.8% | 42.9% |

Scoring ignored case and punctuation, collapsed whitespace, and included spaces in character counts.

### Material keyword coverage at eight selected locations

| Pipeline | Recovered targets | Coverage |
|---|---:|---:|
| Tesseract baseline | 3/8 | 37.5% |
| Tesseract tiled | 3/8 | 37.5% |
| EasyOCR tiled, GPU | 2/8 | 25.0% |

EasyOCR produced 130 text detections, eight material-bearing boxes, and five retained material mentions after merging repeats.

## Findings

Tiling did not improve coverage on the selected targets. EasyOCR recovered some useful labels elsewhere in the drawing but performed worse on the selected benchmark.

GPU execution was verified. No model training or fine-tuning was performed.

## Limitations

This is a development experiment on one drawing, not an independent test set. Keyword coverage does not measure complete transcription accuracy, full-drawing material recall, or asbestos classification. EasyOCR boxes may span multiple words.

## Next phase

Develop structured material records and traceable reference matching. Expand annotated data before further OCR tuning or fine-tuning.