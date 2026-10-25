"""Connect supported PDF layouts to the reference matcher, retaining evidence."""

from copy import deepcopy

from extract_reference_candidates import parse_table
from extract_schedule import extract_schedule
from material_matcher import unresolved
from material_review import review_material


def build_pdf_candidates(analysis):
    page = analysis["page_number"]
    origin = {
        "pdf_sha256": analysis["pdf_sha256"],
        "page_number": page,
        "coordinate_system": analysis["coordinate_system"],
    }
    output = {"candidates": [], "conditional_rules": [], "skipped_tables": []}

    for number, record in enumerate(extract_schedule(analysis["text"]), 1):
        record = deepcopy(record)
        record["query"]["query_id"] = f"pdf-p{page}-item{number}"
        record["source"] = {
            **origin, "extraction_method": "labelled_block_rules"
        }
        output["candidates"].append(record)

    for number, table in enumerate(analysis["tables"], 1):
        source = {
            **origin,
            "table_number": number,
            "table_bbox_pdf_points": deepcopy(table["bbox_pdf_points"]),
            "extraction_method": "document_specific_table_rules",
        }
        try:
            names, rules = parse_table(table["rows"])
        except ValueError as error:
            output["skipped_tables"].append({
                "source": source, "reason": str(error)
            })
            continue

        for entry in names:
            query_id = (
                f"pdf-p{page}-t{number}"
                f"-r{entry['row']}-c{entry['column']}"
            )
            output["candidates"].append({
                "query": {
                    "query_id": query_id,
                    "product_name": entry["name"],
                    "manufacturer": None,
                    "manufacture_month": None,
                },
                "table_evidence": deepcopy(entry),
                "source": deepcopy(source),
                "issues": [],
            })

        output["conditional_rules"].extend(
            {**deepcopy(rule), "source": deepcopy(source)} for rule in rules
        )

    return output


def match_pdf_candidate(candidate, catalogue):
    if candidate["issues"]:
        return {
            "decision": unresolved("conflicting_extracted_fields"),
            "suggestions": [],
        }
    return review_material(candidate["query"], catalogue)
