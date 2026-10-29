import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/processed"

VOCABULARY = {
    "stucco", "brick", "concrete", "stone", "iron", "glass", "tin"
}


def normalize(text):
    return re.sub(r"^\W+|\W+$", "", text.casefold())


def find_materials(filename):
    data = json.loads(
        (FOLDER / filename).read_text(encoding="utf-8")
    )

    matches = []

    for word in data["words"]:
        material = normalize(word["text"])

        if material in VOCABULARY:
            matches.append({
                "material": material,
                "raw_text": word["text"],
                "confidence": word["confidence"],
                "box": word["box"],
                "source_word_id": word["id"],
                "asbestos_status": "unresolved",
            })

    return matches


def main():
    baseline = find_materials("baseline_words_v2.json")
    tiled = find_materials("tiled_words_deduplicated.json")

    baseline_counts = Counter(
        item["material"] for item in baseline
    )
    tiled_counts = Counter(
        item["material"] for item in tiled
    )

    print(f"{'Material':<12} {'Baseline':>8} {'Tiled':>8}")

    for material in sorted(VOCABULARY):
        print(
            f"{material:<12} "
            f"{baseline_counts[material]:>8} "
            f"{tiled_counts[material]:>8}"
        )

    report = {
        "method": "Exact keyword matching after normalization",
        "vocabulary": sorted(VOCABULARY),
        "baseline_mentions": baseline,
        "tiled_mentions": tiled,
        "note": (
            "Counts are candidate mentions, not accuracy scores. "
            "Remaining duplicates and incorrect readings are possible."
        ),
    }

    (FOLDER / "material_comparison.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    with Image.open(FOLDER / "drawing_crop.png") as source:
        overlay = source.convert("RGB")

    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default(size=24)

    for index, item in enumerate(tiled, start=1):
        left, top, right, bottom = item["box"]

        draw.rectangle(
            (left, top, right, bottom),
            outline="blue",
            width=4,
        )

        label = (
            f"{index}: {item['material']} "
            f"({item['confidence']:.0f})"
        )

        draw.text(
            (left, max(0, top - 28)),
            label,
            fill="blue",
            font=font,
        )

    overlay.save(FOLDER / "tiled_material_boxes.png")

    print(f"\nBaseline material candidates: {len(baseline)}")
    print(f"Tiled material candidates: {len(tiled)}")
    print("Saved comparison JSON and material overlay.")


if __name__ == "__main__":
    main()