"""Prepare the pretrained Japanese-English models used by the live OCR worker."""

import os
from pathlib import Path

from ocr_worker import worker_environment


def main():
    os.environ.update(worker_environment())
    import cv2
    import easyocr
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cv2.setNumThreads(1)
    folder = Path(__file__).resolve().parent / ".models/easyocr"
    easyocr.Reader(["ja", "en"], gpu=False, quantize=False,
                   model_storage_directory=str(folder), download_enabled=True)
    print("Japanese-English OCR models are ready:", folder)


if __name__ == "__main__":
    main()
