"""Run OCR in a separate process so native failures can be reported by the UI."""

import argparse
import faulthandler
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent


def worker_environment():
    environment = os.environ.copy()
    environment.update({
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "PYTHONFAULTHANDLER": "1",
        "PYTHONUNBUFFERED": "1",
    })
    return environment


def memory_status():
    status = {}
    for name in ("memory.current", "memory.max", "memory.events"):
        path = Path("/sys/fs/cgroup") / name
        try:
            status[name] = path.read_text().strip()
        except OSError:
            pass
    return status


def log_text(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return (value or "")[-12000:]


def run_isolated_ocr(content, page_number, timeout_seconds=180):
    from pdf_processing import validate_pdf_bytes

    validate_pdf_bytes(content)
    before = memory_status()
    with TemporaryDirectory(prefix="strata-ocr-") as folder:
        pdf_path = Path(folder) / "input.pdf"
        output_path = Path(folder) / "result.json"
        pdf_path.write_bytes(content)
        command = [
            sys.executable, "-u", str(ROOT / "ocr_worker.py"),
            "--pdf", str(pdf_path), "--page", str(page_number),
            "--output", str(output_path),
        ]
        try:
            process = subprocess.run(
                command, cwd=ROOT, env=worker_environment(),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                f"OCR worker exceeded {timeout_seconds} seconds.\n"
                + log_text(error.stdout)
            ) from error
        if process.returncode:
            raise RuntimeError(
                f"OCR worker exit code {process.returncode}.\n"
                f"Memory before: {json.dumps(before)}\n"
                f"Memory after: {json.dumps(memory_status())}\n"
                + log_text(process.stdout)
            )
        try:
            result = json.loads(output_path.read_text(encoding="utf-8"))
            if (result["pdf_sha256"] != hashlib.sha256(content).hexdigest()
                    or result["page_number"] != page_number
                    or result["ocr_used"] is not True
                    or not isinstance(result["ocr"], dict)):
                raise ValueError("Wrong source or result type.")
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise RuntimeError(
                "OCR worker did not produce a valid result for this page.\n"
                + log_text(process.stdout)
            ) from error
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    os.environ.update(worker_environment())
    faulthandler.enable()
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ImportError, OSError, ValueError):
        pass

    print("Stage 1/4: reading the selected PDF page.", flush=True)
    from pdf_processing import inspect_pdf_page
    from pdf_ocr import recognize_pdf_page
    content = args.pdf.read_bytes()
    native, _ = inspect_pdf_page(content, args.page)

    print("Stage 2/4: importing OCR libraries.", flush=True)
    import platform
    import cv2
    import torch
    import easyocr

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cv2.setNumThreads(1)
    print("Stage 3/4: loading cached models; CPU, quantize=False.", flush=True)
    reader = easyocr.Reader(
        ["ja", "en"], gpu=False, quantize=False,
        model_storage_directory=str(ROOT / ".models/easyocr"),
        download_enabled=False,
    )
    info = {
        "engine": "EasyOCR", "easyocr_version": easyocr.__version__,
        "torch_version": torch.__version__, "python_version": platform.python_version(),
        "languages": ["ja", "en"], "device": "cpu", "quantize": False,
        "cpu_threads": 1, "execution": "isolated_process",
    }
    print("Stage 4/4: rendering and recognising the page.", flush=True)
    result = recognize_pdf_page(content, args.page, native, reader, info)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"Text boxes: {len(result['ocr']['detections'])}", flush=True)
    print(f"Inference seconds: {result['ocr']['inference_seconds']}", flush=True)
    print(f"Saved: {args.output}", flush=True)


if __name__ == "__main__":
    main()
