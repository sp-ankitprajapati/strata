"""Prepare and evaluate a fixed synthetic scan suite without tuning the OCR."""

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from evaluate_regions import edit_distance
from evaluate_schedule_ocr import normalize_for_cer
from ocr_worker import run_isolated_ocr
from pdf_candidates import build_pdf_candidates, match_pdf_candidate


ROOT = Path(__file__).resolve().parent
CONDITIONS = ("clean", "skew_1_5", "blur_0_8")
SCENARIOS = [
    {"id": "V-101", "product_name": "ゴールデン モエンサイディング",
     "manufacturer": "Nichiha", "manufacture_month": "1980-02",
     "status": "asbestos_containing", "reason": "exact_product_manufacturer_and_month_match"},
    {"id": "V-102", "product_name": "モエンサイディング-M",
     "manufacturer": "Nichiha", "manufacture_month": "2001-09",
     "status": "non_asbestos_containing", "reason": "exact_product_manufacturer_and_month_match"},
    {"id": "V-103", "product_name": "モエンサイディング-M",
     "manufacturer": "Nichiha", "manufacture_month": None,
     "status": "unresolved", "reason": "manufacture_month_missing"},
    {"id": "V-104", "product_name": "モエンサイディング-M",
     "manufacturer": "Example Supplier", "manufacture_month": "2001-09",
     "status": "unresolved", "reason": "manufacturer_mismatch"},
]


def digest(content):
    return hashlib.sha256(content).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_suite(font_path):
    folder = ROOT / "reports/validation_suite"
    if (folder / "manifest.json").exists():
        raise FileExistsError("The suite is already prepared. Use --run with its saved inputs.")
    font = ImageFont.truetype(str(font_path), size=36)
    try:
        font.set_variation_by_axes([400])
    except (OSError, ValueError):
        pass
    fixtures = folder / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    cases = []
    for scenario in SCENARIOS:
        date_line = (
            f"Manufacture month: {scenario['manufacture_month']}"
            if scenario["manufacture_month"] else "Installation year: 2001"
        )
        lines = ["Data type: synthetic", "", f"Item: {scenario['id']}",
                 f"Product: {scenario['product_name']}",
                 f"Manufacturer: {scenario['manufacturer']}", date_line]
        width = max(1200, int(max(font.getlength(line) for line in lines)) + 120)
        original = Image.new("RGB", (width, 120 + 60 * len(lines)), "white")
        draw = ImageDraw.Draw(original)
        for index, line in enumerate(lines):
            draw.text((60, 60 + index * 60), line, font=font, fill="black", anchor="lt")
        for condition in CONDITIONS:
            image = original.copy()
            if condition == "skew_1_5":
                image = image.rotate(1.5, Image.Resampling.BICUBIC,
                                     expand=True, fillcolor="white")
            elif condition == "blur_0_8":
                image = image.filter(ImageFilter.GaussianBlur(0.8))
            case_id = f"{scenario['id']}_{condition}"
            path = fixtures / f"{case_id}.pdf"
            image.save(path, "PDF", resolution=150, title=f"Synthetic {case_id}")
            cases.append({
                "case_id": case_id, "condition": condition,
                "pdf_file": path.relative_to(folder).as_posix(),
                "pdf_sha256": digest(path.read_bytes()),
                "expected_text": "\n".join(line for line in lines if line),
                "expected": dict(scenario),
            })
    write_json(folder / "manifest.json", {
        "data_kind": "synthetic_development_stress_suite",
        "scope": "Four scenarios with three correlated scan variants each.",
        "alignment": "One expected item per page; OCR item IDs are scored separately.",
        "font_sha256": digest(font_path.read_bytes()), "font_size": 36,
        "cases": cases,
    })
    print(f"Prepared {len(cases)} frozen cases: {folder}", flush=True)


def field_text(value):
    return "".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def score_case(case, analysis, catalogue):
    expected = case["expected"]
    results = [] if analysis is None else [
        {**candidate, **match_pdf_candidate(candidate, catalogue)}
        for candidate in build_pdf_candidates(analysis)["candidates"]
    ]
    record = results[0] if len(results) == 1 else None
    decision = record["decision"] if record else {}
    query = record["query"] if record else {}
    edits = characters = None
    if analysis is not None:
        reference = normalize_for_cer(case["expected_text"])
        prediction = normalize_for_cer(analysis["text"])
        edits, characters = edit_distance(reference, prediction), len(reference)
    return {
        "case_id": case["case_id"], "condition": case["condition"],
        "execution_ok": analysis is not None, "extracted_items": len(results),
        "expected_status": expected["status"], "predicted_status": decision.get("status"),
        "status_agreement": decision.get("status") == expected["status"],
        "reason_agreement": decision.get("reason") == expected["reason"],
        "incorrect_resolved_decision": (
            decision.get("status") in {"asbestos_containing", "non_asbestos_containing"}
            and decision["status"] != expected["status"]
        ),
        "field_agreement_ignoring_spacing": {
            field: bool(record) and field_text(query.get(field)) == field_text(expected[field])
            for field in ("product_name", "manufacturer", "manufacture_month")
        },
        "item_id_agreement": bool(record) and field_text(record["item_label"]) == field_text(expected["id"]),
        "cer_edits": edits, "reference_characters": characters,
        "cer": edits / characters if characters else None,
        "inference_seconds": analysis["ocr"]["inference_seconds"] if analysis else None,
        "results": results,
    }


