import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pdfplumber


ROOT = Path(__file__).resolve().parent
URL = "https://www.kmew.co.jp/kenkai/syoumeisyo.php"


def main():
    pdf_path = ROOT / "data/raw/kmew_reference.pdf"
    metadata_path = ROOT / "data/metadata/kmew_reference_source.json"
    output_dir = ROOT / "data/processed/kmew_reference"

    for directory in [
        pdf_path.parent,
        metadata_path.parent,
        output_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    retrieved_at = None

    if pdf_path.exists():
        print("Using the saved PDF snapshot.")

        if metadata_path.exists():
            previous = json.loads(
                metadata_path.read_text(encoding="utf-8")
            )
            retrieved_at = previous.get("retrieved_at_utc")
    else:
        print("Downloading the manufacturer PDF...")

        request = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=60) as response:
            content = response.read()

        if not content.startswith(b"%PDF-"):
            raise ValueError(
                "The server returned something other than a PDF."
            )

        pdf_path.write_bytes(content)
        retrieved_at = datetime.now(timezone.utc).isoformat()

    metadata = {
        "data_kind": "real_manufacturer_reference_document",
        "source_url": URL,
        "retrieved_at_utc": retrieved_at,
        "pdf_sha256": hashlib.sha256(
            pdf_path.read_bytes()
        ).hexdigest(),
        "pdfplumber_version": pdfplumber.__version__,
    }

    if metadata_path.exists():
        previous = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
        if previous["pdf_sha256"] != metadata["pdf_sha256"]:
            raise ValueError(
                "The PDF differs from its saved source metadata."
            )

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pages = []

    with pdfplumber.open(pdf_path) as document:
        print(f"PDF pages: {len(document.pages)}")

        for number, page in enumerate(document.pages, start=1):
            text = page.extract_text(
                x_tolerance=2,
                y_tolerance=3,
            ) or ""

            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=3,
            )

            tables = [
                {
                    "bbox_pdf_points": list(table.bbox),
                    "rows": table.extract(),
                }
                for table in page.find_tables()
            ]

            prefix = f"page_{number:03d}"

            (output_dir / f"{prefix}.txt").write_text(
                text,
                encoding="utf-8",
            )

            preview = page.to_image(resolution=150)
            preview.save(output_dir / f"{prefix}.png")

            pages.append({
                "page_number": number,
                "width_pdf_points": page.width,
                "height_pdf_points": page.height,
                "text": text,
                "words": words,
                "table_candidates": tables,
            })

            print(f"Page {number}:")
            print(f"  Extracted characters: {len(text)}")
            print(f"  Word boxes: {len(words)}")
            print(f"  Table candidates: {len(tables)}")
            print("  Text preview:")
            print("\n".join(text.splitlines()[:8]))

    report = {
        **metadata,
        "extraction_method": "native_pdf_text_and_line_based_tables",
        "ocr_used": False,
        "coordinate_system": "PDF points; top-left origin",
        "pages": pages,
    }

    path = output_dir / "inspection.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved inspection: {path}")
    print(f"Saved page previews in: {output_dir}")


if __name__ == "__main__":
    main()