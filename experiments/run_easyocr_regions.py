import json
from pathlib import Path

import easyocr
import torch

from experiments.evaluate_regions import edit_distance, normalize


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/processed/region_experiment"
MODELS = ROOT / ".models/easyocr"


def main():
    baseline = json.loads(
        (FOLDER / "evaluation.json").read_text(encoding="utf-8")
    )

    MODELS.mkdir(parents=True, exist_ok=True)

    print("Loading English OCR models...", flush=True)

    reader = easyocr.Reader(
        ["en"],
        gpu=False,
        model_storage_directory=str(MODELS),
        user_network_directory=str(MODELS / "user_network"),
    )

    results = []

    for sample in baseline["results"]:
        name = sample["region"]
        expected = sample["reference"]

        print(f"\nReading {name}...", flush=True)

        detections = reader.readtext(
            str(FOLDER / f"{name}.png"),
            detail=1,
            paragraph=False,
            workers=0,
            batch_size=1,
        )

        raw_prediction = " ".join(
            text for box, text, confidence in detections
        )

        reference = normalize(expected)
        prediction = normalize(raw_prediction)

        char_errors = edit_distance(reference, prediction)
        word_errors = edit_distance(
            reference.split(), prediction.split()
        )

        results.append({
            "region": name,
            "reference": expected,
            "raw_prediction": raw_prediction,
            "normalized_prediction": prediction,
            "character_edits": char_errors,
            "reference_characters": len(reference),
            "word_edits": word_errors,
            "reference_words": len(reference.split()),
            "detections": [
                {
                    "box": [
                        [float(x), float(y)] for x, y in box
                    ],
                    "text": text,
                    "confidence": float(confidence),
                }
                for box, text, confidence in detections
            ],
        })

        print(f"Reference: {expected}")
        print(f"EasyOCR:   {raw_prediction or '(no text detected)'}")
        print(
            f"CER {char_errors / len(reference):.1%}, "
            f"WER {word_errors / len(reference.split()):.1%}"
        )

    cer = (
        sum(item["character_edits"] for item in results)
        / sum(item["reference_characters"] for item in results)
    )
    wer = (
        sum(item["word_edits"] for item in results)
        / sum(item["reference_words"] for item in results)
    )

    report = {
        "scope": "Same three manually selected development crops",
        "engine": "EasyOCR",
        "easyocr_version": easyocr.__version__,
        "torch_version": torch.__version__,
        "languages": ["en"],
        "device": "cpu",
        "normalization": baseline["normalization"],
        "cer": cer,
        "wer": wer,
        "results": results,
    }

    destination = FOLDER / "easyocr_evaluation.json"
    destination.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nCombined recognition results:")
    print(
        f"Tesseract: CER {baseline['cer']:.1%}, "
        f"WER {baseline['wer']:.1%}"
    )
    print(f"EasyOCR:   CER {cer:.1%}, WER {wer:.1%}")
    print(f"Saved: {destination}")


if __name__ == "__main__":
    main()