import json
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw
from demo_assets import demo_asset

import hashlib
import sqlite3

from material_review import review_material
from review_history import load_history, save_review

ROOT = Path(__file__).resolve().parents[1]



def load_report(mode):
    path = ROOT / "reports" / "matching" / f"{mode}_decisions.json"

    if not path.exists():
        st.error("The saved matching report is missing.")
        st.stop()

    return json.loads(path.read_text(encoding="utf-8"))


def show_drawing_context(query):
    try:
        path = demo_asset(ROOT, "drawing_crop")
    except (OSError, KeyError, ValueError) as error:
        st.error(f"Could not load the bundled drawing example: {error}")
        return

    box = query.get("box_in_crop")
    if not box:
        st.info("This annotation has no saved drawing coordinates.")
        return

    x1, y1, x2, y2 = box
    padding = 160

    with Image.open(path) as image:
        left = max(0, x1 - padding)
        top = max(0, y1 - padding)
        right = min(image.width, x2 + padding)
        bottom = min(image.height, y2 + padding)

        context = image.crop((left, top, right, bottom)).convert("RGB")

    draw = ImageDraw.Draw(context)
    draw.rectangle(
        (x1 - left, y1 - top, x2 - left, y2 - top),
        outline="blue",
        width=4,
    )

    st.image(
        context,
        caption="Blue box: the selected OCR material mention.",
        alt=f"Drawing context around {query['product_name']}",
        width="stretch",
    )


st.title("Strata")
st.caption("Building drawing intelligence · Material reference review")

source = st.sidebar.radio(
    "Choose a data source",
    ["Drawing OCR", "Synthetic examples"],
    key="source",
)

mode = "drawing" if source == "Drawing OCR" else "demo"
report = load_report(mode)
results = report["results"]

if not results:
    st.info("This report contains no annotations.")
    st.stop()

if mode == "drawing":
    st.info(
        "These are material mentions extracted from a real drawing. "
        "Generic material names may remain unresolved."
    )
else:
    st.warning(
        "These are synthetic test queries matched against real manufacturer "
        "references. They were not extracted from the drawing."
    )

selected = st.selectbox(
    "Select an annotation",
    options=range(len(results)),
    format_func=lambda index: (
        f"{results[index]['query']['query_id']} · "
        f"{results[index]['query']['product_name']}"
    ),
    key=f"annotation_{mode}",
)

record = results[selected]
query = record["query"]
decision = record["decision"]

evidence_column, decision_column = st.columns([1.3, 1])

with evidence_column:
    st.subheader("Input evidence")

    if mode == "drawing":
        show_drawing_context(query)
    else:
        st.caption("Synthetic example: no associated drawing region.")

    st.text_input(
        "Original product or material text",
        value=query["product_name"],
        disabled=True,
        key=f"original_text_{mode}_{selected}",
    )

    st.write("**Manufacturer:**", query.get("manufacturer") or "Not provided")
    st.write(
        "**Manufacture month:**",
        query.get("manufacture_month") or "Not provided",
    )

    confidence = query.get("ocr_confidence")
    if confidence is not None:
        st.caption(
            f"OCR confidence: {confidence:.1f} "
            f"({query.get('ocr_confidence_scale', 'engine scale')}). "
            "This is separate from the material decision."
        )

with decision_column:
    st.subheader("Saved reference decision")

    status = decision["status"]

    if status == "asbestos_containing":
        st.error("Reference status: asbestos-containing")
    elif status == "non_asbestos_containing":
        st.success("Reference status: non-asbestos-containing")
    else:
        st.warning("Unresolved — further evidence required")

    st.caption("This result describes reference matching for the supplied details.")
    st.write("**Reason:**", decision["reason"].replace("_", " "))

    if decision.get("matched_record_id"):
        st.write("**Matched record:**", decision["matched_record_id"])

    for number, url in enumerate(decision.get("source_urls", []), start=1):
        st.link_button(f"Open decision source {number}", url)

    suggestions = record.get("suggestions", [])
    if suggestions:
        st.markdown("**Candidates requiring review**")

        for candidate in suggestions:
            with st.container(border=True):
                st.write(candidate["product_name"])
                st.caption(
                    f"{candidate['manufacturer']} · "
                    f"Name similarity: {candidate['similarity_score']:.3f}"
                )
                st.caption(
                    "Name similarity is not a probability of asbestos content. "
                    "This candidate does not change the unresolved decision."
                )

                for number, url in enumerate(candidate["source_urls"], start=1):
                    st.link_button(
                        f"Candidate source {number}",
                        url,
                    )

