import streamlit as st


st.set_page_config(
    page_title="Strata",
    page_icon=":material/architecture:",
    layout="wide",
)

page = st.navigation([
    st.Page(
        "app_pages/saved_reviews.py",
        title="Saved reviews",
        icon=":material/fact_check:",
        default=True,
    ),
    st.Page(
        "app_pages/process_pdf.py",
        title="Process PDF",
        icon=":material/description:",
    ),
])

page.run()