# Author-side helpers

Run these from the repository root with `python -m scripts.<name>`:

- `create_scan_example`: wraps the archived synthetic schedule image as an
  image-only PDF under ignored raw data.
- `save_scan_checkpoint`: captures a completed standalone OCR run and its
  reference decisions into the scanned-PDF report.
- `package_demo`: captures real demo assets, provenance and the working CPU
  environment. It expects the full author environment and original inputs.

These helpers are not part of ordinary demo startup. They can create or update
evidence and environment files. Preserve an existing capture before intentionally
creating another one; the tracked historical report evidence was left unchanged
during the repository-layout cleanup.
