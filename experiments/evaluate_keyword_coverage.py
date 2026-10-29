import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/processed"
OUTPUT = FOLDER / "keyword_benchmark"

# Manually selected development regions.
# Coordinates are fractions of drawing_crop.png dimensions.
REGIONS = {
    "central_stucco_on_brick": {
        "box": [0.333, 0.597, 0.460, 0.650],
        "expected": ["stucco", "brick"],
    },
    "iron_rail": {
        "box": [0.530, 0.574, 0.615, 0.608],
        "expected": ["iron"],
    },
    "concrete_steps": {
        "box": [0.490, 0.913, 0.670, 0.947],
        "expected": ["concrete"],
    },
    "central_door_glass": {
        "box": [0.535, 0.694, 0.600, 0.738],
        "expected": ["glass"],
    },
    "left_tin_roof": {
        "box": [0.020, 0.410, 0.155, 0.452],
        "expected": ["tin"],
    },
    "upper_right_stucco_on_brick": {
        "box": [0.730, 0.179, 0.875, 0.216],
        "expected": ["stucco", "brick"],
    },
}


def center_inside(word_box, region_box):
    center_x = (word_box[0] + word_box[2]) / 2
    center_y = (word_box[1] + word_box[3]) / 2

    left, top, right, bottom = region_box
    return left <= center_x < right and top <= center_y < bottom


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    comparison = json.loads(
        (FOLDER / "material_comparison_all.json").read_text(
            encoding="utf-8"
        )
    )

    pipelines = {
        "baseline": comparison["baseline_mentions"],
        "tiled": comparison["tiled_mentions"],
        "easyocr_gpu": comparison["easyocr_gpu_mentions"],
    }

    totals = {name: 0 for name in pipelines}
    reference_count = 0
    records = []

    with Image.open(FOLDER / "drawing_crop.png") as image:
        width, height = image.size

        for name, region in REGIONS.items():
            box = [
                round(region["box"][0] * width),
                round(region["box"][1] * height),
                round(region["box"][2] * width),
                round(region["box"][3] * height),
            ]

            image.crop(tuple(box)).save(OUTPUT / f"{name}.png")

            expected = set(region["expected"])
            reference_count += len(expected)

            record = {
                "region": name,
                "box": box,
                "expected": sorted(expected),
            }

            print(f"\n{name}: expected {', '.join(sorted(expected))}")

            for pipeline, mentions in pipelines.items():
                found = {
                    item["material"]
                    for item in mentions
                    if center_inside(item["box"], box)
                }

                matched = expected & found
                totals[pipeline] += len(matched)

                record[pipeline] = {
                    "matched": sorted(matched),
                    "missed": sorted(expected - matched),
                }

                print(
                    f"  {pipeline}: "
                    f"{', '.join(sorted(matched)) or '(none)'}"
                )

            records.append(record)

    print("\nTarget keyword coverage:")

    for pipeline, matched_count in totals.items():
        print(
            f"{pipeline}: {matched_count}/{reference_count} "
            f"({matched_count / reference_count:.1%})"
        )

    report = {
        "scope": "Six manually selected development regions",
        "matching_rule": (
            "Exact material identity and candidate box center "
            "inside the reference region"
        ),
        "reference_keyword_occurrences": reference_count,
        "matched_counts": totals,
        "regions": records,
    }

    (OUTPUT / "coverage.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()