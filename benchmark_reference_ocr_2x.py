import hashlib
import json
import time

from PIL import Image

from benchmark_reference_ocr import ROOT, evaluate_names


def main():
    import easyocr
    import torch

    torch.set_num_threads(2)

    report_dir = ROOT / "reports/reference_extraction"
    baseline_path = report_dir / "wall_table_ocr_cpu.json"
    baseline = json.loads(
        baseline_path.read_text(encoding="utf-8")
    )

    if (
        easyocr.__version__ != baseline["easyocr_version"]
        or str(torch.__version__) != baseline["torch_version"]
    ):
        raise ValueError(
            "Use the same OCR environment as the baseline."
        )

    folder = ROOT / "data/processed/kmew_ocr"
    original_path = folder / "wall_table.png"

    original_sha = hashlib.sha256(
        original_path.read_bytes()
    ).hexdigest()

    if original_sha != baseline["crop_sha256"]:
        raise ValueError(
            "The source crop differs from the baseline."
        )

    with Image.open(original_path) as original:
        enlarged = original.resize(
            (original.width * 2, original.height * 2),
            Image.Resampling.LANCZOS,
        )

    image_path = folder / "wall_table_2x.png"
    enlarged.save(image_path)

    print(
        f"OCR crop size: {enlarged.width} x {enlarged.height}"
    )
    print("Loading the same Japanese-English OCR model on CPU...")

    reader = easyocr.Reader(
        ["ja", "en"],
        gpu=False,
        model_storage_directory=str(ROOT / ".models/easyocr"),
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

    detections = [
        {
            "id": number,
            "text": text,
            "confidence": float(confidence),
            "polygon_in_crop": [
                [float(x), float(y)] for x, y in polygon
            ],
        }
        for number, (polygon, text, confidence)
        in enumerate(predictions, start=1)
    ]

    reference_names = [
        row["reference_name"] for row in baseline["results"]
    ]
    results = evaluate_names(reference_names, detections)
    recovered = sum(row["recovered"] for row in results)

    before = {
        row["reference_name"]
        for row in baseline["results"]
        if row["recovered"]
    }
    after = {
        row["reference_name"]
        for row in results
        if row["recovered"]
    }

    report = {
        **baseline,
        "experiment": "2x_LANCZOS_input_resize",
        "baseline_report_sha256": hashlib.sha256(
            baseline_path.read_bytes()
        ).hexdigest(),
        "baseline_input_crop_sha256": baseline["crop_sha256"],
        "ocr_crop_scale": 2,
        "ocr_crop_size": [enlarged.width, enlarged.height],
        "polygon_coordinate_system": (
            "Pixels in the enlarged OCR crop"
        ),
        "crop_sha256": hashlib.sha256(
            image_path.read_bytes()
        ).hexdigest(),
        "inference_seconds": round(elapsed, 3),
        "recovered_count": recovered,
        "strict_name_coverage": recovered / len(results),
        "results": results,
        "detections": detections,
        "gained_names": sorted(after - before),
        "lost_names": sorted(before - after),
    }

    output = report_dir / "wall_table_ocr_cpu_2x.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"Baseline: {baseline['recovered_count']}/"
        f"{baseline['reference_count']} "
        f"({baseline['strict_name_coverage']:.1%})"
    )
    print(
        f"2x input: {recovered}/{len(results)} "
        f"({recovered / len(results):.1%})"
    )
    print(f"Inference time: {elapsed:.1f} seconds")
    print("Gained:", ", ".join(report["gained_names"]) or "(none)")
    print("Lost:", ", ".join(report["lost_names"]) or "(none)")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()