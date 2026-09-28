import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from services.hpv_simulation import simulate

GEOJSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "geo" / "india_states.geojson"
)


@st.cache_data
def load_geojson():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def render_hpv_simulation():

    st.title("🧬 HPV Vaccination Population-Impact Simulation")

    st.warning(
        "This is a SIMULATION built on real population and "
        "geography data plus published public-health reference "
        "assumptions -- it is not a measurement of actual "
        "vaccination coverage or outcomes. India has no HPV "
        "vaccination coverage dataset yet (the vaccine's national "
        "rollout is recent), so this models a hypothetical scenario."
    )

    with st.expander("What's real data vs. what's an assumption?"):

        st.markdown(
            """
            **Real data:**
            - State boundaries: 2011 Census (PC11) state polygons,
              from AI Kosh / Development Data Lab's SHRUG dataset.
            - State population: 2011 Census of India official totals
              (undivided-state boundaries, matching the geometry).

            **Modeling assumptions (published public-health
            reference values, not from our dataset catalogue):**
            - Girls aged 9-14 (WHO's primary HPV vaccination
              cohort) ≈ 5.8% of total population, estimated from the
              2011 Census age structure.
            - Cervical cancer incidence: 18 per 100,000 women/year,
              India's national rate (GLOBOCAN 2020), applied
              **uniformly across all states** -- reliable per-state
              incidence rates aren't available from one consistent
              source, so map variation below reflects real
              population differences, not differential regional risk.
            - Vaccine efficacy: 90%, within published clinical trial
              ranges against covered HPV strains.
            """
        )

    render_simulation_fragment()


@st.fragment
def render_simulation_fragment():

    coverage = st.slider(
        "Assumed vaccination coverage scenario (%)",
        min_value=0,
        max_value=100,
        value=50,
        step=5
    )

    results = simulate(coverage)

    rows = [
        {"state": state, **values}
        for state, values in results.items()
    ]

    df = pd.DataFrame(rows)

    total_avoided = df["cases_avoided_per_year"].sum()
    total_vaccinated = df["vaccinated_girls"].sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Girls vaccinated (scenario)",
            f"{total_vaccinated:,.0f}"
        )

    with col2:
        st.metric(
            "Est. cervical cancer cases avoided / year",
            f"{total_avoided:,.0f}"
        )

    with col3:
        st.metric(
            "Coverage scenario",
            f"{coverage}%"
        )

    st.divider()

    geojson = load_geojson()

    fig = px.choropleth(
        df,
        geojson=geojson,
        featureidkey="properties.s_name",
        locations="state",
        color="cases_avoided_per_year",
        color_continuous_scale="Reds",
        labels={
            "cases_avoided_per_year": "Cases avoided/year"
        },
        hover_data={
            "population": ":,",
            "eligible_girls": ":,",
            "vaccinated_girls": ":,",
            "cases_avoided_per_year": ":,.1f",
            "state": False
        }
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=600
    )

    st.plotly_chart(fig, width="stretch")

    st.divider()

    st.markdown("### Per-state detail")

    st.dataframe(
        df.sort_values(
            "cases_avoided_per_year",
            ascending=False
        ),
        width="stretch",
        hide_index=True
    )