st.divider()
st.caption(
    f"Reference catalogue: {report['catalogue_id']} · "
    f"Reviewed: {report['catalogue_reviewed_on']}"
)

with st.expander("Inspect the saved record"):
    st.json(record)

export = {
    "mode": mode,
    "query_data_kind": report["query_data_kind"],
    "catalogue_id": report["catalogue_id"],
    "catalogue_reviewed_on": report["catalogue_reviewed_on"],
    "catalogue_sha256": report["catalogue_sha256"],
    "result": record,
}

st.download_button(
    "Download original saved result",
    data=json.dumps(export, ensure_ascii=False, indent=2),
    file_name=f"strata_{query['query_id']}.json",
    mime="application/json",
)

st.divider()
st.subheader("Review product details")
st.caption(
    "Submit verified corrections with an evidence note. "
    "The original OCR record and saved decision above remain unchanged."
)

record_key = hashlib.sha256(
    json.dumps(
        {"mode": mode, "record": record},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
).hexdigest()

history_path = ROOT / "data" / "reviews" / "reviews.sqlite3"

try:
    history = load_history(history_path, record_key)
except (OSError, sqlite3.Error) as error:
    st.error(f"Could not read review history: {error}")
    st.stop()

defaults = history[-1]["reviewed_query"] if history else query

with st.form(f"review_{record_key}"):
    product = st.text_input(
        "Product name",
        value=defaults.get("product_name") or "",
        key=f"product_{record_key}",
    )
    manufacturer = st.text_input(
        "Manufacturer",
        value=defaults.get("manufacturer") or "",
        key=f"manufacturer_{record_key}",
    )
    month = st.text_input(
        "Manufacture month (YYYY-MM)",
        value=defaults.get("manufacture_month") or "",
        help="Leave unknown details blank. Enter the product's manufacturing date.",
        key=f"month_{record_key}",
    )
    reviewer = st.text_input(
        "Reviewer name",
        help="Self-reported name for this prototype.",
        key=f"reviewer_{record_key}",
    )
    note = st.text_area(
        "Evidence or reason for this review",
        help="Describe the supporting document, or label a synthetic test.",
        key=f"note_{record_key}",
    )
    submitted = st.form_submit_button("Run matching and save review")

if submitted:
    if not product.strip() or not reviewer.strip() or not note.strip():
        st.error("Enter a product name, reviewer name and evidence note.")
    else:
        reviewed_query = {
            **query,
            "product_name": product.strip(),
            "manufacturer": manufacturer.strip() or None,
            "manufacture_month": month.strip() or None,
        }

        try:
            catalogue_bytes = (
                ROOT / "data/reference/manufacturer_records.json"
            ).read_bytes()
            catalogue = json.loads(catalogue_bytes)

            details = {
                "mode": mode,
                "query_data_kind": report["query_data_kind"],
                "reviewer": reviewer.strip(),
                "evidence_note": note.strip(),
                "original_record": record,
                "reviewed_query": reviewed_query,
                "review_result": review_material(reviewed_query, catalogue),
                "catalogue_id": catalogue["dataset_id"],
                "catalogue_reviewed_on": catalogue["reviewed_on"],
                "catalogue_sha256": hashlib.sha256(catalogue_bytes).hexdigest(),
            }

            event = save_review(history_path, record_key, details)

        except (OSError, sqlite3.Error, ValueError, KeyError) as error:
            st.error(f"Review was not saved: {error}")
        else:
            history.append(event)
            st.success("Review saved.")

if history:
    latest = history[-1]

    st.subheader("Last submitted review")
    st.caption(
        f"{latest['saved_at_utc']} · Reviewer: {latest['reviewer']} · "
        "This result applies to the submitted details below."
    )
    st.json(latest["reviewed_query"])
    st.json(latest["review_result"])

    for number, url in enumerate(
        latest["review_result"]["decision"]["source_urls"], start=1
    ):
        st.link_button(f"Reviewed decision source {number}", url)

    with st.expander(f"Saved review history ({len(history)} submissions)"):
        st.json(history)

    st.download_button(
        "Download review history",
        data=json.dumps(history, ensure_ascii=False, indent=2),
        file_name=f"strata_{mode}_{query['query_id']}_reviews.json",
        mime="application/json",
        key=f"history_download_{record_key}",
    )
else:
    st.caption("No reviews have been submitted for this annotation.")