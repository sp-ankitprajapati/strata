"""Resolve bundled examples and verify their captured content hashes."""

import hashlib
import json
from pathlib import Path


def demo_asset(root, name):
    root = Path(root).resolve()
    manifest = json.loads((root / "assets/demo/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != 1:
        raise ValueError("Unsupported demo manifest version.")
    asset = manifest["assets"][name]
    path = (root / asset["repo_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("Demo asset path must stay inside this project.") from error
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != asset["sha256"]:
        raise ValueError(f"Bundled demo asset has changed: {name}")
    return path
