import hashlib
import json
import platform
import time
from pathlib import Path

import easyocr
import torch


ROOT = Path(__file__).resolve().parent


def main():
    torch.set_num_threads(2)

    folder = ROOT / "data/processed/synthetic_schedule"
    image_path = folder / "schedule_clean.png"

    if not image_path.exists():
        raise FileNotFoundError("Run render_schedule.py first.")

    model_dir = ROOT / ".models/easyocr"
    model_dir.mkdir(parents=True, exist_ok=True)

    print("Loading English-Japanese OCR on CPU...")

    reader = easyocr.Reader(
        ["ja", "en"],
        gpu=False,
        model_storage_directory=str(model_dir),
    )

    start = time.perf_counter()

    predictions = reader.readtext(
        str(image_path),
        detail=1,
        paragraph=False,
        batch_size=1,
        workers=0,
    )

    elapsed = time.perf_counter() - start
    detections = []

    for index, (polygon, text, confidence) in enumerate(
        predictions, start=1
    ):
        detections.append({
            "id": index,
            "polygon": [[float(x), float(y)] for x, y in polygon],
            "text": text,
            "confidence": float(confidence),
        })

        print(f"{index:02d} | {float(confidence):.3f} | {text}")

    output = {
        "data_kind": "synthetic_schedule_ocr",
        "image_file": image_path.relative_to(ROOT).as_posix(),
        "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        "engine": "EasyOCR",
        "easyocr_version": easyocr.__version__,
        "torch_version": torch.__version__,
        "python_version": platform.python_version(),
        "languages": ["ja", "en"],
        "device": "cpu",
        "inference_seconds": round(elapsed, 3),
        "detections": detections,
    }

    output_path = folder / "easyocr_ja_en_cpu.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Text detections: {len(detections)}")
    print(f"Inference time: {elapsed:.1f} seconds")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()