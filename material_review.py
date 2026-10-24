from difflib import SequenceMatcher

from material_matcher import match_material, normalize_text


def suggest_candidates(query, catalogue, threshold=0.85, limit=3):
    product = normalize_text(query.get("product_name"))
    manufacturer = normalize_text(query.get("manufacturer"))

    if not product or query.get("product_code"):
        return []

    suggestions = []

    for record in catalogue["records"]:
        manufacturer_names = [
            record["manufacturer"]
        ] + record.get("manufacturer_aliases", [])

        if manufacturer and manufacturer not in {
            normalize_text(name) for name in manufacturer_names
        }:
            continue

        names = [
            record["product_name"]
        ] + record.get("aliases", [])

        score = max(
            SequenceMatcher(
                None,
                product,
                normalize_text(name),
                autojunk=False,
            ).ratio()
            for name in names
        )

        if score >= threshold:
            suggestions.append({
                "record_id": record["record_id"],
                "product_name": record["product_name"],
                "manufacturer": record["manufacturer"],
                "similarity_score": round(score, 4),
                "match_period_start": record["match_period_start"],
                "match_period_end": record["match_period_end"],
                "source_urls": list(record["source_urls"]),
                "requires_review": True,
            })

    suggestions.sort(
        key=lambda item: (
            -item["similarity_score"],
            item["record_id"],
        )
    )

    return suggestions[:limit]


def review_material(query, catalogue):
    decision = match_material(query, catalogue)
    suggestions = []

    if decision["reason"] == "no_exact_product_match":
        suggestions = suggest_candidates(query, catalogue)

    return {
        "decision": decision,
        "suggestions": suggestions,
    }