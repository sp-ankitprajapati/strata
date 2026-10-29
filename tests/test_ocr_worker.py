import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from ocr_worker import run_isolated_ocr


CONTENT = b"%PDF-1.4\nMocked subprocess input; not parsed in these launcher tests.\n"


class OCRWorkerTests(unittest.TestCase):
    def result(self, content=CONTENT):
        return {
            "pdf_sha256": hashlib.sha256(content).hexdigest(),
            "page_number": 1, "ocr_used": True, "ocr": {},
        }

    def test_result_is_returned_and_temporary_files_are_removed(self):
        paths = []

        def run(command, **options):
            source = Path(command[command.index("--pdf") + 1])
            output = Path(command[command.index("--output") + 1])
            self.assertEqual(source.read_bytes(), CONTENT)
            self.assertEqual(options["env"]["OMP_NUM_THREADS"], "1")
            output.write_text(json.dumps(self.result()), encoding="utf-8")
            paths.extend([source, output])
            return subprocess.CompletedProcess(command, 0, stdout="Saved")

        with patch("ocr_worker.subprocess.run", side_effect=run):
            self.assertEqual(run_isolated_ocr(CONTENT, 1), self.result())
        self.assertTrue(all(not path.exists() for path in paths))

    def test_native_abort_becomes_a_reported_error(self):
        process = subprocess.CompletedProcess([], -6, stdout="Stage 3: model load")
        with patch("ocr_worker.subprocess.run", return_value=process):
            with self.assertRaisesRegex(RuntimeError, "exit code -6"):
                run_isolated_ocr(CONTENT, 1)

    def test_timeout_becomes_a_reported_error(self):
        failure = subprocess.TimeoutExpired([], 180, output=b"Stage 4: inference")
        with patch("ocr_worker.subprocess.run", side_effect=failure):
            with self.assertRaisesRegex(RuntimeError, "exceeded 180 seconds"):
                run_isolated_ocr(CONTENT, 1)

    def test_wrong_page_result_is_rejected(self):
        def run(command, **options):
            output = Path(command[command.index("--output") + 1])
            output.write_text(json.dumps({**self.result(), "page_number": 2}))
            return subprocess.CompletedProcess(command, 0, stdout="Saved")

        with patch("ocr_worker.subprocess.run", side_effect=run):
            with self.assertRaisesRegex(RuntimeError, "valid result for this page"):
                run_isolated_ocr(CONTENT, 1)


if __name__ == "__main__":
    unittest.main()
