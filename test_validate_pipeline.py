import json
import unittest
from pathlib import Path

from validate_pipeline import SCENARIOS, score_case, summarise


ROOT = Path(__file__).resolve().parent


def make_case(index=1):
    expected = dict(SCENARIOS[index])
    date = (f"Manufacture month: {expected['manufacture_month']}"
            if expected["manufacture_month"] else "Installation year: 2001")
    text = (f"Data type: synthetic\nItem: {expected['id']}\n"
            f"Product: {expected['product_name']}\n"
            f"Manufacturer: {expected['manufacturer']}\n{date}")
    return {"case_id": "test", "condition": "clean", "expected": expected,
            "expected_text": text}


def text_analysis(text):
    return {"pdf_sha256": "fixture", "page_number": 1,
            "coordinate_system": "PDF points; top-left origin",
            "text": text, "tables": [], "ocr": {"inference_seconds": 1}}


class ValidationMetricTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = json.loads(
            (ROOT / "data/reference/manufacturer_records.json").read_bytes()
        )

    def score(self, case, text):
        return score_case(case, text_analysis(text), self.catalogue)

    def test_correct_fields_and_decision_receive_agreement(self):
        case = make_case()
        result = self.score(case, case["expected_text"])
        self.assertTrue(result["status_agreement"])
        self.assertTrue(result["reason_agreement"])
        self.assertEqual(result["cer"], 0)
        self.assertTrue(all(result["field_agreement_ignoring_spacing"].values()))

    def test_missing_item_cannot_count_as_correct_unresolved(self):
        result = self.score(make_case(2), "Data type: synthetic")
        self.assertEqual(result["extracted_items"], 0)
        self.assertIsNone(result["predicted_status"])
        self.assertFalse(result["status_agreement"])

    def test_unjustified_resolved_result_is_counted(self):
        case = make_case(2)
        text = case["expected_text"].replace("Installation year: 2001",
                                            "Manufacture month: 2001-09")
        result = self.score(case, text)
        self.assertTrue(result["incorrect_resolved_decision"])
        self.assertFalse(result["reason_agreement"])

    def test_item_id_errors_are_separate_from_material_decisions(self):
        case = make_case()
        result = self.score(case, case["expected_text"].replace("V-102", "V-IO2"))
        self.assertFalse(result["item_id_agreement"])
        self.assertTrue(result["status_agreement"])

    def test_japanese_character_errors_are_included_in_cer(self):
        case = make_case(0)
        result = self.score(case, case["expected_text"].replace("ゴールデン", "ゴルデン"))
        self.assertGreater(result["cer_edits"], 0)
        self.assertGreater(result["cer"], 0)

    def test_summary_weights_cer_by_characters_and_keeps_execution_failures(self):
        short = make_case()
        long = make_case(0)
        rows = [self.score(short, short["expected_text"]),
                self.score(long, long["expected_text"].replace("ゴールデン", "ゴルデン")),
                score_case(short, None, self.catalogue)]
        result = summarise(rows)
        self.assertEqual(result["cases"], 3)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["cer_over_completed_runs"],
                         sum(r["cer_edits"] for r in rows[:2]) /
                         sum(r["reference_characters"] for r in rows[:2]))
        self.assertLess(result["status_agreement_count"], result["cases"])


if __name__ == "__main__":
    unittest.main()
