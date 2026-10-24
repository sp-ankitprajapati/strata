import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data/processed/drawing_crop.png"
OUTPUT = ROOT / "data/processed/tiles_1600_200"

TILE_SIZE = 1600
MIN_OVERLAP = 200


def tile_starts(length):
    """Spread tiles across one dimension, including both edges."""
    if length <= TILE_SIZE:
        return [0]

    maximum_step = TILE_SIZE - MIN_OVERLAP
    intervals = math.ceil((length - TILE_SIZE) / maximum_step)

    return [
        round(i * (length - TILE_SIZE) / intervals)
        for i in range(intervals + 1)
    ]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    records = []

    with Image.open(SOURCE) as image:
        width, height = image.size

        for top in tile_starts(height):
            for left in tile_starts(width):
                right = min(left + TILE_SIZE, width)
                bottom = min(top + TILE_SIZE, height)

                tile_id = f"tile_{len(records) + 1:03d}"
                filename = f"{tile_id}.png"
                box = [left, top, right, bottom]

                image.crop(tuple(box)).save(OUTPUT / filename)

                records.append({
                    "tile_id": tile_id,
                    "filename": filename,
                    "box_in_crop": box,
                })

    manifest = {
        "source_image": SOURCE.name,
        "source_dimensions": [width, height],
        "tile_size": TILE_SIZE,
        "minimum_overlap": MIN_OVERLAP,
        "coordinate_space": "drawing_crop.png pixels",
        "tiles": records,
    }

    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"Source dimensions: {width} × {height}")
    print(f"Created {len(records)} tiles.")
    print(f"Saved tiles and manifest to: {OUTPUT}")


if __name__ == "__main__":
    main()