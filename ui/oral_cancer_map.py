import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from services.oral_cancer_simulation import (
    simulate,
    SWEDEN_BENCHMARK_REDUCTION_PCT,
)

GEOJSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "geo" / "india_states.geojson"
)


@st.cache_data
def load_geojson():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def render_oral_cancer_simulation():

    st.title("🚬 Oral Cancer Risk & Tobacco-Reduction Projection")

    st.warning(
        "This replaces the earlier HPV simulation's flat national "
        "rate with REAL state-by-state variation. The oral cancer "
        "risk map below is driven by actual NFHS-5 tobacco-use "
        "data per state, per sex -- it is not a uniform assumption."
    )

    with st.expander("What's real data vs. what's an assumption?"):

        st.markdown(
            """
            **Real data:**
            - Tobacco use by state and sex: NFHS-5 (2019-21) official
              Table 2.36, transcribed directly from the DHS/MoHFW
              report -- ranges from 0.4% (Punjab, women) to 73.1%
              (Mizoram, men).
            - National oral cancer incidence: 10.4 per 100,000
              (age-standardized), National Cancer Registry Programme.
            - State population: 2011 Census totals.

            **Modeling assumption:** each state's oral cancer risk is
            scaled relative to its real tobacco-use rate vs. the
            national average, applied to the national baseline
            incidence. Tobacco/smokeless tobacco is the established
            dominant driver of oral cancer in India, but no
            consistent state-by-state cancer-incidence dataset
            exists to measure this directly -- so this is a
            transparent proxy, not a measured rate.

            **On "Sweden":** the literature does **not** support
            "snus reduces oral cancer" as a direct mechanism --
            pooled studies of Swedish snus users show a *null*
            association with oral cancer specifically. What Sweden
            genuinely achieved is 44% lower tobacco-related
            mortality than the EU average, via smokers switching
            from cigarettes to snus. That 44% is used below as a
            **policy-ambition benchmark** -- what a comparable
            reduction in India's own real oral-cancer driver
            (smokeless tobacco use) would project to -- not a claim
            that snus itself lowers oral cancer risk.
            """
        )

    render_simulation_fragment()


@st.fragment
def render_simulation_fragment():

    col_a, col_b = st.columns(2)

    with col_a:
        sex = st.radio(
            "Population",
            ["combined", "men", "women"],
            format_func=lambda s: s.capitalize(),
            horizontal=True
        )

    with col_b:
        st.caption(
            f"Sweden's documented tobacco-reduction achievement: "
            f"{SWEDEN_BENCHMARK_REDUCTION_PCT}%"
        )

    reduction = st.slider(
        "Assumed reduction in tobacco use scenario (%) "
        f"-- Sweden benchmark = {SWEDEN_BENCHMARK_REDUCTION_PCT}%",
        min_value=0,
        max_value=100,
        value=SWEDEN_BENCHMARK_REDUCTION_PCT,
        step=5
    )

    results = simulate(reduction, sex=sex)

    rows = [
        {"state": state, **values}
        for state, values in results.items()
    ]

    df = pd.DataFrame(rows)

    total_baseline = df["baseline_annual_cases"].sum()
    total_avoided = df["cases_avoided_per_year"].sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Est. baseline oral cancer cases / year",
            f"{total_baseline:,.0f}"
        )

    with col2:
        st.metric(
            "Est. cases avoided under this scenario",
            f"{total_avoided:,.0f}"
        )

    with col3:
        st.metric(
            "Reduction scenario",
            f"{reduction}%"
        )

    st.divider()

    st.markdown(
        "#### Real state-level oral cancer risk "
        "(driven by NFHS-5 tobacco data)"
    )

    geojson = load_geojson()

    fig_risk = px.choropleth(
        df,
        geojson=geojson,
        featureidkey="properties.s_name",
        locations="state",
        color="incidence_per_100k",
        color_continuous_scale="Oranges",
        labels={
            "incidence_per_100k": "Est. incidence /100k"
        },
        hover_data={
            "tobacco_use_pct": ":.1f",
            "relative_risk": ":.2f",
            "incidence_per_100k": ":.1f",
            "state": False
        }
    )

    fig_risk.update_geos(fitbounds="locations", visible=False)
    fig_risk.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=550
    )

    st.plotly_chart(fig_risk, width="stretch", key="risk_map")

    st.caption(
        "This map reflects REAL geographic variation in tobacco "
        "use (NFHS-5) -- it does not change with the slider above, "
        "since it shows current relative risk, not a future "
        "scenario."
    )

    st.divider()

    st.markdown("#### Per-state detail")

    st.dataframe(
        df.sort_values(
            "cases_avoided_per_year",
            ascending=False
        ),
        width="stretch",
        hide_index=True
    )
