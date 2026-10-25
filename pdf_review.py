"""Save human reviews of PDF entries without changing the extracted record."""

import hashlib
import json
from copy import deepcopy

from material_review import review_material
from review_history import save_review


def pdf_review_key(record):
    identity = {
        "scope": "pdf_entry_review_v1",
        "pdf_sha256": record["source"]["pdf_sha256"],
        "page_number": record["source"]["page_number"],
        "query_id": record["query"]["query_id"],
        "extraction_method": record["source"]["extraction_method"],
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()


def save_pdf_review(
    path, record, catalogue_bytes, fields, reviewer, note,
    review_kind, document_context,
):
    if review_kind not in {"evidence_based_review", "synthetic_test"}:
        raise ValueError("Select a valid review type.")

    values = {}
    for field in ("product_name", "manufacturer", "manufacture_month"):
        value = fields.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} must be text or empty.")
        values[field] = (value or "").strip() or None

    if not values["product_name"]:
        raise ValueError("Enter a product name.")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Enter a reviewer name.")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Enter an evidence note or describe the synthetic test.")

    catalogue = json.loads(catalogue_bytes)
    reviewed_query = {**deepcopy(record["query"]), **values}
    details = {
        "mode": "pdf",
        "query_data_kind": "human_review_of_pdf_extraction",
        "review_kind": review_kind,
        "reviewer": reviewer.strip(),
        "evidence_note": note.strip(),
        "original_record": deepcopy(record),
        "document_context": deepcopy(document_context),
        "reviewed_query": reviewed_query,
        "review_result": review_material(reviewed_query, catalogue),
        "catalogue_id": catalogue["dataset_id"],
        "catalogue_reviewed_on": catalogue["reviewed_on"],
        "catalogue_sha256": hashlib.sha256(catalogue_bytes).hexdigest(),
    }
    return save_review(path, pdf_review_key(record), details)
