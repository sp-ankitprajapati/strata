import hashlib
import json
import sqlite3
from pathlib import Path

import streamlit as st

from demo_assets import demo_asset
from pdf_processing import inspect_pdf_page, pdf_page_count
from pdf_candidates import build_pdf_candidates, match_pdf_candidate
from ocr_worker import run_isolated_ocr
from pdf_review import pdf_review_key, save_pdf_review
from review_history import load_history


ROOT = Path(__file__).resolve().parents[1]
st.session_state.setdefault("pdf_ocr_latest", None)


@st.cache_data(max_entries=4, show_spinner=False)
def cached_page_count(content):
    return pdf_page_count(content)


@st.cache_data(max_entries=4, show_spinner=False)
def cached_inspection(content, page_number):
    return inspect_pdf_page(content, page_number)


@st.cache_data(max_entries=2, show_spinner=False)
def cached_ocr_page(content, page_number):
    return run_isolated_ocr(content, page_number)


st.title("Process PDF")
st.caption("Select a page, inspect its text and tables, and export the evidence.")

source = st.segmented_control(
    "Document source",
    ["Project example", "Scanned schedule example", "Upload PDF"],
    default="Project example",
    key="pdf_document_source",
)

if source == "Project example":
    try:
        path = demo_asset(ROOT, "kmew_pdf")
    except (OSError, KeyError, ValueError) as error:
        st.error(f"Could not load the bundled PDF example: {error}")
        st.stop()
    content = path.read_bytes()
    filename = "KMEW manufacturer reference"
    origin = "project_example"
elif source == "Scanned schedule example":
    try:
        path = demo_asset(ROOT, "synthetic_scan")
    except (OSError, KeyError, ValueError) as error:
        st.error(f"Could not load the bundled scanned example: {error}")
        st.stop()
    content = path.read_bytes()
    filename = "Synthetic schedule scan"
    origin = "synthetic_scan_example"
    st.warning("Synthetic example for checking the scanned-PDF workflow.")
elif source == "Upload PDF":
    uploaded = st.file_uploader(
        "Choose a PDF",
        type=["pdf"],
        key="pdf_upload",
    )
    if uploaded is None:
        st.info("Choose a PDF to begin.")
        st.stop()
    content = uploaded.getvalue()
    filename = uploaded.name
    origin = "user_uploaded_document"
else:
    st.info("Select a document source.")
    st.stop()

try:
    with st.spinner("Reading PDF..."):
        total = cached_page_count(content)
    if total < 1:
        raise ValueError("The PDF contains no pages.")
except Exception as error:
    st.error(f"Could not read this PDF: {error}")
    st.stop()

fingerprint = hashlib.sha256(content).hexdigest()

page_number = st.number_input(
    "Page number",
    min_value=1,
    max_value=total,
    value=1,
    step=1,
    key=f"pdf_page_{fingerprint}",
)

try:
    with st.spinner("Extracting the selected page..."):
        analysis, preview = cached_inspection(content, int(page_number))
except Exception as error:
    st.error(f"Could not process this page: {error}")
    st.stop()

native_analysis = analysis

st.caption(
    f"{filename} · Page {page_number}/{total} · "
    f"{len(analysis['text'])} characters · "
    f"{len(analysis['tables'])} table candidates"
)

left, right = st.columns([1, 1])

with left:
    st.subheader("Page preview")
    st.image(
        preview,
        alt=f"Selected PDF page {page_number}",
        width="stretch",
    )

with right:
    st.subheader("Extracted text")
    if analysis["text"].strip():
        st.text_area(
            "Selectable PDF text",
            value=analysis["text"],
            height=400,
            disabled=True,
            key=f"pdf_text_{fingerprint}_{page_number}",
        )
    else:
        st.info("No selectable text was found. This page may need OCR.")

