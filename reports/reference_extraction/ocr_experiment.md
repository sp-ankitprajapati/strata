# Japanese table OCR: input-scale experiment

## Question

Does enlarging the table image improve recovery of small Japanese product-series names?

## Setup

The experiment used the exterior-wall table from the saved KMEW certificate. Native PDF coordinates selected the table region, and native extraction supplied 21 reference names for comparison.

Pretrained EasyOCR ran with Japanese and English enabled on CPU. The second experiment enlarged the same crop using 2× Lanczos interpolation.

The model, language settings and scoring rule remained unchanged.

## Results

| Input | Dimensions | Names recovered | Coverage | Inference time |
|---|---|---|---|---|
| Original | 1139 × 631 | 11/21 | 52.4% | 14.1 s |
| Enlarged | 2278 × 1262 | 21/21 | 100.0% | 38.5 s |

The enlarged input recovered all ten previously missed names and lost none.

## Evaluation rule

A reference name counted as recovered when an individual OCR detection matched it after Unicode NFKC normalization, whitespace removal and case folding. Punctuation was retained.

Duplicate detections did not increase the score. Longer names could not satisfy shorter names through substring matching.

## Interpretation and limits

Input scale materially affected recognition on this table. Higher recovery came with increased CPU inference time.

This is a development experiment on one table from a digitally rendered PDF. Reference names came from native extraction rather than independent human annotation. The result does not establish accuracy on unseen drawings, degraded scans or other layouts.

## Next validation

Keep the 2× setting fixed and evaluate the remaining table layouts. Run comparisons within the same GPU environment, recording software versions and preprocessing settings.