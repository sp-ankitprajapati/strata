import copy
import tempfile
import unittest
from pathlib import Path

from review_history import load_history, save_review


class ReviewHistoryTests(unittest.TestCase):
    def test_reviews_persist_and_stay_with_their_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.sqlite3"
            details = {
                "original_query": {"product_name": "STUCCO"},
                "reviewer": "Ankit",
            }
            before = copy.deepcopy(details)

            self.assertEqual(load_history(path, "drawing"), [])

            first = save_review(path, "drawing", details)
            second = save_review(path, "drawing", details)
            save_review(path, "demo", {"reviewer": "Test"})

            self.assertEqual(load_history(path, "drawing"), [first, second])
            self.assertEqual(len(load_history(path, "demo")), 1)
            self.assertNotEqual(first["review_id"], second["review_id"])
            self.assertEqual(details, before)

    def test_invalid_payload_does_not_append_a_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.sqlite3"
            first = save_review(path, "drawing", {"reviewer": "Ankit"})

            with self.assertRaises(TypeError):
                save_review(path, "drawing", {"invalid": object()})

            self.assertEqual(load_history(path, "drawing"), [first])


if __name__ == "__main__":
    unittest.main()