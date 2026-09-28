import json

import pandas as pd
import streamlit as st

from services.dataset_service import get_dataset
from services.extraction import extract_data_gov


def render_dataset(dataset_id):

    dataset = get_dataset(dataset_id)

    if not dataset:

        st.error("Dataset not found.")

        if st.button("← Back"):
            st.session_state.pop(
                "selected_dataset",
                None
            )
            st.rerun()

        return

    if st.button("← Back to Search"):

        st.session_state.pop(
            "selected_dataset",
            None
        )

        st.rerun()

    st.title(dataset["name"])

    if dataset["description"]:
        st.write(dataset["description"])

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### Source")

        st.write(
            dataset["source"]
            or "Not specified"
        )

        st.markdown("### Organization")

        st.write(
            dataset["organization"]
            or "Not specified"
        )

        st.markdown("### Category")

        st.write(
            dataset["category"]
            or "Not specified"
        )

        st.markdown("### Geography")

        st.write(
            dataset["geographic_level"]
            or "Not specified"
        )

    with col2:

        st.markdown("### Granularity")

        st.write(
            dataset["granularity"]
            or "Not specified"
        )

        st.markdown("### Period")

        period = ""

        if dataset["start_date"]:
            period += dataset["start_date"]

        if dataset["end_date"]:
            period += f" → {dataset['end_date']}"

        st.write(
            period or "Not specified"
        )

        st.markdown("### Access")

        st.write(
            dataset["access_type"]
            or "Not specified"
        )

        st.markdown("### Format")

        st.write(
            dataset["format"]
            or "Not specified"
        )

    st.divider()

    st.markdown("### Availability")

    col1, col2, col3 = st.columns(3)

    with col1:

        if dataset["api_available"]:

            st.success("✓ API Available")

        else:

            st.warning("API unavailable")

    with col2:

        if dataset["download_available"]:

            st.success("✓ Download Available")

        else:

            st.info("Download unavailable")

    with col3:

        if dataset["source_url"]:

            st.link_button(
                "Open Source",
                dataset["source_url"]
            )

    if dataset["api_available"]:

        st.divider()

        st.markdown("### 📊 Extract Data")

        limit = st.number_input(
            "Number of records",
            min_value=1,
            max_value=10000,
            value=100
        )

        if st.button(
            "Fetch Data",
            type="primary"
        ):

            try:

                resource_id = dataset["external_id"]

                df = extract_data_gov(
                    resource_id,
                    limit=limit
                )

                if df.empty:

                    st.warning(
                        "No records returned."
                    )

                else:

                    st.success(
                        f"Fetched {len(df)} records."
                    )

                    st.dataframe(
                        df,
                        use_container_width=True
                    )

                    csv = df.to_csv(
                        index=False
                    ).encode("utf-8")

                    st.download_button(
                        "⬇ Download CSV",
                        csv,
                        file_name=(
                            f"{dataset['name']}.csv"
                        ),
                        mime="text/csv"
                    )

            except Exception as error:

                st.error(
                    f"Extraction failed: {error}"
                )