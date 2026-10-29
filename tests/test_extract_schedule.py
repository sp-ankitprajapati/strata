import unittest

from extract_schedule import extract_schedule


class ScheduleExtractionTests(unittest.TestCase):
    def test_extracts_fields_and_preserves_evidence(self):
        text = (
            "Item: A\n"
            "Product: モエンサイディング-M\n"
            "Manufacturer: Nichiha\n"
            "Manufacture month: 1995-08\n"
        )
        record = extract_schedule(text)[0]

        self.assertEqual(
            record["query"]["product_name"],
            "モエンサイディング-M",
        )
        self.assertEqual(record["query"]["manufacturer"], "Nichiha")
        self.assertEqual(record["query"]["manufacture_month"], "1995-08")
        self.assertEqual(
            record["field_evidence"]["product_name"][0]["line"], 2
        )

    def test_installation_year_is_not_a_manufacturing_date(self):
        record = extract_schedule(
            "Item: A\nProduct: Board\nInstallation year: 1995\n"
        )[0]

        self.assertIsNone(record["query"]["manufacture_month"])

    def test_duplicate_fields_are_flagged(self):
        record = extract_schedule(
            "Item: A\nManufacturer: Nichiha\nManufacturer: Other\n"
        )[0]

        self.assertIsNone(record["query"]["manufacturer"])
        self.assertEqual(record["issues"], ["manufacturer"])

    def test_fields_do_not_leak_between_items(self):
        records = extract_schedule(
            "Item: A\nManufacturer: Nichiha\nItem: B\nProduct: Board\n"
        )

        self.assertIsNone(records[1]["query"]["manufacturer"])

    def test_compact_labels_preserve_values_and_original_text(self):
        text = (
            "ITEM:S-OO2\n"
            "PRODUCT: モエンサイディング-M\n"
            "MANUFACTURER: Nichiha\n"
            "Manufacturemonth:1995-08\n"
        )
        record = extract_schedule(text)[0]

        self.assertEqual(record["item_label"], "S-OO2")
        self.assertEqual(
            record["query"]["product_name"],
            "モエンサイディング-M",
        )
        self.assertEqual(record["query"]["manufacturer"], "Nichiha")
        self.assertEqual(record["query"]["manufacture_month"], "1995-08")
        self.assertEqual(
            record["source_lines"][3]["text"],
            "Manufacturemonth:1995-08",
        )

    def test_normalized_duplicate_labels_are_still_flagged(self):
        record = extract_schedule(
            "Item:A\n"
            "Manufacture month:1978-06\n"
            "Manufacturemonth:1995-08\n"
        )[0]

        self.assertIsNone(record["query"]["manufacture_month"])
        self.assertEqual(record["issues"], ["manufacture_month"])

    def test_other_date_labels_are_not_guessed(self):
        record = extract_schedule(
            "Item:A\n"
            "Installationyear:1995\n"
            "Manufactureyear:1995\n"
        )[0]

        self.assertIsNone(record["query"]["manufacture_month"])


if __name__ == "__main__":
    unittest.main()