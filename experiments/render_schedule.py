import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]

FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
)
LICENSE_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/notosansjp/OFL.txt"
)


def download(url, path):
    if path.exists():
        return

    request = Request(
        url,
        headers={"User-Agent": "Strata-learning-project"},
    )
    with urlopen(request, timeout=90) as response:
        content = response.read()

    path.write_bytes(content)


def main():
    source_path = ROOT / "examples/synthetic_schedule.txt"
    source = source_path.read_text(encoding="utf-8")

    if not source.startswith("Data type: synthetic\n"):
        raise ValueError("Expected a clearly labelled synthetic schedule.")

    font_dir = ROOT / "data/raw/fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    font_path = font_dir / "NotoSansJP.ttf"

    print("Preparing the Japanese font...")
    download(FONT_URL, font_path)
    download(LICENSE_URL, font_dir / "OFL.txt")

    font = ImageFont.truetype(str(font_path), size=36)
    font.set_variation_by_axes([400])

    lines = source.splitlines()
    margin, line_height = 60, 60

    width = max(
        1400,
        int(max(font.getlength(line) for line in lines)) + 2 * margin,
    )
    height = 2 * margin + len(lines) * line_height

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    ground_truth = []

    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        position = (margin, margin + (number - 1) * line_height)

        draw.text(
            position,
            line,
            font=font,
            fill="black",
            anchor="lt",
        )

        ground_truth.append({
            "source_line": number,
            "text": line,
            "box": list(
                draw.textbbox(position, line, font=font, anchor="lt")
            ),
        })

    output_dir = ROOT / "data/processed/synthetic_schedule"
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path = output_dir / "schedule_clean.png"
    image.save(image_path)

    metadata = {
        "data_kind": "synthetic_schedule_image",
        "source_file": source_path.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        "image_size": [width, height],
        "font_url": FONT_URL,
        "font_license_url": LICENSE_URL,
        "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
        "font_size": 36,
        "font_weight": 400,
        "lines": ground_truth,
    }

    (output_dir / "ground_truth.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Image size: {width} x {height}")
    print(f"Ground-truth text lines: {len(ground_truth)}")
    print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()