import re
import unicodedata
from datetime import date


def normalize_text(value):
    if not isinstance(value, str):
        return ""

    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(value.split())


def unresolved(reason, candidates=()):
    return {
        "status": "unresolved",
        "reason": reason,
        "matched_record_id": None,
        "candidate_record_ids": [
            record["record_id"] for record in candidates
        ],
        "source_urls": [],
    }


def match_material(query, catalogue):
    """Match supplied product facts to a manufacturer reference."""
    if query.get("product_code"):
        return unresolved("product_code_matching_not_supported")

    product = normalize_text(query.get("product_name"))

    candidates = [
        record for record in catalogue["records"]
        if product and product in {
            normalize_text(name)
            for name in [record["product_name"]]
            + record.get("aliases", [])
        }
    ]

    if not candidates:
        return unresolved("no_exact_product_match")

    manufacturer = normalize_text(query.get("manufacturer"))

    if not manufacturer:
        return unresolved("manufacturer_missing", candidates)

    products = candidates
    candidates = [
        record for record in products
        if manufacturer in {
            normalize_text(name)
            for name in [record["manufacturer"]]
            + record.get("manufacturer_aliases", [])
        }
    ]

    if not candidates:
        return unresolved("manufacturer_mismatch", products)

    month = normalize_text(query.get("manufacture_month"))

    if not month:
        return unresolved("manufacture_month_missing", candidates)

    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", month):
            raise ValueError("Expected YYYY-MM")

        date.fromisoformat(month + "-01")
    except ValueError:
        return unresolved(
            "manufacture_month_invalid_or_imprecise",
            candidates,
        )

    if month > catalogue["reviewed_on"][:7]:
        return unresolved("date_after_reference_review", candidates)

    dated = [
        record for record in candidates
        if record["match_period_start"]
        <= month
        <= record["match_period_end"]
    ]

    if not dated:
        return unresolved("date_outside_reference_period", candidates)

    if len(dated) != 1:
        return unresolved("ambiguous_reference", dated)

    record = dated[0]

    return {
        "status": record["reference_status"],
        "reason": "exact_product_manufacturer_and_month_match",
        "matched_record_id": record["record_id"],
        "candidate_record_ids": [record["record_id"]],
        "source_urls": list(record["source_urls"]),
    }