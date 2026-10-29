import json
import unittest
from copy import deepcopy
from pathlib import Path

from pdf_candidates import build_pdf_candidates, match_pdf_candidate


ROOT = Path(__file__).resolve().parents[1]


def page(text="", tables=None, fingerprint="a" * 64):
    return {
        "page_number": 1,
        "pdf_sha256": fingerprint,
        "coordinate_system": "PDF points; top-left origin",
        "text": text,
        "tables": tables or [],
    }


class PDFCandidateTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = json.loads(
            (ROOT / "data/reference/manufacturer_records.json").read_text(
                encoding="utf-8"
            )
        )

    def test_labelled_fields_reach_matcher_with_original_evidence(self):
        text = (
            "Item: A\nProduct: モエンサイディング-M\n"
            "Manufacturer: Nichiha\nManufacturemonth: 1995-08\n"
        )
        record = build_pdf_candidates(page(text))["candidates"][0]
        result = match_pdf_candidate(record, self.catalogue)
        self.assertEqual(result["decision"]["status"], "non_asbestos_containing")
        self.assertEqual(record["source_lines"][-1]["text"],
                         "Manufacturemonth: 1995-08")
        self.assertEqual(record["source"]["pdf_sha256"], "a" * 64)

    def test_table_names_do_not_inherit_manufacturer_or_sales_date(self):
        analysis = page("KMEW\nSales from 2003-12", [{
            "bbox_pdf_points": [10, 20, 100, 90],
            "rows": [
                ["シリーズ名", "商品板厚(㎜)", "商品名", "塗装種類", "塗装色"],
                ["レジェール", "21", "全て", "全て", "全て"],
            ],
        }])
        original = deepcopy(analysis)
        record = build_pdf_candidates(analysis)["candidates"][0]
        self.assertIsNone(record["query"]["manufacturer"])
        self.assertIsNone(record["query"]["manufacture_month"])
        self.assertEqual(record["table_evidence"]["raw_cells"],
                         analysis["tables"][0]["rows"][1])
        record["table_evidence"]["raw_cells"][0] = "Changed locally"
        self.assertEqual(analysis, original)

    def test_unknown_tables_are_reported_without_guessed_names(self):
        result = build_pdf_candidates(page(tables=[{
            "bbox_pdf_points": [0, 0, 50, 50],
            "rows": [["Unknown layout"], ["Board"]],
        }]))
        self.assertEqual(result["candidates"], [])
        self.assertEqual(len(result["skipped_tables"]), 1)

    def test_conflicting_fields_block_automatic_matching(self):
        text = (
            "Item: A\nProduct: モエンサイディング-M\n"
            "Manufacturer: Nichiha\nManufacture month: 1995-08\n"
            "Manufacturemonth: 1978-06\n"
        )
        record = build_pdf_candidates(page(text))["candidates"][0]
        result = match_pdf_candidate(record, self.catalogue)
        self.assertEqual(result["decision"]["status"], "unresolved")
        self.assertEqual(result["decision"]["reason"],
                         "conflicting_extracted_fields")


if __name__ == "__main__":
    unittest.main()
