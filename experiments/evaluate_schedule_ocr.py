import hashlib
import json
import unicodedata
from pathlib import Path

from experiments.evaluate_regions import edit_distance
from ocr_layout import reconstruct_lines
from extract_schedule import extract_schedule
from material_matcher import unresolved
from material_review import review_material


ROOT = Path(__file__).resolve().parents[1]


def normalize_for_cer(text):
    # Preserve Japanese characters and punctuation.
    return " ".join(
        unicodedata.normalize("NFKC", text).casefold().split()
    )




def main():
    folder = ROOT / "data/processed/synthetic_schedule"

    prediction_path = folder / "easyocr_ja_en_cpu.json"
    predictions = json.loads(
        prediction_path.read_text(encoding="utf-8")
    )
    truth = json.loads(
        (folder / "ground_truth.json").read_text(encoding="utf-8")
    )

    if predictions["image_sha256"] != truth["image_sha256"]:
        raise ValueError("OCR and ground truth refer to different images.")

    lines = reconstruct_lines(predictions["detections"])
    predicted_text = "\n".join(line["text"] for line in lines)
    expected_text = "\n".join(line["text"] for line in truth["lines"])

    reference = normalize_for_cer(expected_text)
    prediction = normalize_for_cer(predicted_text)

    scores = {}

    comparisons = [
        ("cer_with_spaces", reference, prediction),
        (
            "cer_without_spaces",
            reference.replace(" ", ""),
            prediction.replace(" ", ""),
        ),
    ]

    for name, expected, actual in comparisons:
        edits = edit_distance(expected, actual)
        scores[name] = {
            "edits": edits,
            "reference_characters": len(expected),
            "cer": edits / len(expected),
        }
        print(f"{name}: {scores[name]['cer']:.1%}")

    # Only OCR text goes into extraction and matching.
    records = extract_schedule(predicted_text)

    catalogue_bytes = (
        ROOT / "data/reference/manufacturer_records.json"
    ).read_bytes()
    catalogue = json.loads(catalogue_bytes)

    for record in records:
        if record["issues"]:
            result = {
                "decision": unresolved("conflicting_extracted_fields"),
                "suggestions": [],
            }
        else:
            result = review_material(record["query"], catalogue)

        record.update(result)

        print(
            f"{record['item_label']}: "
            f"{record['decision']['status']} | "
            f"{record['decision']['reason']}"
        )

    report = {
        "field_label_handling": "Whitespace removed and case folded in field labels only",
        "data_kind": "synthetic_schedule_ocr_evaluation",
        "scope": "One clean development image; not real-drawing accuracy",
        "normalization": (
            "NFKC, casefold, whitespace collapsed; punctuation retained"
        ),
        "line_reconstruction": (
            "50% vertical overlap, then left-to-right"
        ),
        "image_sha256": predictions["image_sha256"],
        "ocr_predictions_sha256": hashlib.sha256(
            prediction_path.read_bytes()
        ).hexdigest(),
        "extractor_sha256": hashlib.sha256(
            (ROOT / "extract_schedule.py").read_bytes()
        ).hexdigest(),
        "catalogue_sha256": hashlib.sha256(catalogue_bytes).hexdigest(),
        "scores": scores,
        "reconstructed_lines": lines,
        "results": records,
    }

    path = ROOT / "reports/schedule_extraction/ocr_label_normalized_evaluation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (folder / "ocr_reconstructed.txt").write_text(
        predicted_text,
        encoding="utf-8",
    )

    print(f"Reconstructed lines: {len(lines)}")
    print(f"Extracted items: {len(records)}")
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()