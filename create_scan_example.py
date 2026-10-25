"""Wrap the existing synthetic schedule image in an image-only PDF."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / "reports/schedule_extraction/evidence/schedule_clean.png"
    output = ROOT / "data/raw/synthetic_schedule_scan.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.convert("RGB").save(
            output, "PDF", resolution=150.0,
            title="Strata synthetic schedule scan",
        )
    print("Data type: synthetic; PDF contains a raster image, not selectable text.")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
