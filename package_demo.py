"""Author-side capture of demo inputs and the working CPU environment."""

import hashlib
import importlib.metadata as metadata
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def package_versions():
    packages = {}
    direct_installs = []
    for distribution in metadata.distributions():
        name = distribution.metadata.get("Name")
        if not name:
            continue
        canonical = re.sub(r"[-_.]+", "-", name).lower()
        if canonical in {"pip", "setuptools", "wheel", "uv"}:
            continue
        direct = distribution.read_text("direct_url.json")
        if direct:
            direct_installs.append(name)
        packages[canonical] = {"name": name, "version": distribution.version}
    for name in ("streamlit", "pillow", "pdfplumber", "easyocr", "torch", "torchvision"):
        if name not in packages:
            raise ValueError(f"Missing {name}. Run this using the working .venv-ocr environment.")
    if "+cpu" not in packages["torch"]["version"]:
        raise ValueError("This checkpoint expects the project's CPU PyTorch environment.")
    return packages, sorted(direct_installs)


def asset_plan():
    kmew = read_json(ROOT / "reports/reference_extraction/evidence/inspection.json")
    inspection = read_json(ROOT / "reports/ocr_baseline/inspection.json")
    drawing_source = read_json(ROOT / "data/metadata/old_capitol_sheet_14.json")
    scan = read_json(ROOT / "reports/scanned_pdf/decisions_cpu.json")
    pdf = ROOT / "data/raw/kmew_reference.pdf"
    crop = ROOT / "data/processed/drawing_crop.png"
    synthetic = ROOT / "reports/scanned_pdf/evidence/synthetic_schedule_scan.pdf"
    if file_sha256(pdf) != kmew["pdf_sha256"]:
        raise ValueError("The KMEW PDF differs from the archived inspection snapshot.")
    if file_sha256(synthetic) != scan["pdf_sha256"]:
        raise ValueError("The synthetic PDF differs from the archived OCR checkpoint.")
    x0, top, x1, bottom = inspection["crop_box"]
    with Image.open(crop) as image:
        if image.size != (x1 - x0, bottom - top):
            raise ValueError("The drawing crop dimensions differ from the inspection record.")
    assets = {
        "kmew_pdf": {
            "repo_path": "assets/demo/kmew_reference.pdf", "sha256": file_sha256(pdf),
            "data_kind": "real_manufacturer_reference_document",
            "source_url": kmew["source_url"], "retrieved_at_utc": kmew["retrieved_at_utc"],
            "evidence_record": "reports/reference_extraction/evidence/inspection.json",
        },
        "drawing_crop": {
            "repo_path": "assets/demo/drawing_crop.png", "sha256": file_sha256(crop),
            "data_kind": "real_drawing_crop", "source_url": drawing_source["source_url"],
            "crop_box_in_source_pixels": inspection["crop_box"],
            "source_size_pixels": [inspection["width"], inspection["height"]],
            "asbestos_status": "not_established",
        },
        "synthetic_scan": {
            "repo_path": "reports/scanned_pdf/evidence/synthetic_schedule_scan.pdf",
            "sha256": file_sha256(synthetic), "data_kind": "synthetic_schedule_scan",
            "evidence_record": "reports/scanned_pdf/decisions_cpu.json",
        },
    }
    copies = [(pdf, ROOT / assets["kmew_pdf"]["repo_path"]),
              (crop, ROOT / assets["drawing_crop"]["repo_path"])]
    for source, destination in copies:
        if destination.exists() and file_sha256(source) != file_sha256(destination):
            raise ValueError(f"Existing demo asset differs: {destination.name}")
    return {"manifest_version": 1, "assets": assets}, copies


def main():
    packages, direct_installs = package_versions()
    manifest, copies = asset_plan()
    folder = ROOT / "assets/demo"
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "manifest.json"
    if manifest_path.exists() and read_json(manifest_path) != manifest:
        raise ValueError("Existing demo manifest differs. Review the snapshot before replacing it.")
    for source, destination in copies:
        if not destination.exists():
            shutil.copyfile(source, destination)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    model_dir = ROOT / ".models/easyocr"
    environment = {
        "python": platform.python_version(), "platform": platform.platform(),
        "machine": platform.machine(),
        "source_commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "packages": packages,
        "direct_install_names": direct_installs,
        "cached_model_sha256": {p.name: file_sha256(p) for p in sorted(model_dir.glob("*.pth"))},
        "scope": "Working CPU snapshot; clean installation remains to be verified.",
    }
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "environment_cpu.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lock = [
        "# Captured working CPU environment; validate installation in a clean Python 3.11 environment.",
        "# CPU PyTorch wheels are served by the additional official index.",
        "--extra-index-url https://download.pytorch.org/whl/cpu",
    ]
    lock.extend(f"{p['name']}=={p['version']}" for _, p in sorted(packages.items()))
    (ROOT / "requirements-lock-cpu.txt").write_text("\n".join(lock) + "\n", encoding="utf-8")
    minimal = [packages[name] for name in ("streamlit", "pillow", "pdfplumber")]
    (ROOT / "requirements-demo.txt").write_text(
        "\n".join(f"{p['name']}=={p['version']}" for p in minimal) + "\n",
        encoding="utf-8",
    )
    print("Demo assets captured and verified:")
    for item in manifest["assets"].values():
        path = ROOT / item["repo_path"]
        print(f"  {item['repo_path']}: {path.stat().st_size:,} bytes")
    print("Python:", environment["python"])
    for name in ("streamlit", "pillow", "pdfplumber", "easyocr", "torch", "torchvision"):
        print(f"{packages[name]['name']}: {packages[name]['version']}")
    print("Locked packages:", len(packages))
    if direct_installs:
        print("Direct-install package names:", direct_installs)
    print("Cached models:", sorted(environment["cached_model_sha256"]))
    print("Free workspace MiB:", shutil.disk_usage(ROOT).free // (1024 * 1024))
    print("Saved requirements-lock-cpu.txt, requirements-demo.txt and docs/environment_cpu.json")


if __name__ == "__main__":
    main()
