import csv
import json
import re
from collections import defaultdict
from pathlib import Path

project_folder = Path(__file__).resolve().parent
folder = project_folder / "data/processed"

material_keywords = {
    "stucco", "brick", "concrete",
    "stone", "iron", "glass", "tin",
}

lines = defaultdict(list)

with (folder / "baseline.tsv").open(
    encoding="utf-8", newline=""
) as file:
    reader = csv.DictReader(
        file,
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
    )

    for row in reader:
        if row["level"] != "5" or not row["text"].strip():
            continue

        line_id = tuple(
            row[field]
            for field in (
                "page_num", "block_num", "par_num", "line_num"
            )
        )
        lines[line_id].append(row)

annotations = []

for line_id, words in lines.items():
    words.sort(key=lambda word: int(word["word_num"]))

    normalized_words = {
        re.sub(r"^\W+|\W+$", "", word["text"].casefold())
        for word in words
    }

    materials = sorted(normalized_words & material_keywords)

    if not materials:
        continue

    annotation = {
        "line_id": "-".join(line_id),
        "raw_text": " ".join(word["text"] for word in words),
        "materials": materials,
        "box_in_crop": [
            min(int(word["left"]) for word in words),
            min(int(word["top"]) for word in words),
            max(int(word["left"]) + int(word["width"])
                for word in words),
            max(int(word["top"]) + int(word["height"])
                for word in words),
        ],
        "asbestos_status": "unresolved",
    }

    annotations.append(annotation)
    print(annotation["raw_text"])

report = {
    "source_image": "drawing_crop.png",
    "method": "Tesseract line grouping and material keywords",
    "annotations": annotations,
}

(folder / "material_contexts.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print(f"\nSaved {len(annotations)} material-bearing OCR lines.")