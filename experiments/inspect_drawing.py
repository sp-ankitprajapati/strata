import json
from pathlib import Path
from PIL import Image

project_folder = Path(__file__).resolve().parents[1]
image_path = project_folder / "data/raw/old_capitol_sheet_14.png"
output_folder = project_folder / "data/processed"
output_folder.mkdir(parents=True, exist_ok=True)

with Image.open(image_path) as image:
    width, height = image.size

    print(f"Image dimensions: {width} × {height} pixels")
    print(f"Image colour mode: {image.mode}")

    # A smaller overview for convenient viewing.
    preview = image.copy()
    preview.thumbnail((2200, 2200))
    preview.save(output_folder / "drawing_preview.png")

    # Preserve full resolution within a central region.
    crop_box = (
        width // 4,
        height // 3,
        3 * width // 4,
        4 * height // 5,
    )
    crop = image.crop(crop_box)
    crop.save(output_folder / "drawing_crop.png")

    # Record where the crop came from.
    inspection = {
        "source_file": image_path.name,
        "width": width,
        "height": height,
        "crop_box": list(crop_box),
    }

(output_folder / "inspection.json").write_text(
    json.dumps(inspection, indent=2),
    encoding="utf-8",
)

print("Saved preview, full-resolution crop, and inspection record.")