# Repository layout and command changes

The application modules remain at the repository root. The two app pages stay in
`app_pages/`. Tests and earlier research scripts have separate folders, while
data, bundled assets and frozen report evidence keep their original locations.

```text
strata/
  streamlit_app.py           # Application entry point
  check_demo.py              # Saved/native-PDF smoke check
  setup_models.py            # Optional live-OCR model setup
  ocr_worker.py              # Isolated live-OCR entry point
  ocr_layout.py              # Shared line reconstruction
  ...                       # Matching, extraction and review modules
  app_pages/                # Streamlit pages
  tests/                    # 12 test modules, 50 test methods
  experiments/              # Drawing, table and scan research
  scripts/                  # Author-side fixture/capture helpers
  assets/demo/              # Bundled real examples and provenance
  data/reference/           # Active manufacturer-reference catalogue
  reports/                  # Preserved experiment evidence
  docs/verification/        # Current software-check output
```

## Everyday commands are unchanged

Run from the repository root in the appropriate environment:

```bash
python -m streamlit run streamlit_app.py
python -m unittest discover -v
python check_demo.py
python setup_models.py
python run_matching.py --help
```

The `tests/__init__.py` file makes default discovery recurse into `tests/`,
including on Python 3.11. Test fixture paths resolve against the repository root,
not against the new test directory.

## Moved experiments

Use module invocation from the repository root. For example, the old
`python create_tiles.py` becomes `python -m experiments.create_tiles`.
Do not run an experiment by changing into `experiments/`: the application modules
and the data paths are defined relative to the project root.

| Area | Module commands / source files |
|---|---|
| Original drawing and inspection | `experiments.fetch_source`, `experiments.inspect_drawing`, `experiments.inspect_example`, `experiments.visualize_words` |
| Region OCR and evaluation | `experiments.experiment_regions`, `experiments.evaluate_regions`, `experiments.run_easyocr_regions` |
| Tiling and material comparison | `experiments.create_tiles`, `experiments.ocr_tiles`, `experiments.ocr_tiles_easyocr`, `experiments.deduplicate_words`, `experiments.extract_materials`, `experiments.build_material_context`, `experiments.compare_materials`, `experiments.evaluate_keyword_coverage`, `experiments.prepare_easyocr_materials` |
| Reference inspection and OCR | `experiments.inspect_reference`, `experiments.inspect_reference_pdf`, `experiments.inspect_reference_ocr_errors`, `experiments.benchmark_reference_ocr`, `experiments.benchmark_reference_ocr_2x`, `experiments.compare_solido_languages`, `experiments.validate_reference_ocr` |
| Synthetic schedule | `experiments.render_schedule`, `experiments.ocr_schedule`, `experiments.evaluate_schedule_ocr` |
| Scan stress suite | `experiments.validate_pipeline` |
| Kaggle checkpoint restoration | `experiments.restore_kaggle_results` |

These are research entry points, not a promise that every experiment can run from
the smaller demo installation. Some require Tesseract, EasyOCR/PyTorch, a GPU,
downloaded fonts or the original ignored drawing/processed data. See the
[experiment guide](../experiments/README.md).

## Author-side helpers

```bash
python -m scripts.create_scan_example
python -m scripts.save_scan_checkpoint
python -m scripts.package_demo
```

These regenerate or capture inputs/evidence and can write reports or environment
files. They are not required to run the bundled demo. Keep original evidence
before using them for a new capture.

## Kaggle notebooks

After updating the repository in Kaggle, replace old script-file invocations with
module invocations. For example:

```python
subprocess.run(
    [sys.executable, "-m", "experiments.ocr_tiles_easyocr", "--device", "cuda"],
    cwd=repo,
    check=True,
)
```

For reference-table validation, use
`[sys.executable, "-m", "experiments.validate_reference_ocr"]` with the same
repository working directory. Restore a saved notebook locally with:

```bash
python -m experiments.validate_reference_ocr --restore-notebook kaggle_gpu.ipynb
```

Historical JSON snapshots still contain the script names, hashes and commit IDs
that applied when their runs were made. Those provenance fields were not rewritten
to describe the new layout. Earlier learning notes may show old root-level
commands; use this mapping when following them with the current checkout.
