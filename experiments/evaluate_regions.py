import json
import re
from pathlib import Path


def normalize(text):
    """Ignore case and punctuation; collapse whitespace."""
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def edit_distance(reference, prediction):
    """Count the fewest insertions, deletions, and substitutions."""
    previous = list(range(len(prediction) + 1))

    for i, expected in enumerate(reference, start=1):
        current = [i]

        for j, actual in enumerate(prediction, start=1):
            current.append(
                min(
                    current[j - 1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (expected != actual),
                )
            )

        previous = current

    return previous[-1]


def main():
    folder = (
        Path(__file__).resolve().parents[1]
        / "data/processed/region_experiment"
    )

    # Reference text checked manually against the drawing.
    references = {
        "stucco_on_brick": "STUCCO ON BRICK",
        "iron_rail": "Iron Rail",
        "concrete_steps": "Concrete Steps",
    }

    results = []

    for name, expected in references.items():
        raw = (folder / f"{name}.txt").read_text(encoding="utf-8")

        reference = normalize(expected)
        prediction = normalize(raw)

        char_errors = edit_distance(reference, prediction)
        word_errors = edit_distance(
            reference.split(), prediction.split()
        )

        result = {
            "region": name,
            "reference": expected,
            "raw_prediction": raw.strip(),
            "normalized_prediction": prediction,
            "character_edits": char_errors,
            "reference_characters": len(reference),
            "word_edits": word_errors,
            "reference_words": len(reference.split()),
        }
        results.append(result)

        print(
            f"{name}: "
            f"CER {char_errors / len(reference):.1%}, "
            f"WER {word_errors / len(reference.split()):.1%}"
        )

    cer = (
        sum(r["character_edits"] for r in results)
        / sum(r["reference_characters"] for r in results)
    )
    wer = (
        sum(r["word_edits"] for r in results)
        / sum(r["reference_words"] for r in results)
    )

    report = {
        "scope": "Three manually selected development regions; PSM 11",
        "normalization": (
            "English lowercase letters/digits; punctuation removed; "
            "whitespace collapsed; spaces included in CER"
        ),
        "cer": cer,
        "wer": wer,
        "results": results,
    }

    (folder / "evaluation.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Combined: CER {cer:.1%}, WER {wer:.1%}")


if __name__ == "__main__":
    main()