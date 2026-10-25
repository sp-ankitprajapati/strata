import hashlib
import json
import math
import time
from pathlib import Path

from PIL import Image

from extract_reference_candidates import compact, parse_table


ROOT = Path(__file__).resolve().parent


def evaluate_names(reference_names, detections):
    results = []

    for name in reference_names:
        expected = compact(name).casefold()

        ids = [
            detection["id"]
            for detection in detections
            if compact(detection["text"]).casefold() == expected
        ]

        results.append({
            "reference_name": name,
            "recovered": bool(ids),
            "matched_detection_ids": ids,
        })

    return results


def main():
    import easyocr
    import torch

    torch.set_num_threads(2)

    evidence = ROOT / "reports/reference_extraction/evidence"
    inspection_path = evidence / "inspection.json"
    inspection = json.loads(
        inspection_path.read_text(encoding="utf-8")
    )

    targets = []

    for page in inspection["pages"]:
        for table_number, table in enumerate(
            page["table_candidates"], start=1
        ):
            names, _ = parse_table(table["rows"])

            if names and names[0]["group"] == "exterior_wall":
                targets.append((page, table_number, table, names))

    if len(targets) != 1:
        raise ValueError(
            "Expected exactly one exterior-wall table."
        )

    page, table_number, table, names = targets[0]
    image_path = evidence / f"page_{page['page_number']:03d}.png"

    output_dir = ROOT / "data/processed/kmew_ocr"
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as image:
        scale_x = image.width / page["width_pdf_points"]
        scale_y = image.height / page["height_pdf_points"]

        x1, y1, x2, y2 = table["bbox_pdf_points"]

        crop_box = [
            max(0, math.floor(x1 * scale_x) - 8),
            max(0, math.floor(y1 * scale_y) - 8),
            min(image.width, math.ceil(x2 * scale_x) + 8),
            min(image.height, math.ceil(y2 * scale_y) + 8),
        ]

        crop = image.crop(crop_box).convert("RGB")

    crop_path = output_dir / "wall_table.png"
    crop.save(crop_path)

    model_dir = ROOT / ".models/easyocr"
    model_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reference names: {len(names)}")
    print(f"OCR crop size: {crop.width} x {crop.height}")
    print("Loading Japanese-English OCR on CPU...")

    reader = easyocr.Reader(
        ["ja", "en"],
        gpu=False,
        model_storage_directory=str(model_dir),
    )

    start = time.perf_counter()

    predictions = reader.readtext(
        str(crop_path),
        detail=1,
        paragraph=False,
        batch_size=1,
        workers=0,
    )

    elapsed = time.perf_counter() - start

    detections = [
        {
            "id": number,
            "text": text,
            "confidence": float(confidence),
            "polygon_in_crop": [
                [float(x), float(y)] for x, y in polygon
            ],
        }
        for number, (polygon, text, confidence)
        in enumerate(predictions, start=1)
    ]

    results = evaluate_names(
        [name["name"] for name in names],
        detections,
    )
    recovered = sum(item["recovered"] for item in results)

    report = {
        "data_kind": "real_pdf_rasterized_table_ocr_experiment",
        "reference_basis": (
            "Native PDF extraction; not independent human ground truth"
        ),
        "scope": "One table selected using native PDF coordinates",
        "metric": (
            "Exact reference-name recovery from individual OCR boxes"
        ),
        "normalization": (
            "NFKC, whitespace removed, casefold; punctuation retained"
        ),
        "source_pdf_sha256": inspection["pdf_sha256"],
        "source_image_sha256": hashlib.sha256(
            image_path.read_bytes()
        ).hexdigest(),
        "inspection_sha256": hashlib.sha256(
            inspection_path.read_bytes()
        ).hexdigest(),
        "page": page["page_number"],
        "table": table_number,
        "crop_box_in_page_pixels": crop_box,
        "crop_sha256": hashlib.sha256(
            crop_path.read_bytes()
        ).hexdigest(),
        "easyocr_version": easyocr.__version__,
        "torch_version": str(torch.__version__),
        "device": "cpu",
        "languages": ["ja", "en"],
        "inference_seconds": round(elapsed, 3),
        "reference_count": len(results),
        "recovered_count": recovered,
        "strict_name_coverage": recovered / len(results),
        "results": results,
        "detections": detections,
    }

    output = (
        ROOT / "reports/reference_extraction/wall_table_ocr_cpu.json"
    )
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for item in results:
        status = "FOUND" if item["recovered"] else "MISSED"
        print(f"{status} | {item['reference_name']}")

    print(
        f"Strict name recovery: {recovered}/{len(results)} "
        f"({recovered / len(results):.1%})"
    )
    print(f"Inference time: {elapsed:.1f} seconds")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()