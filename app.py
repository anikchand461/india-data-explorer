import streamlit as st
from dotenv import load_dotenv

from database.database import initialize_database
from services.dataset_service import get_statistics
from ui.sidebar import render_sidebar
from ui.search import render_search
from ui.dataset import render_dataset
from ui.oral_cancer_map import render_oral_cancer_simulation


load_dotenv()

st.set_page_config(
    page_title="India Data Explorer",
    page_icon="🇮🇳",
    layout="wide"
)


initialize_database()


def render_overview():

    st.title("🇮🇳 India Data Explorer")

    st.markdown(
        """
        ### Indian Government Data Discovery Platform

        Search, explore and extract datasets from
        Indian government data sources.
        """
    )

    stats = get_statistics()

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Datasets",
            stats["total"]
        )

    with col2:

        st.metric(
            "Sources",
            stats["sources"]
        )

    with col3:

        st.metric(
            "Categories",
            stats["categories"]
        )

    with col4:

        st.metric(
            "API Datasets",
            stats["api_count"]
        )

    st.divider()

    st.markdown("## What can you explore?")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            """
            ### 🏥 Health

            Health, vaccination, nutrition,
            maternal and child health data.
            """
        )

    with col2:

        st.markdown(
            """
            ### 👥 Population

            Census, demographic and
            population datasets.
            """
        )

    with col3:

        st.markdown(
            """
            ### 🌾 Agriculture

            Crops, irrigation, agricultural
            production and related datasets.
            """
        )

    st.info(
        "More sources will be added progressively."
    )


page = render_sidebar()


if page == "🏠 Overview":

    if "selected_dataset" in st.session_state:

        st.session_state.pop(
            "selected_dataset",
            None
        )

    render_overview()


elif page == "🔎 Explore Datasets":

    if "selected_dataset" in st.session_state:

        render_dataset(
            st.session_state["selected_dataset"]
        )

    else:

        render_search()


elif page == "🚬 Oral Cancer Projection":

    if "selected_dataset" in st.session_state:

        st.session_state.pop(
            "selected_dataset",
            None
        )

    render_oral_cancer_simulation()