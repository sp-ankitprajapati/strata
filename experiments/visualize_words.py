import csv
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

project_folder = Path(__file__).resolve().parents[1]
folder = project_folder / "data/processed"

with (folder / "baseline.tsv").open(
    encoding="utf-8", newline=""
) as file:
    rows = list(
    csv.DictReader(
        file,
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
    )
)

word_rows = [
    row for row in rows
    if row["level"] == "5" and row["text"].strip()
]

if not word_rows:
    raise ValueError("The TSV contains no non-empty word candidates.")

with Image.open(folder / "drawing_crop.png") as source:
    image = source.convert("RGB")

# Confirm that the OCR data belongs to this image size.
page_row = next(row for row in rows if row["level"] == "1")
tsv_size = (int(page_row["width"]), int(page_row["height"]))

if image.size != tsv_size:
    raise ValueError(
        f"Image size {image.size} differs from TSV size {tsv_size}."
    )

draw = ImageDraw.Draw(image)
font = ImageFont.load_default(size=22)
words = []

for word_id, row in enumerate(word_rows, start=1):
    left = int(row["left"])
    top = int(row["top"])
    right = left + int(row["width"])
    bottom = top + int(row["height"])
    confidence = float(row["conf"])

    words.append({
        "id": word_id,
        "text": row["text"],
        "confidence": confidence,
        "box": [left, top, right, bottom],
    })

    colour = "green" if confidence >= 60 else "red"

    draw.rectangle(
        (left, top, right, bottom),
        outline=colour,
        width=3,
    )
    draw.text(
        (left, max(0, top - 24)),
        str(word_id),
        fill=colour,
        font=font,
    )

# A visible label helps us identify the newly generated image.
draw.rectangle((0, 0, 1800, 75), fill="white")
draw.text(
    (12, 12),
    f"Strata overlay v2: {len(words)} word candidates",
    fill="blue",
    font=ImageFont.load_default(size=38),
)

image.save(folder / "baseline_boxes_v2.png")

report = {
    "source_image": "drawing_crop.png",
    "coordinate_space": "source-image pixels",
    "display_threshold": 60,
    "words": words,
}

(folder / "baseline_words_v2.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Image dimensions: {image.size}")
print(f"Word candidates read and drawn: {len(words)}")
print(f"Lowest box boundary: {max(word['box'][3] for word in words)}")
print("Last three candidates:")
for word in words[-3:]:
    print(word)

print("Saved baseline_boxes_v2.png")