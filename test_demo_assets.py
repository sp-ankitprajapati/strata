import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from demo_assets import demo_asset


class DemoAssetTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "assets/demo").mkdir(parents=True)
        self.content = b"bundled fixture"
        (self.root / "assets/demo/input.bin").write_bytes(self.content)
        self.manifest = {
            "manifest_version": 1,
            "assets": {"sample": {"repo_path": "assets/demo/input.bin",
                                   "sha256": hashlib.sha256(self.content).hexdigest()}},
        }
        self.write_manifest()

    def write_manifest(self):
        (self.root / "assets/demo/manifest.json").write_text(json.dumps(self.manifest))

    def test_valid_asset_resolves_to_captured_file(self):
        self.assertEqual(demo_asset(self.root, "sample").read_bytes(), self.content)

    def test_changed_asset_is_rejected(self):
        (self.root / "assets/demo/input.bin").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "has changed"):
            demo_asset(self.root, "sample")

    def test_asset_cannot_escape_project_root(self):
        self.manifest["assets"]["sample"]["repo_path"] = "../outside.bin"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "inside this project"):
            demo_asset(self.root, "sample")

    def test_missing_asset_is_reported(self):
        with self.assertRaises(KeyError):
            demo_asset(self.root, "missing")


if __name__ == "__main__":
    unittest.main()
