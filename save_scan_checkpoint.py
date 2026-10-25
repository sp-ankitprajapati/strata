"""Archive the successful standalone scan run and replay reference matching."""

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from pdf_candidates import build_pdf_candidates, match_pdf_candidate


ROOT = Path(__file__).resolve().parent


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    source = ROOT / "data/processed/synthetic_schedule/scan_ocr_diagnostic.json"
    pdf_path = ROOT / "data/raw/synthetic_schedule_scan.pdf"
    analysis_bytes = source.read_bytes()
    analysis = json.loads(analysis_bytes)
    if not analysis.get("ocr_used"):
        raise ValueError("Expected the completed OCR run.")
    if analysis["pdf_sha256"] != sha(pdf_path.read_bytes()):
        raise ValueError("Saved OCR and the current scan PDF have different hashes.")

    catalogue_bytes = (ROOT / "data/reference/manufacturer_records.json").read_bytes()
    catalogue = json.loads(catalogue_bytes)
    extracted = build_pdf_candidates(analysis)
    results = [
        {**candidate, **match_pdf_candidate(candidate, catalogue)}
        for candidate in extracted["candidates"]
    ]
    counts = dict(Counter(r["decision"]["status"] for r in results))
    folder = ROOT / "reports/scanned_pdf"
    evidence = folder / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, evidence / "ocr_analysis_cpu.json")
    shutil.copyfile(pdf_path, evidence / "synthetic_schedule_scan.pdf")
    report = {
        "query_data_kind": "synthetic_schedule_scan",
        "scope": "One clean development fixture; broader document evaluation pending.",
        "run_origin": "standalone_diagnostic; separate from the later app run",
        "ocr_analysis_file": "evidence/ocr_analysis_cpu.json",
        "ocr_analysis_sha256": sha(analysis_bytes),
        "pdf_file": "evidence/synthetic_schedule_scan.pdf",
        "pdf_sha256": analysis["pdf_sha256"],
        "page_number": analysis["page_number"],
        "ocr_engine_info": analysis["ocr"]["engine_info"],
        "ocr_settings": analysis["ocr"]["settings"],
        "text_boxes": len(analysis["ocr"]["detections"]),
        "inference_seconds": analysis["ocr"]["inference_seconds"],
        "catalogue_id": catalogue["dataset_id"],
        "catalogue_reviewed_on": catalogue["reviewed_on"],
        "catalogue_sha256": sha(catalogue_bytes),
        "code_snapshot_sha256": {
            name: sha((ROOT / name).read_bytes()) for name in [
                "pdf_ocr.py", "ocr_worker.py", "pdf_candidates.py",
                "extract_schedule.py", "material_matcher.py", "material_review.py",
            ]
        },
        "counts": counts,
        "results": results,
    }
    (folder / "decisions_cpu.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = f"""# Scanned PDF OCR integration checkpoint

## Preserved standalone run

- Input: image-only PDF generated from the project's synthetic Japanese-English schedule.
- OCR text boxes: {report['text_boxes']}.
- Recorded inference time: {report['inference_seconds']:.3f} seconds.
- Extracted item blocks: {len(results)}.
- Reference decision counts: {json.dumps(counts)}.
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
"""
    (folder / "README.md").write_text(summary, encoding="utf-8")
    for record in results:
        print(f"{record['item_label']}: {record['decision']['status']} | "
              f"{record['decision']['reason']}")
    print("Counts:", counts)
    print("Saved checkpoint:", folder)


if __name__ == "__main__":
    main()
