import argparse
import hashlib
import json
import math
import platform
import subprocess
import time
from pathlib import Path

from PIL import Image

from experiments.benchmark_reference_ocr import ROOT, evaluate_names
from extract_reference_candidates import parse_table


OUTPUT = (
    ROOT / "reports/reference_validation/table_validation_cuda.json"
)
CHECKPOINT = "strata_reference_validation_v1"


def restore_notebook(path):
    notebook = json.loads(
        Path(path).read_text(encoding="utf-8")
    )
    report = None

    for cell in notebook.get("cells", []):
        for output in cell.get("outputs", []):
            payload = output.get("data", {}).get("application/json")

            if isinstance(payload, str):
                payload = json.loads(payload)

            if isinstance(payload, dict) and CHECKPOINT in payload:
                report = payload[CHECKPOINT]

    expected = {
        ("roof", 1), ("roof", 2),
        ("SOLIDO", 1), ("SOLIDO", 2),
    }

    if (
        not isinstance(report, dict)
        or report.get("device") != "cuda"
        or len(report.get("runs", [])) != 4
        or {
            (run["group"], run["scale"])
            for run in report["runs"]
        } != expected
    ):
        raise ValueError(
            "No complete GPU validation checkpoint found."
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Restored: {OUTPUT}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-notebook")
    args = parser.parse_args()

    if args.restore_notebook:
        restore_notebook(args.restore_notebook)
        return

    import easyocr
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError(
            "Select a Kaggle GPU kernel before running this script."
        )

    evidence = ROOT / "reports/reference_extraction/evidence"
    inspection_path = evidence / "inspection.json"
    inspection = json.loads(
        inspection_path.read_text(encoding="utf-8")
    )

    targets = []

    for page in inspection["pages"]:
        for table_number, table in enumerate(
            page["table_candidates"], start=1
        ):
            names, _ = parse_table(table["rows"])

            if names and names[0]["group"] in {"roof", "SOLIDO"}:
                targets.append(
                    (page, table_number, table, names)
                )

    if len(targets) != 2:
        raise ValueError(
            "Expected one roofing table and one SOLIDO table."
        )

    folder = ROOT / "data/processed/reference_validation"
    folder.mkdir(parents=True, exist_ok=True)

    reader = easyocr.Reader(
        ["ja", "en"],
        gpu="cuda:0",
        quantize=False,
        model_storage_directory=str(ROOT / ".models/easyocr"),
    )

    settings = {
        "detail": 1,
        "paragraph": False,
        "batch_size": 1,
        "workers": 0,
    }
    runs = []

    for page, table_number, table, names in targets:
        group = names[0]["group"]
        source_image = (
            evidence / f"page_{page['page_number']:03d}.png"
        )

        with Image.open(source_image) as image:
            sx = image.width / page["width_pdf_points"]
            sy = image.height / page["height_pdf_points"]
            x1, y1, x2, y2 = table["bbox_pdf_points"]

            box = [
                max(0, math.floor(x1 * sx) - 8),
                max(0, math.floor(y1 * sy) - 8),
                min(image.width, math.ceil(x2 * sx) + 8),
                min(image.height, math.ceil(y2 * sy) + 8),
            ]
            original = image.crop(box).convert("RGB")

        for scale in [1, 2]:
            crop = (
                original
                if scale == 1
                else original.resize(
                    (original.width * 2, original.height * 2),
                    Image.Resampling.LANCZOS,
                )
            )

            image_path = folder / f"{group}_{scale}x.png"
            crop.save(image_path)

            # Warm up before measuring inference.
            reader.readtext(str(image_path), **settings)
            torch.cuda.synchronize()

            started = time.perf_counter()
            predictions = reader.readtext(
                str(image_path), **settings
            )
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - started

            detections = [
                {
                    "id": index,
                    "text": text,
                    "confidence": float(confidence),
                    "polygon_in_resized_crop": [
                        [float(x), float(y)]
                        for x, y in polygon
                    ],
                }
                for index, (polygon, text, confidence)
                in enumerate(predictions, start=1)
            ]

            results = evaluate_names(
                [name["name"] for name in names],
                detections,
            )
            count = sum(row["recovered"] for row in results)

            runs.append({
                "group": group,
                "scale": scale,
                "page": page["page_number"],
                "table": table_number,
                "crop_box_in_page_pixels": box,
                "ocr_crop_size": [crop.width, crop.height],
                "crop_sha256": hashlib.sha256(
                    image_path.read_bytes()
                ).hexdigest(),
                "source_image_sha256": hashlib.sha256(
                    source_image.read_bytes()
                ).hexdigest(),
                "reference_count": len(results),
                "recovered_count": count,
                "strict_name_coverage": count / len(results),
                "inference_seconds": round(elapsed, 3),
                "results": results,
                "detections": detections,
            })

            print(
                f"{group} {scale}x: {count}/{len(results)} "
                f"({count / len(results):.1%}), "
                f"{elapsed:.2f}s"
            )

    report = {
        "data_kind": "same_document_additional_table_validation",
        "scope": (
            "Two additional tables from the same PDF; "
            "not independent documents"
        ),
        "reference_basis": "Native PDF extraction",
        "metric": "Exact name recovery from individual OCR boxes",
        "normalization": (
            "NFKC, whitespace removed, casefold; punctuation retained"
        ),
        "source_pdf_sha256": inspection["pdf_sha256"],
        "inspection_sha256": hashlib.sha256(
            inspection_path.read_bytes()
        ).hexdigest(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip(),
        "device": "cuda",
        "gpu": torch.cuda.get_device_name(0),
        "python_version": platform.python_version(),
        "easyocr_version": easyocr.__version__,
        "torch_version": str(torch.__version__),
        "cuda_build": torch.version.cuda,
        "languages": ["ja", "en"],
        "quantize": False,
        "readtext_settings": settings,
        "timing": (
            "One untimed warm-up per image; "
            "CUDA synchronized around timing"
        ),
        "runs": runs,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()