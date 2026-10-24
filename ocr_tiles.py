import csv
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TILES = ROOT / "data/processed/tiles_1600_200"
OUTPUT = TILES / "ocr_psm11"


def main():
    manifest = json.loads(
        (TILES / "manifest.json").read_text(encoding="utf-8")
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)

    words = []

    for index, tile in enumerate(manifest["tiles"], start=1):
        tile_id = tile["tile_id"]
        prefix = OUTPUT / tile_id

        print(
            f"OCR {index}/{len(manifest['tiles'])}: {tile_id}",
            flush=True,
        )

        result = subprocess.run(
            [
                "tesseract",
                str(TILES / tile["filename"]),
                str(prefix),
                "--oem", "1",
                "-l", "eng",
                "--psm", "11",
                "txt", "tsv",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"OCR failed for {tile_id}:\n{result.stderr}"
            )

        offset_x, offset_y = tile["box_in_crop"][:2]

        with prefix.with_suffix(".tsv").open(
            encoding="utf-8", newline=""
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter="\t",
                quoting=csv.QUOTE_NONE,
            )

            for row in reader:
                text = row["text"].strip()

                if row["level"] != "5" or not text:
                    continue

                left = int(row["left"])
                top = int(row["top"])
                right = left + int(row["width"])
                bottom = top + int(row["height"])

                words.append({
                    "id": len(words) + 1,
                    "tile_id": tile_id,
                    "text": text,
                    "confidence": float(row["conf"]),
                    "line_id": [
                        row["page_num"],
                        row["block_num"],
                        row["par_num"],
                        row["line_num"],
                    ],
                    "box_in_tile": [left, top, right, bottom],
                    "box": [
                        left + offset_x,
                        top + offset_y,
                        right + offset_x,
                        bottom + offset_y,
                    ],
                })

    report = {
        "source_image": manifest["source_image"],
        "source_dimensions": manifest["source_dimensions"],
        "coordinate_space": "drawing_crop.png pixels",
        "settings": {"oem": 1, "language": "eng", "psm": 11},
        "tile_count": len(manifest["tiles"]),
        "duplicates_removed": False,
        "words": words,
    }

    destination = ROOT / "data/processed/tiled_words_psm11.json"
    destination.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved {len(words)} word candidates before deduplication.")
    print(f"Results: {destination}")


if __name__ == "__main__":
    main()