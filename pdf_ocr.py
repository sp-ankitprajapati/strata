"""Render one PDF page and preserve OCR text, geometry and provenance."""

import hashlib
import json
import math
import time
from copy import deepcopy
from io import BytesIO

import pdfplumber
from PIL import Image

from evaluate_schedule_ocr import reconstruct_lines
from pdf_processing import validate_pdf_bytes


OCR_SETTINGS = {
    "detail": 1, "paragraph": False, "batch_size": 1, "workers": 0,
    "canvas_size": 1600,
}
MAX_SIDE = 1600
MAX_PIXELS = 1_500_000


def render_for_ocr(content, page_number):
    validate_pdf_bytes(content)
    with pdfplumber.open(BytesIO(content)) as document:
        if not 1 <= page_number <= len(document.pages):
            raise ValueError("The selected page is outside this PDF.")
        page = document.pages[page_number - 1]
        resolution = min(
            150, MAX_SIDE * 72 / max(page.width, page.height),
            72 * math.sqrt(MAX_PIXELS / (page.width * page.height)),
        )
        rendered = page.to_image(resolution=resolution, antialias=True)
        image = rendered.original.convert("RGB")
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        if image.width * image.height > MAX_PIXELS:
            scale = math.sqrt(MAX_PIXELS / (image.width * image.height))
            image = image.resize(
                (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        png = buffer.getvalue()
        metadata = {
            "image_sha256": hashlib.sha256(png).hexdigest(),
            "image_size_pixels": list(image.size),
            "render_bbox_pdf_points": list(rendered.bbox),
            "requested_resolution_dpi": resolution,
        }
    return png, metadata


def make_ocr_analysis(native, raster, predictions, engine_info, elapsed):
    width, height = raster["image_size_pixels"]
    x0, top, x1, bottom = raster["render_bbox_pdf_points"]
    detections = []
    for number, (polygon, text, confidence) in enumerate(predictions, 1):
        pixels = [[float(x), float(y)] for x, y in polygon]
        score = float(confidence)
        if not all(math.isfinite(v) for point in pixels for v in point):
            raise ValueError("OCR returned invalid coordinates.")
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("OCR returned invalid confidence.")
        detections.append({
            "id": number, "text": str(text), "confidence": score,
            "confidence_scale": "0 to 1; OCR engine score",
            "polygon_pixels": pixels,
            "polygon_pdf_points": [
                [x0 + x / width * (x1 - x0), top + y / height * (bottom - top)]
                for x, y in pixels
            ],
        })

    lines = reconstruct_lines([
        {"id": d["id"], "text": d["text"], "polygon": d["polygon_pixels"]}
        for d in detections
    ])
    evidence = {
        "engine_info": deepcopy(engine_info), "settings": dict(OCR_SETTINGS),
        "raster": deepcopy(raster), "detections": detections,
    }
    result_sha = hashlib.sha256(json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode("utf-8")).hexdigest()
    return {
        **deepcopy(native),
        "extraction_method": "easyocr", "ocr_used": True,
        "text": "\n".join(line["text"] for line in lines),
        "words": [], "tables": [],
        "ocr": {
            **evidence, "lines": lines, "result_sha256": result_sha,
            "inference_seconds": round(elapsed, 3),
            "layout_scope": "labelled item blocks; scanned tables not reconstructed",
        },
    }


def recognize_pdf_page(content, page_number, native, reader, engine_info):
    if (native["pdf_sha256"] != hashlib.sha256(content).hexdigest()
            or native["page_number"] != page_number):
        raise ValueError("Native extraction and OCR must refer to the same page.")
    png, raster = render_for_ocr(content, page_number)
    start = time.perf_counter()
    predictions = reader.readtext(png, **OCR_SETTINGS)
    elapsed = time.perf_counter() - start
    return make_ocr_analysis(native, raster, predictions, engine_info, elapsed)
