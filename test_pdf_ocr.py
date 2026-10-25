import hashlib
import json
import unittest
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from PIL import Image

from pdf_candidates import build_pdf_candidates, match_pdf_candidate
from pdf_ocr import make_ocr_analysis, recognize_pdf_page, render_for_ocr
from pdf_processing import inspect_pdf_page
from pdf_review import pdf_review_key


ROOT = Path(__file__).resolve().parent
INFO = {"engine": "fake_test_reader", "languages": ["ja", "en"], "device": "cpu"}


def synthetic_pdf(resolution=150):
    buffer = BytesIO()
    Image.new("RGB", (1200, 800), "white").save(buffer, "PDF", resolution=resolution)
    return buffer.getvalue()


def predictions():
    texts = [
        "Item: S-001", "Product: モエンサイディング-M",
        "Manufacturer: Nichiha", "Manufacturemonth: 1995-08",
    ]
    return [
        ([[10, y], [350, y], [350, y + 20], [10, y + 20]], text, 0.9)
        for y, text in zip([20, 60, 100, 140], texts)
    ]


class PDFOCRTests(unittest.TestCase):
    def setUp(self):
        self.content = synthetic_pdf()
        self.native, _ = inspect_pdf_page(self.content, 1)
        self.raster = {
            "image_sha256": "f" * 64, "image_size_pixels": [1000, 500],
            "render_bbox_pdf_points": [10, 20, 510, 270],
        }

    def analysis(self, raw=None, elapsed=1):
        return make_ocr_analysis(
            self.native, self.raster, predictions() if raw is None else raw,
            INFO, elapsed,
        )

    def test_image_only_page_has_no_native_text_and_bounded_render(self):
        self.assertEqual(self.native["text"].strip(), "")
        png, raster = render_for_ocr(synthetic_pdf(resolution=10), 1)
        with Image.open(BytesIO(png)) as image:
            self.assertLessEqual(max(image.size), 1600)
            self.assertLessEqual(image.width * image.height, 1_500_000)
            self.assertEqual(list(image.size), raster["image_size_pixels"])
        self.assertEqual(hashlib.sha256(png).hexdigest(), raster["image_sha256"])

    def test_pixel_boxes_map_to_pdf_points_including_page_offset(self):
        result = self.analysis()
        detection = result["ocr"]["detections"][0]
        self.assertEqual(detection["polygon_pdf_points"][0], [15, 30])
        self.assertEqual(detection["polygon_pixels"][0], [10, 20])

    def test_ocr_evidence_reaches_candidate_and_matcher(self):
        catalogue = json.loads(
            (ROOT / "data/reference/manufacturer_records.json").read_bytes()
        )
        record = build_pdf_candidates(self.analysis())["candidates"][0]
        self.assertEqual(record["source"]["extraction_method"],
                         "ocr_labelled_block_rules")
        self.assertEqual(len(record["ocr_evidence"]["detections"]), 4)
        self.assertEqual(record["ocr_evidence"]["detections"][0]["confidence"], 0.9)
        self.assertEqual(match_pdf_candidate(record, catalogue)["decision"]["status"],
                         "non_asbestos_containing")

    def test_ocr_result_does_not_mutate_native_extraction(self):
        original = deepcopy(self.native)
        result = self.analysis()
        result["words"].append({"text": "Changed"})
        self.assertEqual(self.native, original)
        self.assertFalse(self.native["ocr_used"])
        self.assertEqual(result["tables"], [])

    def test_empty_ocr_does_not_create_material_entries(self):
        analysis = self.analysis(raw=[])
        self.assertEqual(analysis["text"], "")
        self.assertEqual(build_pdf_candidates(analysis)["candidates"], [])

    def test_changed_predictions_have_separate_review_history_keys(self):
        first = build_pdf_candidates(self.analysis())["candidates"][0]
        changed = predictions()
        polygon, _, confidence = changed[1]
        changed[1] = (polygon, "Product: モエンサイディング-N", confidence)
        second = build_pdf_candidates(self.analysis(raw=changed))["candidates"][0]
        self.assertNotEqual(pdf_review_key(first), pdf_review_key(second))
        self.assertEqual(self.analysis(elapsed=1)["ocr"]["result_sha256"],
                         self.analysis(elapsed=9)["ocr"]["result_sha256"])

    def test_recognition_uses_selected_page_and_rejects_mismatched_source(self):
        class FakeReader:
            def readtext(self, content, **settings):
                if not content.startswith(b"\x89PNG"):
                    raise AssertionError("Expected a rendered PNG.")
                return predictions()

        analysis = recognize_pdf_page(self.content, 1, self.native, FakeReader(), INFO)
        self.assertTrue(analysis["ocr_used"])
        self.assertEqual(len(analysis["ocr"]["detections"]), 4)
        wrong = {**self.native, "pdf_sha256": "wrong"}
        with self.assertRaises(ValueError):
            recognize_pdf_page(self.content, 1, wrong, FakeReader(), INFO)
        with self.assertRaises(ValueError):
            render_for_ocr(self.content, 2)


if __name__ == "__main__":
    unittest.main()