def summarise(rows):
    completed = [r for r in rows if r["execution_ok"]]
    characters = sum(r["reference_characters"] for r in completed)
    edits = sum(r["cer_edits"] for r in completed)
    class_metrics = {}
    for label in ("asbestos_containing", "non_asbestos_containing"):
        tp = sum(r["expected_status"] == label and r["predicted_status"] == label for r in rows)
        fp = sum(r["expected_status"] != label and r["predicted_status"] == label for r in rows)
        fn = sum(r["expected_status"] == label and r["predicted_status"] != label for r in rows)
        class_metrics[label] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        }
    return {
        "cases": len(rows), "completed": len(completed),
        "status_agreement_count": sum(r["status_agreement"] for r in rows),
        "reason_agreement_count": sum(r["reason_agreement"] for r in rows),
        "single_item_count": sum(r["extracted_items"] == 1 for r in rows),
        "item_id_agreement_count": sum(r["item_id_agreement"] for r in rows),
        "incorrect_resolved_decisions": sum(r["incorrect_resolved_decision"] for r in rows),
        "field_agreement_counts": {
            field: sum(r["field_agreement_ignoring_spacing"][field] for r in rows)
            for field in ("product_name", "manufacturer", "manufacture_month")
        },
        "cer_over_completed_runs": edits / characters if characters else None,
        "cer_edits": edits, "reference_characters": characters,
        "resolved_class_metrics": class_metrics,
    }


def run_suite():
    folder = ROOT / "reports/validation_suite"
    manifest_bytes = (folder / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    catalogue_bytes = (ROOT / "data/reference/manufacturer_records.json").read_bytes()
    catalogue = json.loads(catalogue_bytes)
    fingerprint = {
        "manifest_sha256": digest(manifest_bytes),
        "catalogue_sha256": digest(catalogue_bytes),
        "pipeline_snapshot_sha256": {
            name: digest((ROOT / name).read_bytes()) for name in [
                "validate_pipeline.py", "ocr_worker.py", "pdf_ocr.py",
                "pdf_candidates.py", "extract_schedule.py",
                "material_matcher.py", "material_review.py", "evaluate_schedule_ocr.py",
                "pdf_processing.py", "evaluate_regions.py",
            ]
        },
    }
    predictions = folder / "predictions"
    predictions.mkdir(exist_ok=True)
    rows = []
    for index, case in enumerate(manifest["cases"], 1):
        content = (folder / case["pdf_file"]).read_bytes()
        if digest(content) != case["pdf_sha256"]:
            raise ValueError(f"Changed fixture: {case['case_id']}")
        output = predictions / f"{case['case_id']}_evaluation.json"
        cached = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
        if cached and cached["fingerprint"] != fingerprint:
            raise ValueError("Saved results use different code or inputs. Preserve them before starting a new suite version.")
        if cached and cached["evaluation"]["execution_ok"]:
            row = cached["evaluation"]
            print(f"[{index}/{len(manifest['cases'])}] Reusing {case['case_id']}", flush=True)
        else:
            print(f"[{index}/{len(manifest['cases'])}] OCR {case['case_id']}", flush=True)
            error = None
            try:
                analysis = run_isolated_ocr(content, 1)
            except (RuntimeError, OSError) as failure:
                analysis, error = None, str(failure)
            row = score_case(case, analysis, catalogue)
            if analysis is not None:
                write_json(predictions / f"{case['case_id']}_ocr.json", analysis)
            if error:
                row["execution_error"] = error
            write_json(output, {"fingerprint": fingerprint, "evaluation": row})
        rows.append(row)
        print(f"  items={row['extracted_items']} status={row['predicted_status']} "
              f"status_agreement={row['status_agreement']}", flush=True)
    summary = {
        "data_kind": manifest["data_kind"], "fingerprint": fingerprint,
        "overall": summarise(rows),
        "by_condition": {c: summarise([r for r in rows if r["condition"] == c]) for c in CONDITIONS},
    }
    write_json(folder / "summary.json", summary)
    lines = ["# Synthetic scan stress evaluation", "",
             "Scope: four item scenarios, each rendered clean, with 1.5-degree skew and with 0.8-pixel Gaussian blur. Variants share source content. Results describe this small synthetic suite; independent real-document evaluation remains separate.", "",
             "OCR receives only PDF bytes and a page number. Expected text, fields and decisions are used afterwards for scoring. One item is expected per page; zero or multiple extracted items cannot count as a correct unresolved decision. OCR item IDs are scored separately and remain unchanged.", "",
             "CER uses NFKC, casefolding and collapsed whitespace while preserving Japanese and punctuation. Field comparison ignores whitespace after NFKC and casefolding. CER covers completed OCR runs; decision agreement includes every case, including execution failures.", "",
             "| Condition | Completed | Decision agreement | Reason agreement | Incorrect resolved | CER |",
             "|---|---:|---:|---:|---:|---:|"]
    for condition, result in {**summary["by_condition"], "Overall": summary["overall"]}.items():
        total = result["cases"]
        cer = result["cer_over_completed_runs"]
        lines.append(f"| {condition} | {result['completed']}/{total} | "
                     f"{result['status_agreement_count']}/{total} | {result['reason_agreement_count']}/{total} | "
                     f"{result['incorrect_resolved_decisions']} | {cer:.1%} |" if cer is not None else
                     f"| {condition} | {result['completed']}/{total} | 0/{total} | 0/{total} | 0 | N/A |")
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary["overall"], indent=2), flush=True)
    print(f"Saved: {folder / 'summary.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--font", type=Path, default=ROOT / "data/raw/fonts/NotoSansJP.ttf")
    args = parser.parse_args()
    if args.prepare:
        prepare_suite(args.font)
    else:
        run_suite()


if __name__ == "__main__":
    main()
