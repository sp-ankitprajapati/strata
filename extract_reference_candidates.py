import json
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def compact(value):
    return "".join(
        unicodedata.normalize("NFKC", value or "").split()
    )


def parse_table(rows):
    if not rows:
        raise ValueError("Empty table.")

    header = [compact(cell) for cell in rows[0]]

    if (
        len(header) == 5
        and header[0] == "シリーズ名"
        and "商品板厚" in header[1]
    ):
        group = "exterior_wall"
    elif len(header) == 4 and header[0].startswith("商品名"):
        group = "roof"
    elif header == ["シリーズ名", "商品名", "塗装種類", "塗装色"]:
        group = "SOLIDO"
    else:
        raise ValueError(f"Unrecognised table header: {rows[0]}")

    candidates, rules = [], []

    for row_number, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            raise ValueError(
                f"Unexpected width in row {row_number}."
            )

        populated = [
            (column, cell)
            for column, cell in enumerate(row, start=1)
            if cell is not None and cell.strip()
        ]

        if not populated:
            continue

        if group == "roof" and len(populated) == 1:
            rules.append({
                "row": row_number,
                "raw_text": populated[0][1],
                "raw_cells": row,
                "review_status": "pending_review",
            })
            continue

        entries = (
            populated if group == "roof" else [(1, row[0])]
        )

        for column, name in entries:
            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    f"Missing name in row {row_number}."
                )

            candidates.append({
                "group": group,
                "name": name,
                "name_kind": (
                    "product_or_series"
                    if group == "roof" else "series"
                ),
                "thickness_mm_raw": (
                    row[1] if group == "exterior_wall" else None
                ),
                "row": row_number,
                "column": column,
                "raw_cells": row,
            })

    return candidates, rules


def main():
    source = ROOT / "data/processed/kmew_reference/inspection.json"
    inspection = json.loads(
        source.read_text(encoding="utf-8")
    )

    pdf_sha = inspection["pdf_sha256"]
    candidates, rules = [], []

    for page in inspection["pages"]:
        for table_number, table in enumerate(
            page["table_candidates"], start=1
        ):
            extracted, table_rules = parse_table(table["rows"])

            origin = {
                "source_url": inspection["source_url"],
                "pdf_sha256": pdf_sha,
                "page": page["page_number"],
                "table": table_number,
                "table_bbox_pdf_points": table["bbox_pdf_points"],
                "coordinate_system": inspection["coordinate_system"],
            }

            for candidate in extracted:
                candidates.append({
                    "candidate_id": (
                        f"kmew-{pdf_sha[:10]}-p{origin['page']}"
                        f"-t{table_number}-r{candidate['row']}"
                        f"-c{candidate['column']}"
                    ),
                    "manufacturer": "KMEW",
                    **candidate,
                    "source": dict(origin),
                    "review_status": "pending_review",
                    "eligible_for_automatic_matching": False,
                })

            for rule in table_rules:
                rules.append({
                    **rule,
                    "source": dict(origin),
                })

    report = {
        "data_kind": "real_reference_extraction_candidates",
        "source_url": inspection["source_url"],
        "pdf_sha256": pdf_sha,
        "retrieved_at_utc": inspection["retrieved_at_utc"],
        "extraction_method": "document_specific_table_rules",
        "ocr_used": False,
        "document_pages": [
            {
                "page": page["page_number"],
                "raw_text": page["text"],
            }
            for page in inspection["pages"]
        ],
        "scope_note": (
            "Keep the certificate wording and table conditions "
            "with these names. A sales-period condition must not "
            "become a manufacturing date. No candidates have "
            "been imported into the active catalogue."
        ),
        "candidates": candidates,
        "conditional_rules": rules,
    }

    output = (
        ROOT / "reports/reference_extraction/kmew_candidates.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for group in ["exterior_wall", "roof", "SOLIDO"]:
        count = sum(c["group"] == group for c in candidates)
        print(f"{group}: {count}")

    print(f"Total candidates: {len(candidates)}")
    print(f"Conditional rules preserved: {len(rules)}")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()