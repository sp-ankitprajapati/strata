import argparse
import json
from pathlib import Path

import easyocr
import torch


ROOT = Path(__file__).resolve().parent
TILES = ROOT / "data/processed/tiles_1600_200"
MODELS = ROOT / ".models/easyocr"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
    )
    args = parser.parse_args()

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable.")

    output = TILES / f"ocr_easyocr_{args.device}"
    output.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(
        (TILES / "manifest.json").read_text(encoding="utf-8")
    )

    print(f"Selected device: {args.device}", flush=True)

    reader = easyocr.Reader(
        ["en"],
        gpu="cuda:0" if args.device == "cuda" else False,
        model_storage_directory=str(MODELS),
        user_network_directory=str(MODELS / "user_network"),
    )

    detections = []

    for index, tile in enumerate(manifest["tiles"], start=1):
        print(
            f"EasyOCR {index}/{len(manifest['tiles'])}: "
            f"{tile['tile_id']}",
            flush=True,
        )

        raw_results = reader.readtext(
            str(TILES / tile["filename"]),
            detail=1,
            paragraph=False,
            workers=0,
            batch_size=1,
        )

        offset_x, offset_y = tile["box_in_crop"][:2]
        tile_results = []

        for polygon, text, confidence in raw_results:
            polygon_in_tile = [
                [float(x), float(y)] for x, y in polygon
            ]
            polygon_in_crop = [
                [x + offset_x, y + offset_y]
                for x, y in polygon_in_tile
            ]

            xs = [point[0] for point in polygon_in_crop]
            ys = [point[1] for point in polygon_in_crop]

            record = {
                "id": len(detections) + 1,
                "tile_id": tile["tile_id"],
                "text": text,
                "confidence": float(confidence),
                "polygon_in_tile": polygon_in_tile,
                "polygon_in_crop": polygon_in_crop,
                "box": [min(xs), min(ys), max(xs), max(ys)],
            }

            detections.append(record)
            tile_results.append(record)

        (output / f"{tile['tile_id']}.json").write_text(
            json.dumps(tile_results, indent=2),
            encoding="utf-8",
        )

        print(f"  Saved {len(tile_results)} text detections.")

    report = {
        "source_image": manifest["source_image"],
        "source_dimensions": manifest["source_dimensions"],
        "coordinate_space": "drawing_crop.png pixels",
        "engine": "EasyOCR",
        "easyocr_version": easyocr.__version__,
        "torch_version": torch.__version__,
        "settings": {
            "languages": ["en"],
            "device": args.device,
            "paragraph": False,
            "workers": 0,
            "batch_size": 1,
        },
        "confidence_scale": "0 to 1",
        "tile_count": len(manifest["tiles"]),
        "duplicates_removed": False,
        "detections": detections,
    }

    destination = (
        ROOT / "data/processed"
        / f"easyocr_tiled_{args.device}.json"
    )
    destination.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(
        f"\nSaved {len(detections)} text detections "
        "before deduplication."
    )
    print(f"Results: {destination}")


if __name__ == "__main__":
    main()