text_source = st.segmented_control(
    "Text source for matching", ["Native PDF", "OCR"],
    default="Native PDF", key=f"pdf_text_source_{fingerprint}_{page_number}",
)
if text_source == "OCR":
    st.caption(
        "Japanese-English OCR runs on CPU when requested. "
        "This version extracts labelled item blocks; scanned tables are not reconstructed."
    )
    if st.button("Run OCR", key=f"pdf_run_ocr_{fingerprint}_{page_number}"):
        try:
            with st.spinner("Reading this page with OCR..."):
                ocr_analysis = cached_ocr_page(content, int(page_number))
            st.session_state.pdf_ocr_latest = ocr_analysis
        except Exception as error:
            st.error(f"OCR did not complete: {error}")
            st.stop()
    latest_ocr = st.session_state.pdf_ocr_latest
    if not latest_ocr or (
        latest_ocr["pdf_sha256"] != fingerprint
        or latest_ocr["page_number"] != int(page_number)
    ):
        st.info("Click Run OCR to prepare text for this page.")
        st.stop()
    analysis = latest_ocr
    st.caption(
        f"OCR text boxes: {len(analysis['ocr']['detections'])} · "
        f"Recorded inference time: {analysis['ocr']['inference_seconds']:.1f} seconds"
    )
    st.text_area(
        "OCR text used for matching", value=analysis["text"], height=320,
        disabled=True, key=f"pdf_ocr_text_{analysis['ocr']['result_sha256']}",
    )
    with st.expander("OCR boxes, confidence scores and model details"):
        st.json(analysis["ocr"])
elif text_source != "Native PDF":
    st.info("Select a text source to continue.")
    st.stop()

st.subheader("Table candidates")
if not analysis["tables"]:
    st.caption(
        "Scanned tables are not reconstructed in this OCR path."
        if analysis["ocr_used"] else "No tables were detected from PDF lines."
    )

for number, table in enumerate(analysis["tables"], start=1):
    with st.expander(f"Table {number} · {len(table['rows'])} rows"):
        st.json(table)

export = {
    "document_origin": origin,
    "document_name": filename,
    "analysis": analysis,
    "native_analysis": native_analysis,
}

st.download_button(
    "Download page extraction",
    data=json.dumps(export, ensure_ascii=False, indent=2),
    file_name=f"strata_{fingerprint[:10]}_page_{page_number}.json",
    mime="application/json",
)

st.subheader("Material entries")
st.caption(
    "Extracts labelled item blocks and the supported reference-table layouts. "
    "Table names need verified manufacturer and manufacturing-date details "
    "before a reference decision can be made."
)

extracted = build_pdf_candidates(analysis)
catalogue_bytes = (ROOT / "data/reference/manufacturer_records.json").read_bytes()
catalogue = json.loads(catalogue_bytes)
results = [
    {**candidate, **match_pdf_candidate(candidate, catalogue)}
    for candidate in extracted["candidates"]
]
unresolved_count = sum(r["decision"]["status"] == "unresolved" for r in results)
st.write(f"Extracted entries: {len(results)} · Unresolved: {unresolved_count}")

if extracted["skipped_tables"]:
    st.info(
        f"{len(extracted['skipped_tables'])} table(s) use an unsupported layout. "
        "Their original cells remain available above."
    )

if results:
    selected_index = st.selectbox(
        "Select an extracted entry",
        options=list(range(len(results))),
        format_func=lambda i: (
            f"{i + 1}. {results[i]['query']['product_name'] or 'Missing product name'}"
            f" · {results[i].get('table_evidence', {}).get('group', 'Labelled item')}"
        ),
        key=(f"pdf_candidate_{fingerprint}_{page_number}_"
             f"{analysis.get('ocr', {}).get('result_sha256', 'native')}"),
    )
    selected = results[selected_index]
    st.write("Reference status:", selected["decision"]["status"])
    st.write("Reason:", selected["decision"]["reason"])
    with st.expander("Extracted fields, source evidence and matching result"):
        st.json(selected)
else:
    st.info("No entries were extracted with the supported layout rules.")

if extracted["conditional_rules"]:
    with st.expander("Source conditions requiring review"):
        st.json(extracted["conditional_rules"])

