import hashlib
import json
from pathlib import Path

from material_matcher import unresolved
from material_review import review_material


ROOT = Path(__file__).resolve().parent

FIELDS = {
    "product": "product_name",
    "manufacturer": "manufacturer",
    "manufacturemonth": "manufacture_month",
}


def extract_schedule(text):
    records = []
    current = None

    for number, line in enumerate(text.splitlines(), start=1):
        label, separator, value = line.partition(":")
        label, value = label.strip(), value.strip()
        # Normalize labels only; preserve values and original source lines.
        label = "".join(label.split()).casefold()

        if separator and label == "item":
            current = {
                "query": {
                    "query_id": f"schedule-{len(records) + 1:03d}",
                    "product_name": None,
                    "manufacturer": None,
                    "manufacture_month": None,
                },
                "item_label": value,
                "source_lines": [],
                "field_evidence": {},
                "issues": [],
            }
            records.append(current)

        if current is None:
            continue

        current["source_lines"].append({"line": number, "text": line})

        field = FIELDS.get(label) if separator else None
        if field is None:
            continue

        evidence = current["field_evidence"].setdefault(field, [])
        evidence.append({"line": number, "value": value})

        if len(evidence) > 1:
            current["query"][field] = None
            if field not in current["issues"]:
                current["issues"].append(field)
        else:
            current["query"][field] = value or None

    return records


def main():
    input_path = ROOT / "examples/synthetic_schedule.txt"
    source = input_path.read_text(encoding="utf-8")

    if not source.startswith("Data type: synthetic\n"):
        raise ValueError("This experiment requires a labelled synthetic input.")

    catalogue_bytes = (
        ROOT / "data/reference/manufacturer_records.json"
    ).read_bytes()
    catalogue = json.loads(catalogue_bytes)

    records = extract_schedule(source)

    for record in records:
        if record["issues"]:
            result = {
                "decision": unresolved("conflicting_extracted_fields"),
                "suggestions": [],
            }
        else:
            result = review_material(record["query"], catalogue)

        record.update(result)

        print(
            f"{record['item_label']}: "
            f"{record['decision']['status']} | "
            f"{record['decision']['reason']}"
        )

    output = {
        "input_data_kind": "synthetic_schedule_text",
        "extraction_method": "labelled_block_rules",
        "ocr_used": False,
        "source_file": input_path.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "catalogue_id": catalogue["dataset_id"],
        "catalogue_reviewed_on": catalogue["reviewed_on"],
        "catalogue_sha256": hashlib.sha256(catalogue_bytes).hexdigest(),
        "results": records,
    }

    path = ROOT / "reports/schedule_extraction/synthetic_decisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()