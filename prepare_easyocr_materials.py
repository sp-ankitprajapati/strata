import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from deduplicate_words import intersection_over_union


ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / "data/processed"


def main():
    source = json.loads(
        (FOLDER / "easyocr_material_candidates_cuda.json")
        .read_text(encoding="utf-8")
    )

    mentions = []

    for candidate in source["candidates"]:
        for material in candidate["materials"]:
            mentions.append({
                "material": material,
                "raw_text": candidate["text"],
                "confidence": candidate["confidence"],
                "box": candidate["box"],
                "source_tile_ids": [candidate["tile_id"]],
                "source_detection_ids": [candidate["id"]],
                "asbestos_status": "unresolved",
            })

    retained = []

    for mention in sorted(
        mentions,
        key=lambda item: item["confidence"],
        reverse=True,
    ):
        duplicate = None

        for existing in retained:
            same_material = (
                mention["material"] == existing["material"]
            )
            different_tile = (
                mention["source_tile_ids"][0]
                not in existing["source_tile_ids"]
            )

            if (
                same_material
                and different_tile
                and intersection_over_union(
                    mention["box"], existing["box"]
                ) >= 0.5
            ):
                duplicate = existing
                break

        if duplicate is None:
            retained.append(mention)
        else:
            duplicate["source_tile_ids"].extend(
                mention["source_tile_ids"]
            )
            duplicate["source_detection_ids"].extend(
                mention["source_detection_ids"]
            )

    comparison = json.loads(
        (FOLDER / "material_comparison.json").read_text(
            encoding="utf-8"
        )
    )

    comparison["method"] = (
        "Material candidates from multiple OCR pipelines "
        "in shared drawing coordinates"
    )
    comparison["easyocr_gpu_mentions"] = retained
    comparison["easyocr_gpu_metadata"] = {
        "input_file": "easyocr_material_candidates_cuda.json",
        "easyocr_version": source["easyocr_version"],
        "torch_version": source["torch_version"],
        "settings": source["settings"],
        "input_mentions": len(mentions),
        "retained_mentions": len(retained),
        "deduplication_iou_threshold": 0.5,
        "position_granularity": "OCR text box; may span several words",
    }

    (FOLDER / "material_comparison_all.json").write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )

    with Image.open(FOLDER / "drawing_crop.png") as image:
        overlay = image.convert("RGB")

    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default(size=24)

    for index, item in enumerate(retained, start=1):
        left, top, right, bottom = item["box"]

        draw.rectangle(
            (left, top, right, bottom),
            outline="blue",
            width=4,
        )
        draw.text(
            (left, max(0, top - 28)),
            f"{index}: {item['material']}",
            fill="blue",
            font=font,
        )

    overlay.save(FOLDER / "easyocr_material_boxes_cuda.png")

    print(f"GPU material mentions before merging: {len(mentions)}")
    print(f"GPU material mentions after merging: {len(retained)}")
    print("Saved combined comparison and GPU material overlay.")


if __name__ == "__main__":
    main()