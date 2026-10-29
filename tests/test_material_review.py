"""Synthetic spelling variations for checking suggestion safeguards."""

import json
import unittest
from pathlib import Path

from material_review import review_material


class MaterialReviewTests(unittest.TestCase):
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
            "product_name": "モエンサイディング-N",
            "manufacturer": "Nichiha",
            "manufacture_month": "1995-08",
            **changes,
        }

    def test_similar_name_stays_unresolved(self):
        result = review_material(
            self.make_query(),
            self.catalogue,
        )

        self.assertEqual(
            result["decision"]["status"], "unresolved"
        )
        self.assertIsNone(
            result["decision"]["matched_record_id"]
        )
        self.assertEqual(
            result["suggestions"][0]["record_id"],
            "nichiha-moen-m",
        )
        self.assertTrue(
            result["suggestions"][0]["requires_review"]
        )
        self.assertNotIn(
            "reference_status",
            result["suggestions"][0],
        )

    def test_manufacturer_filter(self):
        result = review_material(
            self.make_query(manufacturer="Example Maker"),
            self.catalogue,
        )

        self.assertEqual(
            result["decision"]["status"], "unresolved"
        )
        self.assertEqual(result["suggestions"], [])

    def test_exact_match_keeps_original_decision(self):
        result = review_material(
            self.make_query(
                product_name="モエンサイディング-M"
            ),
            self.catalogue,
        )

        self.assertEqual(
            result["decision"]["status"],
            "non_asbestos_containing",
        )
        self.assertEqual(result["suggestions"], [])


if __name__ == "__main__":
    unittest.main()