matching_export = {
    **export,
    "catalogue_id": catalogue["dataset_id"],
    "catalogue_reviewed_on": catalogue["reviewed_on"],
    "catalogue_sha256": hashlib.sha256(catalogue_bytes).hexdigest(),
    "results": results,
    "conditional_rules": extracted["conditional_rules"],
    "skipped_tables": extracted["skipped_tables"],
}
st.download_button(
    "Download page matching results",
    data=json.dumps(matching_export, ensure_ascii=False, indent=2),
    file_name=f"strata_{fingerprint[:10]}_page_{page_number}_matching.json",
    mime="application/json",
)

if results:
    st.divider()
    st.subheader("Review selected entry")
    st.caption(
        "Supply verified product details and an evidence note. "
        "Choose Synthetic test for practice submissions. "
        "Each submission is saved separately from the extracted result above."
    )

    record_key = pdf_review_key(selected)
    history_path = ROOT / "data/reviews/reviews.sqlite3"
    try:
        history = load_history(history_path, record_key)
    except (OSError, sqlite3.Error) as error:
        st.error(f"Could not read review history: {error}")
        st.stop()

    defaults = history[-1]["reviewed_query"] if history else selected["query"]
    with st.form(f"pdf_review_{record_key}"):
        kind = st.segmented_control(
            "Review type", ["Evidence-based review", "Synthetic test"],
            default=("Synthetic test" if origin == "synthetic_scan_example"
                     else "Evidence-based review"),
            key=f"pdf_kind_{record_key}",
        )
        product = st.text_input(
            "Product name", value=defaults.get("product_name") or "",
            key=f"pdf_product_{record_key}",
        )
        manufacturer = st.text_input(
            "Manufacturer", value=defaults.get("manufacturer") or "",
            key=f"pdf_manufacturer_{record_key}",
        )
        month = st.text_input(
            "Manufacture month (YYYY-MM)",
            value=defaults.get("manufacture_month") or "",
            help="Leave unknown dates blank. A sales date is a different fact.",
            key=f"pdf_month_{record_key}",
        )
        reviewer = st.text_input(
            "Reviewer name", help="Self-reported name for this prototype.",
            key=f"pdf_reviewer_{record_key}",
        )
        note = st.text_area(
            "Evidence or reason for this review", key=f"pdf_note_{record_key}",
        )
        submitted = st.form_submit_button("Run matching and save PDF review")

    if submitted:
        kind_code = {
            "Evidence-based review": "evidence_based_review",
            "Synthetic test": "synthetic_test",
        }.get(kind)
        context = {
            "document_origin": origin,
            "document_name": filename,
            "raw_page_text": analysis["text"],
            "conditional_rules": extracted["conditional_rules"],
            "text_extraction_method": analysis["extraction_method"],
        }
        try:
            event = save_pdf_review(
                history_path, selected, catalogue_bytes,
                {"product_name": product, "manufacturer": manufacturer,
                 "manufacture_month": month},
                reviewer, note, kind_code, context,
            )
        except (OSError, sqlite3.Error, ValueError, KeyError) as error:
            st.error(f"Review was not saved: {error}")
        else:
            history.append(event)
            st.success("PDF review saved.")

    if history:
        latest = history[-1]
        st.subheader("Last submitted PDF review")
        if latest["review_kind"] == "synthetic_test":
            st.warning("Synthetic test submission — uses practice details.")
        st.caption(
            f"{latest['saved_at_utc']} · Reviewer: {latest['reviewer']}"
        )
        st.write("Submitted reference status:",
                 latest["review_result"]["decision"]["status"])
        st.write("Reason:", latest["review_result"]["decision"]["reason"])
        st.json(latest["reviewed_query"])
        with st.expander(f"PDF review history ({len(history)} submissions)"):
            st.json(history)
        st.download_button(
            "Download PDF review history",
            data=json.dumps(history, ensure_ascii=False, indent=2),
            file_name=f"strata_pdf_{record_key[:12]}_reviews.json",
            mime="application/json", key=f"pdf_history_{record_key}",
        )
    else:
        st.caption("No reviews have been submitted for this PDF entry.")

