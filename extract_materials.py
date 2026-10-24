import json
import re
from pathlib import Path

project_folder = Path(__file__).resolve().parent
folder = project_folder / "data/processed"

ocr = json.loads(
    (folder / "baseline_words_v2.json").read_text(encoding="utf-8")
)

inspection = json.loads(
    (folder / "inspection.json").read_text(encoding="utf-8")
)

# Position of our source crop within the original drawing.
origin_x, origin_y = inspection["crop_box"][:2]

# A small pilot vocabulary, not an asbestos database.
material_keywords = {
    "stucco", "brick", "concrete",
    "stone", "iron", "glass", "tin",
}

mentions = []

for word in ocr["words"]:
    # Ignore capitalization and surrounding punctuation.
    normalized = re.sub(
        r"^\W+|\W+$", "", word["text"].casefold()
    )

    if normalized not in material_keywords:
        continue

    left, top, right, bottom = word["box"]

    mentions.append({
        "ocr_word_id": word["id"],
        "material": normalized,
        "original_ocr_text": word["text"],
        "ocr_confidence": word["confidence"],
        "box_in_crop": word["box"],
        "box_in_original_drawing": [
            left + origin_x,
            top + origin_y,
            right + origin_x,
            bottom + origin_y,
        ],
        "asbestos_status": "unresolved",
    })

report = {
    "document_id": "old_capitol_sheet_14",
    "method": "English keyword baseline",
    "mentions": mentions,
}

(folder / "material_mentions.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print(f"Found {len(mentions)} material mentions.")

for mention in mentions:
    print(
        f"{mention['material']} | "
        f"OCR: {mention['original_ocr_text']} | "
        f"Confidence: {mention['ocr_confidence']:.1f}"
    )