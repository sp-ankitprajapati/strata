import unittest

from experiments.benchmark_reference_ocr import evaluate_names


class ReferenceOCRTests(unittest.TestCase):
    def test_longer_name_does_not_count_as_shorter_name(self):
        result = evaluate_names(
            ["セラディール14"],
            [{"id": 1, "text": "セラディール14広幅"}],
        )

        self.assertFalse(result[0]["recovered"])

    def test_unicode_case_and_spacing_normalization(self):
        result = evaluate_names(
            ["ＬＡＰ-ＷＡＬＬ"],
            [{"id": 1, "text": "lap - wall"}],
        )

        self.assertTrue(result[0]["recovered"])

    def test_duplicate_detections_do_not_inflate_recovery(self):
        result = evaluate_names(
            ["レジェール"],
            [
                {"id": 1, "text": "レジェール"},
                {"id": 2, "text": "レジェール"},
            ],
        )

        self.assertEqual(
            sum(row["recovered"] for row in result), 1
        )
        self.assertEqual(
            result[0]["matched_detection_ids"], [1, 2]
        )


if __name__ == "__main__":
    unittest.main()