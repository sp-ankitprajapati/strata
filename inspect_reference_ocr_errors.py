import hashlib
import json
from pathlib import Path

from PIL import Image

from extract_reference_candidates import compact


ROOT = Path(__file__).resolve().parent


def main():
    evidence = ROOT / "reports/reference_extraction/evidence"
    benchmark_path = (
        ROOT / "reports/reference_extraction/wall_table_ocr_cpu.json"
    )

    benchmark = json.loads(
        benchmark_path.read_text(encoding="utf-8")
    )
    inspection = json.loads(
        (evidence / "inspection.json").read_text(encoding="utf-8")
    )

    page = next(
        page for page in inspection["pages"]
        if page["page_number"] == benchmark["page"]
    )

    image_path = evidence / f"page_{benchmark['page']:03d}.png"

    with Image.open(image_path) as image:
        scale_y = image.height / page["height_pdf_points"]

    crop_top = benchmark["crop_box_in_page_pixels"][1]
    errors = []

    for result in benchmark["results"]:
        if result["recovered"]:
            continue

        name = result["reference_name"]

        native_words = [
            word for word in page["words"]
            if compact(word["text"]) == compact(name)
        ]

        if len(native_words) != 1:
            raise ValueError(
                f"Could not locate one native text box for: {name}"
            )

        word = native_words[0]
        top = word["top"] * scale_y - crop_top
        bottom = word["bottom"] * scale_y - crop_top

        row_detections = []

        for detection in benchmark["detections"]:
            ys = [
                point[1]
                for point in detection["polygon_in_crop"]
            ]

            overlap = min(bottom, max(ys)) - max(top, min(ys))

            if overlap >= 0.5 * (bottom - top):
                row_detections.append(detection)

        row_detections.sort(
            key=lambda detection: min(
                point[0]
                for point in detection["polygon_in_crop"]
            )
        )

        print(f"\nREFERENCE: {name}")
        print(
            "OCR ROW: "
            + (
                " | ".join(
                    detection["text"]
                    for detection in row_detections
                )
                or "(no overlapping detection)"
            )
        )

        errors.append({
            "reference_name": name,
            "expected_vertical_band_in_crop_pixels": [top, bottom],
            "ocr_row_context": row_detections,
        })

    output = benchmark_path.parent / "wall_table_ocr_errors.json"
    output.write_text(
        json.dumps(
            {
                "benchmark_sha256": hashlib.sha256(
                    benchmark_path.read_bytes()
                ).hexdigest(),
                "purpose": "Diagnostic row alignment; predictions unchanged",
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nMissed names inspected: {len(errors)}")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()