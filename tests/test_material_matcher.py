"""Synthetic queries against our manufacturer reference records."""

import copy
import json
import unittest
from pathlib import Path

from material_matcher import match_material


class MaterialMatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = (
            Path(__file__).resolve().parents[1]
            / "data/reference/manufacturer_records.json"
        )
        cls.catalogue = json.loads(
            path.read_text(encoding="utf-8")
        )

    def make_query(self, **changes):
        return {
            "product_name": "モエンサイディング-M",
            "manufacturer": "Nichiha",
            "manufacture_month": "1995-08",
            **changes,
        }

    def test_reference_decisions(self):
        golden = "ゴールデン モエンサイディング"

        cases = [
            ("non_containing", {}, "non_asbestos_containing"),

            ("containing", {
                "product_name": golden,
                "manufacture_month": "1978-06",
            }, "asbestos_containing"),

            ("width_and_case", {
                "product_name": "モエンサイディング－Ｍ",
                "manufacturer": "  ＮＩＣＨＩＨＡ  ",
            }, "non_asbestos_containing"),

            ("last_valid_month", {
                "product_name": golden,
                "manufacture_month": "1981-04",
            }, "asbestos_containing"),

            ("first_invalid_month", {
                "product_name": golden,
                "manufacture_month": "1981-05",
            }, "unresolved"),

            ("generic_material", {
                "product_name": "stucco",
            }, "unresolved"),

            ("spelling_error", {
                "product_name": "モエンサイディング-N",
            }, "unresolved"),

            ("missing_manufacturer", {
                "manufacturer": None,
            }, "unresolved"),

            ("wrong_manufacturer", {
                "manufacturer": "Example Maker",
            }, "unresolved"),

            ("missing_month", {
                "manufacture_month": None,
            }, "unresolved"),

            ("year_only", {
                "manufacture_month": "1981",
            }, "unresolved"),

            ("invalid_month", {
                "manufacture_month": "1995-13",
            }, "unresolved"),

            ("future_month", {
                "manufacture_month": "2027-01",
            }, "unresolved"),

            ("unverified_code", {
                "product_code": "DEMO-X",
            }, "unresolved"),
        ]

        for name, changes, expected in cases:
            with self.subTest(case=name):
                result = match_material(
                    self.make_query(**changes),
                    self.catalogue,
                )

                self.assertEqual(result["status"], expected)

                if expected == "unresolved":
                    self.assertIsNone(result["matched_record_id"])
                    self.assertEqual(result["source_urls"], [])
                else:
                    self.assertTrue(result["matched_record_id"])
                    self.assertTrue(result["source_urls"])

    def test_conflicting_records_remain_unresolved(self):
        catalogue = copy.deepcopy(self.catalogue)

        # Deliberately conflicting test fixture, not a real claim.
        conflict = copy.deepcopy(catalogue["records"][1])
        conflict["record_id"] = "synthetic-conflict"
        conflict["reference_status"] = "asbestos_containing"
        catalogue["records"].append(conflict)

        result = match_material(self.make_query(), catalogue)

        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["reason"], "ambiguous_reference")


if __name__ == "__main__":
    unittest.main()