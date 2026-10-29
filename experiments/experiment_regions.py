import json
import subprocess
from pathlib import Path
from PIL import Image

project_folder = Path(__file__).resolve().parents[1]
source_path = project_folder / "data/processed/drawing_crop.png"
output_folder = project_folder / "data/processed/region_experiment"
output_folder.mkdir(parents=True, exist_ok=True)

# Coordinates expressed as fractions of the source image.
regions = {
    "stucco_on_brick": (0.333, 0.597, 0.460, 0.650),
    "iron_rail": (0.530, 0.574, 0.615, 0.608),
    "concrete_steps": (0.490, 0.913, 0.670, 0.947),
}

results = []

with Image.open(source_path) as image:
    width, height = image.size

    for name, region in regions.items():
        left, top, right, bottom = region

        box = (
            int(left * width),
            int(top * height),
            int(right * width),
            int(bottom * height),
        )

        region_path = output_folder / f"{name}.png"
        output_prefix = output_folder / name

        image.crop(box).save(region_path)

        subprocess.run(
            [
                "tesseract",
                str(region_path),
                str(output_prefix),
                "--oem", "1",
                "-l", "eng",
                "--psm", "11",
                "txt",
                "tsv",
            ],
            check=True,
        )

        text = output_prefix.with_suffix(".txt").read_text(
            encoding="utf-8"
        ).strip()

        print(f"\n{name}:")
        print(text if text else "[No text recognized]")

        results.append({
            "region": name,
            "box_in_source_crop": list(box),
            "recognized_text": text,
        })

report = {
    "source_image": source_path.name,
    "region_selection": "manual",
    "ocr_settings": {
        "engine_mode": 1,
        "language": "eng",
        "page_segmentation_mode": 11,
    },
    "results": results,
}

(output_folder / "results.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)