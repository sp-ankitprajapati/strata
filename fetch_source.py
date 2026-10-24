import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

image_url = (
    "https://upload.wikimedia.org/wikipedia/commons/3/37/"
    "Old_State_Capitol_Building%2C_Markham_and_Center_Streets%2C_"
    "Little_Rock%2C_Pulaski_County%2C_AR_HABS_ARK%2C60-LIRO%2C1-_"
    "%28sheet_14_of_27%29.png"
)

project_folder = Path(__file__).resolve().parent
image_path = project_folder / "data/raw/old_capitol_sheet_14.png"
metadata_path = project_folder / "data/metadata/old_capitol_sheet_14.json"

request = Request(
    image_url,
    headers={"User-Agent": "Strata/0.1 educational document research"},
)

print("Downloading one real drawing...")

try:
    with urlopen(request, timeout=60) as response:
        image_bytes = response.read()
except HTTPError as error:
    print(f"The source refused the request: HTTP {error.code}")
    raise SystemExit(1)
except URLError as error:
    print(f"Connection failed: {error.reason}")
    raise SystemExit(1)

# Check that the response is a PNG image rather than an HTML page.
if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
    print("The response was not a PNG image.")
    raise SystemExit(1)

image_path.parent.mkdir(parents=True, exist_ok=True)
image_path.write_bytes(image_bytes)

metadata = {
    "document_id": "old_capitol_sheet_14",
    "source_url": image_url,
    "dataset_reference": "WAFFLE",
    "waffle_sample_id": "33669447",
    "original_split": "train",
    "purpose": "Initial OCR practice",
    "asbestos_status": "not_established"
}

metadata_path.parent.mkdir(parents=True, exist_ok=True)
metadata_path.write_text(
    json.dumps(metadata, indent=2),
    encoding="utf-8"
)

print(f"Image saved: {image_path}")
print(f"Downloaded: {len(image_bytes):,} bytes")
print(f"Source information saved: {metadata_path}")