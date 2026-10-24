import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    path = ROOT / "data/reference/manufacturer_records.json"
    catalogue = json.loads(path.read_text(encoding="utf-8"))

    allowed_statuses = {
        "asbestos_containing",
        "non_asbestos_containing",
    }
    seen_ids = set()

    for record in catalogue["records"]:
        record_id = record["record_id"]

        if record_id in seen_ids:
            raise ValueError(f"Duplicate record ID: {record_id}")
        seen_ids.add(record_id)

        if record["reference_status"] not in allowed_statuses:
            raise ValueError(f"Invalid status: {record_id}")

        if not record["source_urls"]:
            raise ValueError(f"Missing evidence source: {record_id}")

        start = date.fromisoformat(
            record["match_period_start"] + "-01"
        )
        end = date.fromisoformat(
            record["match_period_end"] + "-01"
        )

        if start > end:
            raise ValueError(f"Reversed date window: {record_id}")

        print(f"\n{record_id}")
        print("Product:", record["product_name"])
        print("Reference status:", record["reference_status"])
        print(
            "Matching period:",
            record["match_period_start"],
            "to",
            record["match_period_end"],
        )

    print(f"\nLoaded {len(seen_ids)} real reference records.")


if __name__ == "__main__":
    main()