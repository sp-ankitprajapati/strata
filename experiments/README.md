# Research experiments

This folder preserves the earlier drawing OCR, tiling, reference-table and
synthetic-scan experiments. Run them **from the repository root as modules**:

```bash
python -m experiments.create_tiles
python -m experiments.ocr_tiles
python -m experiments.ocr_tiles_easyocr --device cuda
python -m experiments.validate_reference_ocr --restore-notebook kaggle_gpu.ipynb
python -m experiments.validate_pipeline --help
```

These examples show the new command form; they have different prerequisites.
The drawing experiments depend on their original inputs under `data/raw/` and
`data/processed/`. Tesseract experiments need the system Tesseract command.
EasyOCR experiments need the full OCR environment and the appropriate cached or
downloaded models; CUDA runs also need a compatible GPU. Fonts and synthetic
ground truth are needed for regeneration. The smaller `requirements-demo.txt`
environment is for saved predictions, native PDFs and review, not every research
runner.

Use the [layout guide](../docs/repository_layout.md) for the complete command map
and the [reports](../reports/) for recorded inputs, settings, outputs and limits.

## Frozen scan-suite evidence

`reports/validation_suite/` retains the original 12-case inputs, OCR predictions,
source fingerprints and summary. The move changes Python source fingerprints;
`--run` must refuse to mix those archived predictions with different current code.
That protection is intentional. Do not edit archived fingerprints or claim a
replay as a new benchmark.

Read the frozen report to inspect the recorded result. For an exact historical
replay, use the recorded checkpoint (`6ff394c`) in a separate checkout with its
recorded environment and its original command. For a new experiment, preserve the
old evidence and prepare a separate suite version/checkout. The refactor does not
change the archived 10/12 decision agreements or 5.42% CER into new measurements.
