import hashlib
import json
import platform
import time

from PIL import Image

from experiments.benchmark_reference_ocr import ROOT, evaluate_names


def main():
    import easyocr
    import torch

    torch.set_num_threads(2)

    report_dir = ROOT / "reports/reference_validation"
    gpu_path = report_dir / "table_validation_cuda.json"
    gpu_report = json.loads(
        gpu_path.read_text(encoding="utf-8")
    )

    reference = next(
        run for run in gpu_report["runs"]
        if run["group"] == "SOLIDO" and run["scale"] == 2
    )

    source = (
        ROOT / "reports/reference_extraction/evidence"
        / f"page_{reference['page']:03d}.png"
    )

    source_sha = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()

    if source_sha != reference["source_image_sha256"]:
        raise ValueError(
            "The source image differs from the GPU experiment."
        )

    folder = ROOT / "data/processed/solido_language"
    folder.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as page:
        crop = page.crop(
            reference["crop_box_in_page_pixels"]
        ).convert("RGB")

    crop = crop.resize(
        (crop.width * 2, crop.height * 2),
        Image.Resampling.LANCZOS,
    )

    image_path = folder / "solido_2x.png"
    crop.save(image_path)

    reference_names = [
        row["reference_name"]
        for row in reference["results"]
    ]
    runs = []

    for languages in [["ja", "en"], ["en"]]:
        print(f"\nLanguages: {languages}")

        reader = easyocr.Reader(
            languages,
            gpu=False,
            quantize=False,
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
                "id": index,
                "text": text,
                "confidence": float(confidence),
                "polygon_in_crop": [
                    [float(x), float(y)]
                    for x, y in polygon
                ],
            }
            for index, (polygon, text, confidence)
            in enumerate(predictions, start=1)
        ]

        results = evaluate_names(
            reference_names, detections
        )
        count = sum(row["recovered"] for row in results)

        for detection in detections:
            print(
                f"{detection['confidence']:.3f} | "
                f"{detection['text']}"
            )

        print(
            f"Strict name recovery: {count}/{len(results)}"
        )
        print(f"Inference time: {elapsed:.1f}s")

        runs.append({
            "languages": languages,
            "device": "cpu",
            "quantize": False,
            "reference_count": len(results),
            "recovered_count": count,
            "strict_name_coverage": count / len(results),
            "inference_seconds": round(elapsed, 3),
            "results": results,
            "detections": detections,
        })

        del reader

    report = {
        "data_kind": "solido_recognizer_language_comparison",
        "scope": "Two Latin series identifiers; development experiment",
        "reference_basis": "Native PDF extraction",
        "comparison": (
            "Language configurations within the same CPU environment"
        ),
        "metric": "Exact name recovery from individual OCR boxes",
        "normalization": (
            "NFKC, whitespace removed, casefold; punctuation retained"
        ),
        "parent_gpu_report_sha256": hashlib.sha256(
            gpu_path.read_bytes()
        ).hexdigest(),
        "source_image_sha256": reference["source_image_sha256"],
        "crop_box_in_page_pixels": (
            reference["crop_box_in_page_pixels"]
        ),
        "crop_sha256": hashlib.sha256(
            image_path.read_bytes()
        ).hexdigest(),
        "ocr_crop_scale": 2,
        "ocr_crop_size": [crop.width, crop.height],
        "easyocr_version": easyocr.__version__,
        "torch_version": str(torch.__version__),
        "python_version": platform.python_version(),
        "runs": runs,
    }

    output = report_dir / "solido_language_cpu.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {output}")


if __name__ == "__main__":
    main()