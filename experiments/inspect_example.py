import json
from pathlib import Path

# Locate the sample relative to this Python file.
project_folder = Path(__file__).resolve().parents[1]
sample_path = project_folder / "examples" / "annotation.json"

# Read the file and convert its JSON into a Python dictionary.
with sample_path.open(encoding="utf-8") as file:
    annotation = json.load(file)

# Display selected fields.
print("Strata — first material record")
print(f"Data type: {annotation['data_kind']}")
print(f"Material: {annotation['material_text']}")
print(f"Product code: {annotation['product_code']}")
print(f"Manufacturer: {annotation['manufacturer']}")
print(f"Year: {annotation['year']}")