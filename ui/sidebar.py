import streamlit as st

from services.dataset_service import get_sources


def render_sidebar():

    with st.sidebar:

        st.markdown(
            """
            # 🇮🇳 India Data Explorer

            Government dataset discovery
            platform
            """
        )

        st.divider()

        st.markdown("### Navigation")

        page = st.radio(
            "",
            [
                "🏠 Overview",
                "🔎 Explore Datasets",
                "🚬 Oral Cancer Projection"
            ],
            label_visibility="collapsed"
        )

        st.divider()

        st.markdown("### Sources")

        sources = get_sources()

        if sources:

            for source in sources:
                st.markdown(
                    f"• {source}"
                )

        else:

            st.caption(
                "No sources available"
            )

    return page