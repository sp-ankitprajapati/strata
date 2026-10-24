import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from material_review import review_material


ROOT = Path(__file__).resolve().parent


def load_queries(mode):
    if mode == "demo":
        path = ROOT / "examples/matching_queries.json"
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )

        if payload["data_kind"] != "synthetic_test_queries":
            raise ValueError(
                "Demo inputs must be marked as synthetic."
            )

        return path, payload["data_kind"], payload["queries"]

    path = (
        ROOT
        / "reports/ocr_baseline/material_comparison_all.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    queries = []

    for index, mention in enumerate(
        payload["baseline_mentions"], start=1
    ):
        queries.append({
            "query_id": f"ocr-{index:03d}",
            "product_name": mention["raw_text"],
            "material_keyword": mention["material"],
            "manufacturer": None,
            "manufacture_month": None,
            "source_image": "drawing_crop.png",
            "box_in_crop": mention["box"],
            "ocr_confidence": mention["confidence"],
            "ocr_confidence_scale": "0 to 100",
        })

    return path, "ocr_derived_generic_mentions", queries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["demo", "drawing"],
        required=True,
    )
    args = parser.parse_args()

    catalogue_path = (
        ROOT / "data/reference/manufacturer_records.json"
    )
    catalogue_bytes = catalogue_path.read_bytes()
    catalogue = json.loads(catalogue_bytes)

    input_path, data_kind, queries = load_queries(args.mode)

    results = [
        {
            "query": query,
            **review_material(query, catalogue),
        }
        for query in queries
    ]

    counts = Counter(
        item["decision"]["status"] for item in results
    )

    report = {
        "mode": args.mode,
        "query_data_kind": data_kind,
        "input_file": str(input_path.relative_to(ROOT)),
        "decision_scope": "Manufacturer reference matching",
        "catalogue_id": catalogue["dataset_id"],
        "catalogue_reviewed_on": catalogue["reviewed_on"],
        "catalogue_sha256": hashlib.sha256(
            catalogue_bytes
        ).hexdigest(),
        "counts": dict(counts),
        "results": results,
    }

    folder = ROOT / "reports/matching"
    folder.mkdir(parents=True, exist_ok=True)

    destination = folder / f"{args.mode}_decisions.json"
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for item in results:
        print(
            f"{item['query']['query_id']}: "
            f"{item['decision']['status']} | "
            f"{item['decision']['reason']}"
        )

        for candidate in item["suggestions"]:
            print(
                f"  Review candidate: {candidate['record_id']} | "
                f"similarity {candidate['similarity_score']:.3f}"
            )

    print("\nCounts:", dict(counts))

    if results:
        print("\nFirst complete decision:")
        print(json.dumps(
            results[0],
            ensure_ascii=False,
            indent=2,
        ))

    print(f"\nSaved: {destination}")


if __name__ == "__main__":
    main()