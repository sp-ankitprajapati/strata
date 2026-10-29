# Repository-layout verification

Verified on 29 October 2026 against the cleanup based on `7400274986a712591bb8ede7eb7e01f3338d23f1`.
The checked Python source hashes (UTF-8, LF line endings) are recorded in [environment.json](environment.json).

## Unit suite

Command: `python -m unittest discover -v` from the repository root.

```text
Ran 50 tests in 0.592s

OK
```

All 50 tests passed, with no skips. Full output: [unittest.txt](unittest.txt).
The tests cover matching, field/table parsing, review isolation, OCR geometry,
worker error handling, bundled-asset checks and evaluation logic. Controlled
readers and subprocess mocks do not measure live OCR accuracy.

## Application smoke check

`python check_demo.py` passed with the real bundled examples in a temporary
snapshot without ignored raw/processed data, saved reviews or model cache.
Both app pages loaded, the native PDF produced 39 selectable entries, and the
image-only scan had no selectable text. Live OCR was not run.

Full output: [demo_smoke.txt](demo_smoke.txt).

## Entry points and preserved behaviour

- `python -m experiments.validate_pipeline --help` passed after moving the runner.
- `python run_matching.py --help` passed without changing its everyday command.
- Root application modules do not import experiment runners.
- The extracted shared `reconstruct_lines` function has the same Python AST as
  the original implementation.
- Tracked assets, the catalogue and frozen report files were unchanged.
- The root now has 16 Python files; 12 test modules, 28 experiment runners and
  three author-side helpers are organised separately.

Outputs: [experiment_cli.txt](experiment_cli.txt), [matching_cli.txt](matching_cli.txt).

## Environment and limits

Python 3.12.14 on `win32`; Streamlit 1.66.1,
Pillow 12.3.0 and pdfplumber 0.11.9.
The local test environment was a venv with access to the bundled runtime packages,
not a clean installation of the full Linux CPU OCR lock. This check did not retrain
models, run GPU inference or replace the historical OCR measurements. The
Streamlit bare-mode warning in the smoke log is expected for AppTest.
