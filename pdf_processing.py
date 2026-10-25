import hashlib
from io import BytesIO

import pdfplumber


MAX_PDF_BYTES = 20 * 1024 * 1024


def validate_pdf_bytes(content):
    if not content or len(content) > MAX_PDF_BYTES:
        raise ValueError(
            "Choose a nonempty PDF smaller than 20 MB."
        )

    if b"%PDF-" not in content[:1024]:
        raise ValueError(
            "The selected file does not have a PDF header."
        )


def pdf_page_count(content):
    validate_pdf_bytes(content)

    with pdfplumber.open(BytesIO(content)) as document:
        return len(document.pages)


def inspect_pdf_page(content, page_number):
    validate_pdf_bytes(content)

    with pdfplumber.open(BytesIO(content)) as document:
        total = len(document.pages)

        if not 1 <= page_number <= total:
            raise ValueError(
                "The selected page is outside this PDF."
            )

        page = document.pages[page_number - 1]

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

        resolution = min(
            150,
            1800 * 72 / max(page.width, page.height),
        )

        preview = page.to_image(resolution=resolution)
        buffer = BytesIO()
        preview.save(buffer, format="PNG")

        analysis = {
            "pdf_sha256": hashlib.sha256(content).hexdigest(),
            "page_number": page_number,
            "page_count": total,
            "extraction_method": "native_pdf",
            "ocr_used": False,
            "pdfplumber_version": pdfplumber.__version__,
            "coordinate_system": "PDF points; top-left origin",
            "page_size_pdf_points": [
                page.width, page.height
            ],
            "text": text,
            "words": words,
            "tables": tables,
        }

    return analysis, buffer.getvalue()