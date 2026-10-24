import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / "data/processed"
IOU_THRESHOLD = 0.5


def normalize(text):
    return re.sub(r"^\W+|\W+$", "", text.casefold())


def intersection_over_union(first, second):
    """Measure overlap: 0 means none; 1 means identical boxes."""
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])

    intersection = max(0, right - left) * max(0, bottom - top)

    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])

    union = first_area + second_area - intersection
    return intersection / union if union > 0 else 0.0


def main():
    source = json.loads(
        (FOLDER / "tiled_words_psm11.json").read_text(
            encoding="utf-8"
        )
    )

    # Consider higher-confidence candidates first.
    candidates = sorted(
        source["words"],
        key=lambda word: word["confidence"],
        reverse=True,
    )

    groups = defaultdict(list)
    retained = []

    for word in candidates:
        key = normalize(word["text"])
        duplicate = None

        if key:
            for existing in groups[key]:
                if word["tile_id"] in existing["source_tile_ids"]:
                    continue

                overlap = intersection_over_union(
                    word["box"], existing["box"]
                )

                if overlap >= IOU_THRESHOLD:
                    duplicate = existing
                    break

        if duplicate is not None:
            duplicate["source_tile_ids"].append(word["tile_id"])
            duplicate["duplicate_ids"].append(word["id"])
        else:
            record = {
                **word,
                "source_tile_ids": [word["tile_id"]],
                "duplicate_ids": [],
            }
            retained.append(record)

            if key:
                groups[key].append(record)

    retained.sort(key=lambda word: word["id"])

    report = {
        **source,
        "duplicates_removed": True,
        "deduplication": {
            "method": "Matching text and cross-tile box overlap",
            "iou_threshold": IOU_THRESHOLD,
            "input_count": len(candidates),
            "retained_count": len(retained),
        },
        "words": retained,
    }

    destination = FOLDER / "tiled_words_deduplicated.json"
    destination.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Input candidates: {len(candidates)}")
    print(f"Duplicates merged: {len(candidates) - len(retained)}")
    print(f"Retained candidates: {len(retained)}")
    print(f"Saved: {destination}")


if __name__ == "__main__":
    main()