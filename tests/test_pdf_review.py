import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from pdf_review import pdf_review_key, save_pdf_review
from review_history import load_history


ROOT = Path(__file__).resolve().parents[1]


class PDFReviewTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "reviews.sqlite3"
        self.catalogue = (
            ROOT / "data/reference/manufacturer_records.json"
        ).read_bytes()
        self.record = {
            "query": {
                "query_id": "pdf-p1-item1",
                "product_name": "モエンサイディング-N",
                "manufacturer": None,
                "manufacture_month": None,
            },
            "source": {
                "pdf_sha256": "a" * 64, "page_number": 1,
                "extraction_method": "labelled_block_rules",
            },
            "source_lines": [{"line": 1, "text": "Synthetic fixture"}],
            "issues": [],
            "decision": {"status": "unresolved"},
        }
        self.fields = {
            "product_name": "モエンサイディング-M",
            "manufacturer": "Nichiha",
            "manufacture_month": "1995-08",
        }

    def save(self, **changes):
        arguments = {
            "path": self.path, "record": self.record,
            "catalogue_bytes": self.catalogue, "fields": self.fields,
            "reviewer": "Test reviewer", "note": "Synthetic fixture correction.",
            "review_kind": "synthetic_test",
            "document_context": {"document_origin": "synthetic_fixture"},
        }
        arguments.update(changes)
        return save_pdf_review(**arguments)

    def test_corrected_query_is_saved_without_changing_original(self):
        original = deepcopy(self.record)
        event = self.save()
        self.assertEqual(self.record, original)
        self.assertEqual(event["original_record"], original)
        self.assertEqual(event["review_result"]["decision"]["status"],
                         "non_asbestos_containing")
        self.assertEqual(event["review_kind"], "synthetic_test")
        self.assertEqual(load_history(self.path, pdf_review_key(self.record)),
                         [event])

    def test_histories_are_separated_by_document_page_and_entry(self):
        self.save()
        for section, field, value in [
            ("source", "pdf_sha256", "b" * 64),
            ("source", "page_number", 2),
            ("query", "query_id", "pdf-p1-item2"),
        ]:
            other = deepcopy(self.record)
            other[section][field] = value
            self.assertNotEqual(pdf_review_key(other), pdf_review_key(self.record))
            self.assertEqual(load_history(self.path, pdf_review_key(other)), [])

    def test_invalid_submission_does_not_append_to_history(self):
        event = self.save()
        for change in [
            {"reviewer": " "}, {"note": ""},
            {"fields": {**self.fields, "product_name": " "}},
            {"review_kind": "unsupported"},
        ]:
            with self.assertRaises(ValueError):
                self.save(**change)
        self.assertEqual(load_history(self.path, pdf_review_key(self.record)),
                         [event])

    def test_missing_month_remains_unresolved_after_review(self):
        event = self.save(fields={**self.fields, "manufacture_month": " "})
        self.assertIsNone(event["reviewed_query"]["manufacture_month"])
        self.assertEqual(event["review_result"]["decision"]["status"], "unresolved")
        self.assertEqual(event["review_result"]["decision"]["reason"],
                         "manufacture_month_missing")


if __name__ == "__main__":
    unittest.main()
