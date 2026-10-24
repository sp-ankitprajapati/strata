import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "easyocr_tiled_cuda.json",
    "easyocr_material_candidates_cuda.json",
}


def extract_checkpoint(notebook):
    checkpoints = []

    for cell in notebook.get("cells", []):
        for output in cell.get("outputs", []):
            payload = output.get("data", {}).get(
                "application/json"
            )

            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    continue

            if (
                isinstance(payload, dict)
                and payload.get("strata_checkpoint_version") == 1
            ):
                checkpoints.append(payload)

    if not checkpoints:
        raise ValueError(
            "No checkpoint found. Run the checkpoint cell "
            "and save the VS Code notebook first."
        )

    files = checkpoints[-1].get("files", {})

    if set(files) != EXPECTED:
        raise ValueError("Unexpected checkpoint files.")

    return files


def main():
    notebook = json.loads(
        (ROOT / "kaggle_gpu.ipynb").read_text(encoding="utf-8")
    )
    files = extract_checkpoint(notebook)

    destination = ROOT / "data/processed"
    destination.mkdir(parents=True, exist_ok=True)

    for name in sorted(EXPECTED):
        (destination / name).write_text(
            json.dumps(files[name], indent=2),
            encoding="utf-8",
        )
        print(f"Restored: {name}")

    print(
        "Text detections:",
        len(files["easyocr_tiled_cuda.json"]["detections"]),
    )
    print(
        "Material-bearing boxes:",
        len(
            files["easyocr_material_candidates_cuda.json"][
                "candidates"
            ]
        ),
    )


if __name__ == "__main__":
    main()