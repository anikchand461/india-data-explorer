import streamlit as st

from services.search import search_datasets
from services.dataset_service import (
    get_categories,
    get_sources
)


def render_search():

    st.title("🔎 Explore Government Datasets")

    st.write(
        "Search and discover datasets from Indian "
        "government data sources."
    )

    query = st.text_input(
        "Search datasets",
        placeholder="e.g. vaccination, population, agriculture..."
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        sources = get_sources()

        source = st.selectbox(
            "Source",
            ["All"] + sources
        )

    with col2:

        categories = get_categories()

        category = st.selectbox(
            "Category",
            ["All"] + categories
        )

    with col3:

        granularity = st.selectbox(
            "Granularity",
            [
                "All",
                "National",
                "State",
                "District",
                "Household",
                "Individual"
            ]
        )

    results = search_datasets(
        query=query,
        source=None if source == "All" else source,
        category=None if category == "All" else category,
        granularity=(
            None
            if granularity == "All"
            else granularity
        )
    )

    st.divider()

    st.write(
        f"### {len(results)} datasets found"
    )

    if not results:

        st.info(
            "No datasets found. Run the ingestion "
            "script after configuring a data source."
        )

        return

    for dataset in results:

        with st.container(border=True):

            st.subheader(dataset["name"])

            if dataset["description"]:
                st.write(
                    dataset["description"]
                )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.caption("Source")
                st.write(dataset["source"])

            with col2:
                st.caption("Organization")
                st.write(
                    dataset["organization"]
                    or "Not specified"
                )

            with col3:
                st.caption("Granularity")
                st.write(
                    dataset["granularity"]
                    or "Not specified"
                )

            if st.button(
                "View Dataset",
                key=f"dataset_{dataset['id']}"
            ):
                st.session_state[
                    "selected_dataset"
                ] = dataset["id"]

                st.rerun()