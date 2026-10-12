"""
Oral Cancer & Tobacco page: burden, state and district maps, NFHS-5 ->
NFHS-6 trend, who uses tobacco, the attributable-fraction projection,
and sources. All data comes from services/oral_cancer_model.py.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services import oral_cancer_model as model

# Categorical slots 1-2 (validated for CVD separation on both surfaces):
# men = blue, women = orange. Combined/overall = aqua (slot 3).
SERIES = {
    "dark": {"Men": "#3987e5", "Women": "#d95926", "Both": "#199e70"},
    "light": {"Men": "#2a78d6", "Women": "#eb6834", "Both": "#1baf7a"},
}

BLUE_RAMP = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
    "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281",
    "#0d366b",
]

NEUTRAL = {"dark": "#383835", "light": "#e4e3df"}

# Simple ranked bars don't need zoom/pan, and the toolbar would sit on
# top of the "India" reference label.
BARS_CONFIG = {"displayModeBar": False}
MUTED_TEXT = {"dark": "#c3c2b7", "light": "#52514e"}
NO_DATA = {"dark": "#2a2a28", "light": "#f0efec"}


def theme():

    try:
        return "light" if st.context.theme.type == "light" else "dark"
    except Exception:
        return "dark"


def series_color(name):

    return SERIES[theme()][name]


def sequential_scale():

    # Near-zero recedes toward the surface: light steps on a light
    # page, dark steps on a dark page.
    ramp = BLUE_RAMP if theme() == "light" else BLUE_RAMP[::-1][1:]

    stops = len(ramp) - 1

    return [[i / stops, c] for i, c in enumerate(ramp)]


def metric_color(column):
    """Single-series charts take the colour of the group they show."""

    if column.startswith("men"):
        return series_color("Men")

    if column.startswith("women"):
        return series_color("Women")

    return series_color("Both")


def diverging_scale():
    """Blue = fell / below average, red = rose / above average."""

    mid = NEUTRAL[theme()]

    blue, red = ("#2a78d6", "#e34948") if theme() == "light" else (
        "#3987e5", "#e66767"
    )

    return [[0, blue], [0.5, mid], [1, red]]


def style(fig, height=None):

    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": 1.08, "x": 0},
        hoverlabel={"align": "left"},
    )

    if height:
        fig.update_layout(height=height)

    return fig


def fmt(value, unit):

    if value is None or pd.isna(value):
        return "–"

    if unit is None or isinstance(value, str):
        return str(value)

    if unit == "%":
        return f"{value:.1f}%"

    if unit == "pp":
        return f"{value:+.1f} pp"

    if unit == "x":
        return f"{value:.2f}×"

    if unit == "lakh":
        return f"₹{value:,.2f} lakh"

    return f"{value:,.0f}"


# --- Map ---------------------------------------------------------------

def bounds(geojson):
    """(lon_min, lat_min, lon_max, lat_max) over every coordinate."""

    lons, lats = [], []

    def walk(coords):
        if isinstance(coords[0], (int, float)):
            lons.append(coords[0])
            lats.append(coords[1])
        else:
            for c in coords:
                walk(c)

    for feature in geojson["features"]:
        walk(feature["geometry"]["coordinates"])

    return min(lons), min(lats), max(lons), max(lats)


def choropleth(
    df, geojson, id_col, value_col, label, unit, hover,
    diverging=False, midpoint=0.0, height=560,
):
    """
    df: one row per feature to colour; features in geojson without a
    row (no data / disputed) are drawn in a flat no-data grey.
    hover: list of (column, label, unit) shown in the tooltip.
    """

    all_ids = [f["id"] for f in geojson["features"]]

    fig = go.Figure()

    fig.add_trace(go.Choropleth(
        geojson=geojson,
        locations=all_ids,
        z=[0] * len(all_ids),
        colorscale=[[0, NO_DATA[theme()]], [1, NO_DATA[theme()]]],
        showscale=False,
        marker_line_color=NEUTRAL[theme()],
        marker_line_width=0.4,
        hovertemplate="%{location}<br>No data<extra></extra>",
    ))

    data = df.dropna(subset=[value_col])

    customdata = data[[c for c, _, _ in hover]].to_numpy()

    hover_lines = [f"<b>%{{customdata[0]}}</b>"] + [
        f"{lbl}: %{{customdata[{i}]}}"
        for i, (_, lbl, _) in enumerate(hover) if i > 0
    ]

    display = data[[c for c, _, _ in hover]].copy()

    for column, _, u in hover[1:]:
        display[column] = [fmt(v, u) for v in data[column]]

    zmin, zmax = data[value_col].min(), data[value_col].max()

    trace = dict(
        geojson=geojson,
        locations=data[id_col],
        z=data[value_col],
        customdata=display.to_numpy(),
        hovertemplate="<br>".join(hover_lines) + "<extra></extra>",
        marker_line_color=NEUTRAL[theme()],
        marker_line_width=0.5,
        colorbar={
            "title": {"text": label, "side": "right"},
            "thickness": 12,
            "len": 0.8,
        },
    )

    if diverging:
        span = max(abs(zmax - midpoint), abs(zmin - midpoint)) or 1
        trace.update(
            colorscale=diverging_scale(),
            zmid=midpoint,
            zmin=midpoint - span,
            zmax=midpoint + span,
        )
    else:
        trace.update(colorscale=sequential_scale())

    fig.add_trace(go.Choropleth(**trace))

    lon_min, lat_min, lon_max, lat_max = bounds(geojson)
    pad = 0.03 * max(lon_max - lon_min, lat_max - lat_min)

    fig.update_geos(
        visible=False,
        bgcolor="rgba(0,0,0,0)",
        projection_type="mercator",
        lonaxis_range=[lon_min - pad, lon_max + pad],
        lataxis_range=[lat_min - pad, lat_max + pad],
    )

    return style(fig, height)


def ranked_bars(df, label_col, value_col, unit, color, height=None,
                reference=None, reference_label=None):

    data = df.dropna(subset=[value_col]).sort_values(value_col)

    fig = go.Figure(go.Bar(
        x=data[value_col],
        y=data[label_col],
        orientation="h",
        marker_color=color,
        marker_line_width=0,
        customdata=[fmt(v, unit) for v in data[value_col]],
        hovertemplate="%{y}: %{customdata}<extra></extra>",
    ))

    if reference is not None:
        fig.add_vline(
            x=reference, line_width=1, line_dash="dot",
            line_color=MUTED_TEXT[theme()],
            annotation_text=reference_label,
            annotation_position="top",
            annotation_font_color=MUTED_TEXT[theme()],
        )

    fig.update_layout(bargap=0.25, showlegend=False)
    fig.update_yaxes(tickfont={"size": 11})
    fig.update_xaxes(showgrid=True, zeroline=False)

    return style(fig, height or max(320, 18 * len(data) + 60))


def csv_download(df, filename, label="Download this table (CSV)"):

    st.download_button(
        label,
        df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


# --- Page --------------------------------------------------------------

def render_oral_cancer_page():

    st.title("🚬 Oral Cancer & Tobacco in India")

    st.markdown(
        "Oral cavity cancer is one of India's most common cancers, and "
        "the leading cancer in men in several registry areas. Its "
        "biggest preventable cause is **smokeless tobacco** (gutkha, "
        "khaini, paan with tobacco). This page combines nine data "
        "sources: the national cancer registry, three survey rounds, "
        "district fact sheets for all 707 districts, and district "
        "tobacco control budgets. It shows where the risk sits, who "
        "carries it, how it is changing, where the money goes, and what "
        "reducing tobacco use could achieve."
    )

    # Nine sections overflow a tab strip, so they are pills that wrap;
    # only the chosen section is rendered.
    choice = st.pills(
        "Section", list(SECTIONS), default=next(iter(SECTIONS)),
        key="oral_section", label_visibility="collapsed",
    )

    # Clicking the selected pill again deselects it; stay put instead.
    if choice is None:
        choice = st.session_state.get("oral_section_last",
                                      next(iter(SECTIONS)))

    st.session_state["oral_section_last"] = choice

    st.divider()

    SECTIONS[choice]()


# --- Tab: burden -------------------------------------------------------

def key_findings():

    states = model.load_state_frame()
    districts = model.load_district_frame()
    background = model.load_background()
    national = model.load_national()
    stage = model.load_stage().set_index("stage")
    _, summary = model.project()

    findings = []

    men6 = states.dropna(subset=["men_tobacco_nfhs6"])
    hi = men6.loc[men6["men_tobacco_nfhs6"].idxmax()]
    lo = men6.loc[men6["men_tobacco_nfhs6"].idxmin()]
    findings.append(
        f"**Men's tobacco use differs about "
        f"{hi['men_tobacco_nfhs6'] / lo['men_tobacco_nfhs6']:.0f}-fold "
        f"between states**: {hi['men_tobacco_nfhs6']:.1f}% in "
        f"{hi['state']} vs {lo['men_tobacco_nfhs6']:.1f}% in "
        f"{lo['state']} (NFHS-6, 2023-24)."
    )

    clean = districts[~districts["disputed"]]
    spread = clean.groupby("state")["men_tobacco_pct"].agg(["min", "max"])
    spread["gap"] = spread["max"] - spread["min"]
    widest = spread["gap"].idxmax()
    in_state = clean[clean["state"] == widest]
    d_lo = in_state.loc[in_state["men_tobacco_pct"].idxmin()]
    d_hi = in_state.loc[in_state["men_tobacco_pct"].idxmax()]
    findings.append(
        f"**State averages hide large district gaps.** Within "
        f"{widest}, men's tobacco use ranges from "
        f"{d_lo['men_tobacco_pct']:.1f}% ({d_lo['district']}) to "
        f"{d_hi['men_tobacco_pct']:.1f}% ({d_hi['district']})."
    )

    fell = (states["men_tobacco_change_pp"] < 0).sum()
    rose = states.dropna(subset=["men_tobacco_change_pp"])
    rose = rose[rose["men_tobacco_change_pp"] > 0]
    findings.append(
        f"**Tobacco use is falling, slowly.** Nationally, men's use "
        f"went from {national['men_tobacco_nfhs5']:.1f}% to "
        f"{national['men_tobacco_nfhs6']:.1f}% and women's from "
        f"{national['women_tobacco_nfhs5']:.1f}% to "
        f"{national['women_tobacco_nfhs6']:.1f}% (2019-21 → 2023-24). "
        f"It fell for men in {fell} states/UTs but rose in "
        f"{len(rose)}, most in "
        f"{', '.join(rose.sort_values('men_tobacco_change_pp', ascending=False)['state'].head(4))}."
    )

    wealth = background[
        (background["dimension"] == "Wealth quintile")
        & (background["sex"] == "Men")
    ].set_index("group")["total_pct"]
    school = background[
        (background["dimension"] == "Schooling")
        & (background["sex"] == "Women")
    ].set_index("group")["total_pct"]
    findings.append(
        f"**It is concentrated among the poorest and least schooled.** "
        f"{wealth['Lowest']:.1f}% of men in the poorest wealth quintile "
        f"use tobacco, vs {wealth['Highest']:.1f}% in the richest. "
        f"Women with no schooling use it at "
        f"{school['No schooling']:.1f}%, vs "
        f"{school['12 or more years complete']:.1f}% with 12+ years."
    )

    smokeless = national["gats_smokeless_only"] + national["gats_both"]
    findings.append(
        f"**Most users chew rather than smoke.** "
        f"{smokeless / national['gats_current'] * 100:.0f}% of tobacco "
        f"users use smokeless products, alone or with smoking (GATS-2). "
        f"That form drives oral cancer."
    )

    findings.append(
        f"**Almost nobody is screened, and most cases are found late.** "
        f"Only {national['women_oral_screening']:.1f}% of women and "
        f"{national['men_oral_screening']:.1f}% of men aged 30-49 have "
        f"ever had an oral cavity exam (NFHS-5). Only "
        f"{stage.at['Localised only', 'both_pct']:.1f}% of mouth "
        f"cancers are still localised at diagnosis (NCRP)."
    )

    findings.append(
        f"**About {summary['attributable_pct']:.0f}% of oral cancer is "
        f"attributable to tobacco** under the default model "
        f"assumptions. A 44% cut in tobacco use (Sweden's benchmark) "
        f"would therefore prevent roughly a fifth of cases in the long "
        f"run, not 44%. See the Projection model tab."
    )

    return findings


def render_burden():

    national = model.load_national()
    proj = model.load_ncrp_projections()
    oral = proj[proj["site"] == "Oral cavity (tongue + mouth)"]

    def cases(sex, year):
        return oral[(oral["sex"] == sex) & (oral["year"] == year)][
            "cases"
        ].iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "New oral cavity cancers, 2025 (projected)",
        f"{cases('Both', 2025):,.0f}",
        f"{cases('Both', 2025) - cases('Both', 2020):+,.0f} vs 2020",
        delta_color="inverse",
        help="NCRP 2020, Table 14.1: tongue (C01-C02) + mouth "
             "(C03-C06), both sexes.",
    )
    c2.metric(
        "Share in men",
        f"{cases('Men', 2025) / cases('Both', 2025) * 100:.0f}%",
        help="NCRP 2020 projections for 2025.",
    )
    c3.metric(
        "Men / women 15+ using tobacco",
        f"{national['men_tobacco_nfhs6']:.1f}% / "
        f"{national['women_tobacco_nfhs6']:.1f}%",
        help="NFHS-6 (2023-24) fact sheets.",
    )
    c4.metric(
        "Women / men 30-49 ever screened",
        f"{national['women_oral_screening']:.1f}% / "
        f"{national['men_oral_screening']:.1f}%",
        help="Ever had an oral cavity exam for oral cancer. NFHS-5 "
             "(2019-21) fact sheets.",
    )

    st.markdown("#### Key findings")

    for finding in key_findings():
        st.markdown(f"- {finding}")

    st.divider()

    left, right = st.columns(2)

    with left:

        st.markdown("##### Projected new oral cavity cancers per year")

        fig = go.Figure()

        for sex in ("Men", "Women"):

            data = oral[oral["sex"] == sex].sort_values("year")

            fig.add_trace(go.Scatter(
                x=data["year"], y=data["cases"], name=sex,
                mode="lines+markers",
                line={"color": series_color(sex), "width": 2},
                marker={"size": 8},
                hovertemplate=f"{sex}, %{{x}}: %{{y:,.0f}}<extra></extra>",
            ))

            last = data.iloc[-1]
            fig.add_annotation(
                x=last["year"], y=last["cases"],
                text=f"{sex} {last['cases']:,.0f}",
                showarrow=False, xanchor="left", xshift=8,
                font={"color": MUTED_TEXT[theme()], "size": 12},
            )

        fig.update_yaxes(rangemode="tozero", tickformat=",")
        fig.update_xaxes(range=[2015.5, 2027.5], dtick=1)
        st.plotly_chart(style(fig, 340), width="stretch")

        st.caption(
            "NCRP 2020 (ICMR-NCDIR), Table 14.1. 2021-2024 are not "
            "published; the line joins 2020 to 2025."
        )

    with right:

        st.markdown("##### How far mouth cancer has spread at diagnosis")

        stage = model.load_stage()

        fig = go.Figure(go.Bar(
            x=stage["both_pct"], y=stage["stage"], orientation="h",
            marker_color=series_color("Both"),
            text=[f"{v:.1f}%" for v in stage["both_pct"]],
            textposition="outside",
            hovertemplate=(
                "%{y}: %{x:.1f}% (%{customdata:,} cases)<extra></extra>"
            ),
            customdata=stage["both_n"],
        ))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(range=[0, 80], ticksuffix="%")
        st.plotly_chart(style(fig, 340), width="stretch")

        st.caption(
            f"NCRP 2020, Table 9.2.1: {stage['both_n'].sum():,} mouth "
            "cancer patients in hospital-based registries. Cancer "
            "caught while localised is far more treatable."
        )


# --- Tab: states -------------------------------------------------------

STATE_METRICS = {
    "Tobacco use": {
        "Men 15+ (NFHS-6, 2023-24)": ("men_tobacco_nfhs6", "%", False),
        "Women 15+ (NFHS-6, 2023-24)": ("women_tobacco_nfhs6", "%", False),
        "Men 15+ (NFHS-5, 2019-21)": ("men_tobacco_nfhs5", "%", False),
        "Women 15+ (NFHS-5, 2019-21)": ("women_tobacco_nfhs5", "%", False),
        "Men, rural (NFHS-6)": ("men_tobacco_rural_nfhs6", "%", False),
        "Men, urban (NFHS-6)": ("men_tobacco_urban_nfhs6", "%", False),
        "Women, rural (NFHS-6)": ("women_tobacco_rural_nfhs6", "%", False),
        "Women, urban (NFHS-6)": ("women_tobacco_urban_nfhs6", "%", False),
    },
    "Change & gaps": {
        "Change in men's use, NFHS-5 → 6": (
            "men_tobacco_change_pp", "pp", True),
        "Change in women's use, NFHS-5 → 6": (
            "women_tobacco_change_pp", "pp", True),
        "Rural minus urban, men (NFHS-5)": (
            "men_tobacco_rural_urban_gap_pp", "pp", True),
        "Rural minus urban, women (NFHS-5)": (
            "women_tobacco_rural_urban_gap_pp", "pp", True),
    },
    "Type of tobacco": {
        "Smokeless share of tobacco users (GATS-2)": (
            "smokeless_share_pct", "%", False),
        "Adults using smokeless only (GATS-2)": (
            "smokeless_only_pct_gats2", "%", False),
        "Adults smoking only (GATS-2)": ("smoked_only_pct_gats2", "%", False),
    },
    "Quitting & exposure (NFHS-5, age 15-49)": {
        "Men users who tried to quit (past year)": (
            "men_tried_to_quit_pct", "%", False),
        "Women users who tried to quit (past year)": (
            "women_tried_to_quit_pct", "%", False),
        "Men users advised to quit by a health provider": (
            "men_advised_to_quit_pct", "%", False),
        "Women users advised to quit by a health provider": (
            "women_advised_to_quit_pct", "%", False),
        "Men exposed to second-hand smoke": (
            "men_secondhand_smoke_pct", "%", False),
        "Women exposed to second-hand smoke": (
            "women_secondhand_smoke_pct", "%", False),
    },
    "Screening & co-risks": {
        "Women 30-49 ever screened for oral cancer (NFHS-5)": (
            "women_oral_screening_nfhs5", "%", False),
        "Men 30-49 ever screened for oral cancer (NFHS-5)": (
            "men_oral_screening_nfhs5", "%", False),
        "Men 15+ who drink alcohol (NFHS-6)": (
            "men_alcohol_nfhs6", "%", False),
        "Women 15+ who drink alcohol (NFHS-6)": (
            "women_alcohol_nfhs6", "%", False),
    },
    "Modelled burden (2025)": {
        "Estimated new oral cavity cancers": ("cases", "n", False),
        "Oral cancer rate relative to India (1 = average)": (
            "relative_rate", "x", True),
        "Share of cases attributable to tobacco": (
            "attributable_pct", "%", False),
    },
}


def state_table():

    df = model.load_state_frame().copy()

    df["smokeless_share_pct"] = df["smokeless_share_of_users"] * 100

    projection, _ = model.project()

    return df.merge(
        projection[["state", "cases", "relative_rate", "attributable_pct"]],
        on="state",
    )


def render_states():

    df = state_table()

    c1, c2 = st.columns([1, 2])

    with c1:
        group = st.selectbox("Topic", list(STATE_METRICS), key="st_group")

    with c2:
        name = st.selectbox(
            "Indicator", list(STATE_METRICS[group]), key="st_metric"
        )

    column, unit, diverging = STATE_METRICS[group][name]

    midpoint = 1.0 if unit == "x" else 0.0

    map_col, bar_col = st.columns([3, 2])

    with map_col:

        fig = choropleth(
            df, model.load_geojson("states"), "state", column, name, unit,
            hover=[
                ("state", "", None),
                (column, name, unit),
                ("men_tobacco_nfhs6", "Men's tobacco use (NFHS-6)", "%"),
                ("women_tobacco_nfhs6", "Women's tobacco use (NFHS-6)", "%"),
                ("smokeless_share_pct", "Smokeless share of users", "%"),
            ],
            diverging=diverging, midpoint=midpoint, height=620,
        )
        st.plotly_chart(fig, width="stretch", key="state_map")

    with bar_col:

        reference = None
        reference_label = None
        if unit == "x":
            reference, reference_label = 1.0, "India"

        st.plotly_chart(
            ranked_bars(
                df, "state", column, unit, metric_color(column),
                height=620, reference=reference,
                reference_label=reference_label,
            ),
            width="stretch", key="state_bars", config=BARS_CONFIG,
        )

    notes = []

    if "nfhs6" in column:
        notes.append(
            "Manipur was not surveyed in NFHS-6, so it shows no data."
        )

    if "gats2" in column or column == "smokeless_share_pct":
        notes.append(
            "GATS-2 (2016-17) has no row for Andaman & Nicobar, "
            "Lakshadweep, Dadra & Nagar Haveli and Daman & Diu, or "
            "Ladakh. The smokeless share uses the national mix for the "
            "first three and Jammu & Kashmir's for Ladakh."
        )

    if "tried_to_quit" in column or "advised" in column:
        notes.append(
            "Small UTs rest on very few tobacco users, so values like "
            "100% are statistically fragile."
        )

    if group == "Modelled burden (2025)":
        notes.append(
            "Model estimates, not measurements. See the Projection "
            "model tab for the method and adjustable assumptions."
        )

    for note in notes:
        st.caption(note)

    with st.expander("All state indicators as a table"):

        columns = ["state", "region"] + [
            c for metrics in STATE_METRICS.values()
            for c, _, _ in metrics.values()
        ]
        table = df[columns].round(2).sort_values("state")
        st.dataframe(table, width="stretch", hide_index=True)
        csv_download(table, "oral_cancer_state_indicators.csv")


# --- Tab: districts ----------------------------------------------------

DISTRICT_METRICS = {
    "Men 15+ using tobacco": ("men_tobacco_pct", "%", False),
    "Women 15+ using tobacco": ("women_tobacco_pct", "%", False),
    "Oral cancer risk index, men (India = 1)": ("risk_men", "x", True),
    "Oral cancer risk index, women (India = 1)": ("risk_women", "x", True),
    "Women 30-49 ever screened for oral cancer": (
        "women_oral_screening_pct", "%", False),
    "Men 15+ who drink alcohol": ("men_alcohol_pct", "%", False),
    "Women 15+ who drink alcohol": ("women_alcohol_pct", "%", False),
    "Women 6+ who ever attended school": (
        "female_ever_schooled_pct", "%", False),
}


def district_table():

    df = model.load_district_frame().copy()

    df["risk_men"] = model.district_risk("men")
    df["risk_women"] = model.district_risk("women")

    return df


def render_districts():

    df = district_table()

    st.markdown(
        "NFHS-5 (2019-21) district fact sheets cover all **707 "
        "districts**. A state average can hide very different district "
        "patterns, which matters for targeting screening and cessation "
        "services."
    )

    c1, c2 = st.columns(2)

    with c1:
        name = st.selectbox(
            "Indicator", list(DISTRICT_METRICS), key="dist_metric"
        )

    with c2:
        state = st.selectbox(
            "Zoom to state",
            ["All India"] + sorted(df["state"].unique()),
            key="dist_state",
        )

    column, unit, diverging = DISTRICT_METRICS[name]

    clean = df[~df["disputed"]]

    geojson = model.load_geojson("districts")

    if state != "All India":
        clean = clean[clean["state"] == state]
        geojson = {
            "type": "FeatureCollection",
            "features": [
                f for f in geojson["features"]
                if f["properties"]["state"] == state
            ],
        }

    fig = choropleth(
        clean, geojson, "district_id", column, name, unit,
        hover=[
            ("district", "", None),
            ("state", "State", None),
            (column, name, unit),
            ("men_tobacco_pct", "Men using tobacco", "%"),
            ("women_tobacco_pct", "Women using tobacco", "%"),
            ("women_oral_screening_pct", "Women screened (30-49)", "%"),
            ("households_surveyed", "Households surveyed", "n"),
        ],
        diverging=diverging, midpoint=1.0, height=640,
    )

    st.plotly_chart(fig, width="stretch", key="district_map")

    st.caption(
        "Grey districts have no reliable value: 9 districts (6 in "
        "Delhi, plus Mahoba, Mahrajganj and Dhule) where independent "
        "extractions of the fact sheets disagree. See Sources & "
        "caveats. Each district estimate rests on roughly 800-1,000 "
        "surveyed households, so small differences between districts "
        "are within sampling error."
    )

    st.markdown(f"##### Spread of “{name}” across districts, by state")

    st.caption(
        "Each dot is a district. States are sorted by their median "
        "district."
    )

    spread = df[~df["disputed"]].dropna(subset=[column])
    order = (
        spread.groupby("state")[column].median().sort_values().index
    )

    fig = go.Figure()

    fig.add_trace(go.Box(
        x=spread[column], y=spread["state"], orientation="h",
        boxpoints="all", jitter=0.4, pointpos=0,
        marker={"size": 5, "color": series_color("Both"), "opacity": 0.75},
        line={"color": MUTED_TEXT[theme()], "width": 1},
        fillcolor="rgba(0,0,0,0)",
        customdata=spread[["district"]].to_numpy(),
        hovertemplate=(
            "%{customdata[0]}, %{y}: %{x:.1f}<extra></extra>"
        ),
        showlegend=False,
    ))

    if state != "All India":
        sel = spread[spread["state"] == state]
        fig.add_trace(go.Scatter(
            x=sel[column], y=sel["state"], mode="markers",
            marker={"size": 9, "color": series_color("Women"),
                    "line": {"width": 2, "color": NO_DATA[theme()]}},
            customdata=sel[["district"]].to_numpy(),
            hovertemplate="%{customdata[0]}: %{x:.1f}<extra></extra>",
            showlegend=False,
        ))

    fig.update_yaxes(categoryorder="array", categoryarray=list(order))

    st.plotly_chart(style(fig, 18 * len(order) + 80), width="stretch")

    left, right = st.columns(2)

    ranked = spread.sort_values(column, ascending=False)
    if state != "All India":
        ranked = ranked[ranked["state"] == state]

    show = ["district", "state", column, "households_surveyed"]

    labels = {
        "district": "District", "state": "State", column: name,
        "households_surveyed": "Households surveyed",
    }

    with left:
        st.markdown("##### Highest 15")
        st.dataframe(
            ranked[show].head(15).round(2).rename(columns=labels),
            hide_index=True, width="stretch",
        )

    with right:
        st.markdown("##### Lowest 15")
        st.dataframe(
            ranked[show].tail(15).iloc[::-1].round(2).rename(columns=labels),
            hide_index=True, width="stretch",
        )

    with st.expander("All district indicators as a table"):
        columns = ["state", "district"] + [
            c for c, _, _ in DISTRICT_METRICS.values()
        ] + ["households_surveyed", "women_interviewed", "men_interviewed",
             "disputed", "patched_from_check_b"]
        table = df[columns].round(2)
        st.dataframe(table, width="stretch", hide_index=True)
        csv_download(table, "oral_cancer_district_indicators.csv")


# --- Tab: risk matrix --------------------------------------------------

# Most to least urgent: red, orange, amber, blue.
SEGMENT_COLORS = {
    "dark": ["#e66767", "#d95926", "#d9a520", "#3987e5"],
    "light": ["#e34948", "#eb6834", "#c98f0c", "#2a78d6"],
}


def segment_map(df, geojson, height=600):
    """Districts coloured by risk segment, one legend entry each."""

    fig = go.Figure()

    all_ids = [f["id"] for f in geojson["features"]]

    fig.add_trace(go.Choropleth(
        geojson=geojson, locations=all_ids, z=[0] * len(all_ids),
        colorscale=[[0, NO_DATA[theme()]], [1, NO_DATA[theme()]]],
        showscale=False, marker_line_color=NEUTRAL[theme()],
        marker_line_width=0.4, showlegend=False,
        hovertemplate="%{location}<br>No data<extra></extra>",
    ))

    for name, color in zip(model.SEGMENTS, SEGMENT_COLORS[theme()]):

        part = df[df["segment"] == name]

        if part.empty:
            continue

        fig.add_trace(go.Choropleth(
            geojson=geojson, locations=part["district_id"],
            z=[1] * len(part), colorscale=[[0, color], [1, color]],
            showscale=False, name=name, showlegend=True,
            marker_line_color=NEUTRAL[theme()], marker_line_width=0.5,
            customdata=part[[
                "district", "state", "risk_index", "smokeless_men_pct",
                "smokeless_women_pct", "women_oral_screening_pct",
            ]].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[0]}</b>, %{customdata[1]}<br>"
                f"{name}<br>"
                "Risk index: %{customdata[2]:.2f}× India<br>"
                "Smokeless use (est.): men %{customdata[3]:.1f}%, "
                "women %{customdata[4]:.1f}%<br>"
                "Women 30-49 ever screened: %{customdata[5]:.1f}%"
                "<extra></extra>"
            ),
        ))

    lon_min, lat_min, lon_max, lat_max = bounds(geojson)
    pad = 0.03 * max(lon_max - lon_min, lat_max - lat_min)

    fig.update_geos(
        visible=False, bgcolor="rgba(0,0,0,0)",
        projection_type="mercator",
        lonaxis_range=[lon_min - pad, lon_max + pad],
        lataxis_range=[lat_min - pad, lat_max + pad],
    )

    style(fig, height)
    fig.update_layout(legend={"orientation": "h", "y": 1.02, "x": 0})

    return fig


def render_matrix():

    df = model.district_cross_matrix()
    india_screening = model.load_national()["women_oral_screening"]

    st.markdown(
        "A cross-matrix of four things for every district: **smokeless "
        "tobacco use**, **oral cancer**, **risk** and the **potential "
        "upside of switching** to lower-risk nicotine products. Two are "
        "ready now; the other two are waiting on data being sourced."
    )

    st.markdown(
        "| Part | Status | What it uses |\n"
        "|---|---|---|\n"
        "| Smokeless tobacco use | ✅ Estimated | NFHS-5 district tobacco "
        "use × the state's GATS-2 smokeless share of users |\n"
        "| Risk districts | ✅ Modelled | The page's oral cancer risk "
        "index plus oral cancer screening coverage |\n"
        "| Oral cancer cases | ⏳ Awaiting data | District or registry "
        "incidence (being sourced) |\n"
        "| Upside of switching | ⏳ Awaiting data | Relative risk of snus "
        "and nicotine pouches, and switching rates (being sourced) |"
    )

    state = st.selectbox(
        "Zoom to state", ["All India"] + sorted(df["state"].unique()),
        key="matrix_state",
    )

    geojson = model.load_geojson("districts")
    scope = df

    if state != "All India":
        scope = df[df["state"] == state]
        geojson = {
            "type": "FeatureCollection",
            "features": [
                f for f in geojson["features"]
                if f["properties"]["state"] == state
            ],
        }

    rated = scope.dropna(subset=["segment"])
    priority = rated[rated["segment"] == model.SEGMENTS[0]]

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Districts", f"{len(rated)}")
    m2.metric(
        "High risk", f"{(rated['risk_tier'] == 'High').sum()}",
        help="Risk index at least 1.25× India.",
    )
    m3.metric(
        "Priority districts", f"{len(priority)}",
        help=(
            "High risk and fewer women 30-49 ever screened than the "
            f"national {india_screening:.1f}%."
        ),
    )
    m4.metric(
        "Median women screened", fmt(
            rated["women_oral_screening_pct"].median(), "%"
        ),
        help=f"India: {india_screening:.1f}% of women 30-49.",
    )

    left, right = st.columns([2, 3])

    with left:

        st.markdown("##### Risk × screening")

        tiers = [name for name, _, _ in model.RISK_TIERS][::-1]
        cols = [True, False]
        counts = [
            [int(((rated["risk_tier"] == t)
                  & (rated["screening_low"] == low)).sum()) for low in cols]
            for t in tiers
        ]
        total = max(len(rated), 1)

        fig = go.Figure(go.Heatmap(
            z=counts,
            x=[f"Screening below India ({india_screening:.1f}%)",
               "At or above India"],
            y=[f"{t} risk" if t != "Below India" else "Below India"
               for t in tiers],
            text=[[f"{c}<br>{c / total:.0%}" for c in row]
                  for row in counts],
            texttemplate="%{text}",
            colorscale=sequential_scale(), showscale=False,
            hovertemplate="%{y}, %{x}: %{z} districts<extra></extra>",
        ))

        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(side="top")

        st.plotly_chart(style(fig, 320), width="stretch",
                        key="matrix_heat", config=BARS_CONFIG)

        st.caption(
            "Risk tiers on the district risk index (India = 1): below "
            "1.0, 1.0 to 1.25, and 1.25 or more. Top-left is the "
            "priority cell: most exposure, least early detection."
        )

    with right:

        st.plotly_chart(segment_map(scope, geojson, 520),
                        width="stretch", key="matrix_map")

    st.markdown("##### Priority districts")

    if priority.empty:
        st.caption(f"No priority districts in {state}.")
    else:
        show = priority.sort_values("risk_index", ascending=False)
        st.dataframe(
            show[[
                "district", "state", "risk_index", "smokeless_men_pct",
                "smokeless_women_pct", "women_oral_screening_pct",
                "ntcp_activity_total",
            ]].round(2).rename(columns={
                "district": "District", "state": "State",
                "risk_index": "Risk index (India = 1)",
                "smokeless_men_pct": "Men, smokeless (est. %)",
                "smokeless_women_pct": "Women, smokeless (est. %)",
                "women_oral_screening_pct": "Women 30-49 screened (%)",
                "ntcp_activity_total": "NTCP budget (₹ lakh)",
            }),
            hide_index=True, width="stretch",
        )

    # Where budgets exist, does money follow risk? Compare within a
    # state only: states size district allocations very differently.
    funded = rated.dropna(subset=["ntcp_activity_total"])

    if len(funded):

        st.markdown("##### Does the tobacco control budget follow risk?")

        rows = []

        for name, group in funded.groupby("state"):
            pri = group[group["segment"] == model.SEGMENTS[0]]
            rest = group[group["segment"] != model.SEGMENTS[0]]
            rows.append({
                "State": name,
                "Districts with budget": len(group),
                "Priority districts": len(pri),
                "Median budget, priority (₹ lakh)":
                    pri["ntcp_activity_total"].median(),
                "Median budget, others (₹ lakh)":
                    rest["ntcp_activity_total"].median(),
            })

        st.dataframe(pd.DataFrame(rows).round(2), hide_index=True,
                     width="stretch")

        st.caption(
            "Sanctioned NTCP activity budgets (FY 2024-25) from the "
            "Tobacco control budget tab, for the 7 states parsed so far. "
            "Compare within a state: allocations are sized differently "
            "from state to state."
        )

    with st.expander("Full cross-matrix as a table"):

        table = scope[[
            "state", "district", "smokeless_men_pct", "smokeless_women_pct",
            "men_tobacco_pct", "women_tobacco_pct", "risk_index",
            "risk_tier", "women_oral_screening_pct", "segment",
            "ntcp_activity_total",
        ]].round(2).assign(**{
            "oral_cancer_cases": "awaiting data",
            "switching_upside": "awaiting data",
        }).sort_values("risk_index", ascending=False)

        st.dataframe(table, width="stretch", hide_index=True)
        csv_download(table, "oral_cancer_risk_cross_matrix.csv")

    st.caption(
        "Caveats: smokeless use is estimated. Within a state, districts "
        "differ only in total tobacco use, because the smokeless share "
        "comes from GATS-2 at state level. Screening is the only "
        "district figure available, and covers women 30-49 only. The risk "
        "index is relative, not a case count. Each district estimate "
        "rests on about 800-1,000 households, so neighbouring tiers "
        "overlap within sampling error. Grey districts are disputed in "
        "the source extractions."
    )


# --- Tab: tobacco control budget ---------------------------------------

NTCP_METRICS = {
    "Total NTCP activity budget": "ntcp_activity_total",
    "COTPA enforcement (FMR 104)": "cotpa_104",
    "Tobacco-free schools, ToFEI (FMR 105)": "tofei_105",
    "Tobacco cessation (FMR 106)": "cessation_106",
}


def lakh(value):

    return fmt(value, "lakh")


def render_ntcp():

    try:
        df = model.load_ntcp_budget()
        split = model.load_ntcp_state_split().set_index("state")
    except FileNotFoundError:
        st.warning(
            "The tobacco control budget data hasn't been built yet. Run "
            "`python3 -m ingestion.ntcp_district_rop` (it downloads the "
            "NHM district RoPs; Haryana's server can take several "
            "minutes), then reload."
        )
        return

    st.markdown(
        "How much each district was **sanctioned** under the National "
        "Tobacco Control Programme (NTCP), from the National Health "
        "Mission's district Records of Proceedings (RoPs). Set against "
        "the district's tobacco use, it shows whether the money follows "
        "the need."
    )

    st.info(
        "**Sanctioned, not spent.** No state publishes district-level "
        "NTCP expenditure; RoP approvals are the finest public figure. "
        "Amounts cover NTCP activity lines only (FMR 104 COTPA "
        "enforcement, 105 tobacco-free schools, 106 cessation), not "
        "NTCP staff salaries, which RoPs book under human resources. "
        f"**{df['state'].nunique()} states so far**; see the note at the "
        "bottom for the others."
    )

    c1, c2 = st.columns(2)

    with c1:
        state = st.selectbox(
            "State", sorted(df["state"].unique()), key="ntcp_state"
        )

    with c2:
        name = st.selectbox(
            "Budget line", list(NTCP_METRICS), key="ntcp_metric"
        )

    column = NTCP_METRICS[name]

    data = df[df["state"] == state]

    fy = data["fy"].iloc[0]

    total = data["ntcp_activity_total"]

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Financial year", fy)
    m2.metric("Districts with a RoP", f"{len(data)}")
    m3.metric("Sanctioned to districts", lakh(total.sum()))
    m4.metric(
        "Typical district (median)", lakh(total.median()),
        help=f"Range {lakh(total.min())} to {lakh(total.max())}",
    )

    geojson = model.load_geojson("districts")
    geojson = {
        "type": "FeatureCollection",
        "features": [
            f for f in geojson["features"]
            if f["properties"]["state"] == state
        ],
    }

    map_col, bar_col = st.columns([3, 2])

    with map_col:

        fig = choropleth(
            data, geojson, "district_id", column, f"{name} (₹ lakh)",
            "lakh",
            hover=[
                ("district", "", None),
                ("ntcp_activity_total", "Total NTCP activity", "lakh"),
                ("cotpa_104", "COTPA enforcement", "lakh"),
                ("tofei_105", "Tobacco-free schools", "lakh"),
                ("cessation_106", "Cessation", "lakh"),
                ("men_tobacco_pct", "Men using tobacco", "%"),
                ("rop_units", "RoP district(s)", None),
            ],
            height=560,
        )
        st.plotly_chart(fig, width="stretch", key="ntcp_map")

    with bar_col:

        st.plotly_chart(
            ranked_bars(data, "district", column, "lakh",
                        series_color("Both"), height=560),
            width="stretch", key="ntcp_bars", config=BARS_CONFIG,
        )

    missing = len(geojson["features"]) - len(data)

    if missing:
        st.caption(
            f"Grey: {missing} NFHS-5 district(s) in {state} with no "
            "usable RoP."
        )

    if data["rop_units"].str.contains(r"\+").any():
        st.caption(
            "Districts created after NFHS-5 are added into the NFHS-5 "
            "district they were carved from (see the RoP district(s) "
            "column)."
        )

    notes = data[data["mapping_note"] != ""]

    if len(notes):
        st.caption(
            "**Approximate:** some newer districts were carved from more "
            "than one NFHS-5 district. Each is counted wholly in the one "
            "that held most of its 2011 population, so these totals are "
            "a little high or low: "
            + "; ".join(
                f"{r.district} {r.mapping_note}"
                for r in notes.itertuples()
            )
            + "."
        )

    # Does the money follow the need?
    st.markdown("##### Does the budget follow tobacco use?")

    st.caption(
        "Each dot is a district: tobacco use among men 15+ (NFHS-5, "
        "2019-21) against its sanctioned NTCP activity budget."
    )

    fig = go.Figure(go.Scatter(
        x=data["men_tobacco_pct"],
        y=data["ntcp_activity_total"],
        mode="markers",
        marker={"size": 10, "color": series_color("Men"), "opacity": 0.85},
        customdata=data[["district"]].to_numpy(),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>Men using tobacco: %{x:.1f}%"
            "<br>Budget: ₹%{y:.2f} lakh<extra></extra>"
        ),
    ))

    fig.update_xaxes(title="Men 15+ using tobacco (%)", showgrid=True)
    fig.update_yaxes(title="NTCP activity budget (₹ lakh)", showgrid=True,
                     rangemode="tozero")

    st.plotly_chart(style(fig, 380), width="stretch", key="ntcp_scatter")

    common = total.round(2).mode().iloc[0]
    same = int((total.round(2) == common).sum())

    if same > len(data) / 2:
        hi = data.loc[data["men_tobacco_pct"].idxmax()]
        lo = data.loc[data["men_tobacco_pct"].idxmin()]
        st.markdown(
            f"**{same} of {len(data)} districts** in {state} are "
            f"sanctioned the same {lakh(common)}. "
            f"{hi['district']} ({hi['men_tobacco_pct']:.1f}% of men use "
            f"tobacco) gets {lakh(hi['ntcp_activity_total'])}; "
            f"{lo['district']} ({lo['men_tobacco_pct']:.1f}%) gets "
            f"{lakh(lo['ntcp_activity_total'])}."
        )

    if state in split.index:
        row = split.loc[state]
        whole = row["state_level_lakh"] + row["district_level_lakh"]
        share = row["state_level_lakh"] / whole
        lead = (
            f"**Most of {state}'s NTCP money stays at state level.** "
            if share > 0.5 else
            f"**{share:.0%} of {state}'s NTCP money stays at state "
            "level.** "
        )
        st.markdown(
            lead +
            f"Of {lakh(whole)} sanctioned for these activities in "
            f"{row['fy']}, {lakh(row['state_level_lakh'])} "
            f"({row['state_level_lakh'] / whole:.0%}) is held at state "
            f"level and {lakh(row['district_level_lakh'])} goes to "
            "districts. The map shows only the district share."
        )

    with st.expander("All districts as a table"):

        columns = [
            "state", "district", "fy", "cotpa_104", "tofei_105",
            "cessation_106", "ntcp_activity_total", "men_tobacco_pct",
            "rop_units", "mapping_note", "source_url",
        ]
        table = df[columns].sort_values(["state", "district"])
        st.dataframe(
            table, width="stretch", hide_index=True,
            column_config={
                "source_url": st.column_config.LinkColumn("RoP"),
            },
        )
        csv_download(table, "ntcp_district_sanctioned_budget.csv")

    st.caption(
        "Sources: NHM district RoPs for FY 2024-25 from Haryana, Odisha "
        "and Rajasthan (their approved 2024-26 district plans), Sikkim, "
        "Meghalaya, Uttarakhand and Assam (its NTCP district budget "
        "sheet). States size their district allocations differently, so "
        "compare districts within a state more than across states. "
        "Rajasthan's Dholpur RoP was published without its amount "
        "columns. Not yet included: Andhra Pradesh, whose only district "
        "RoPs are scanned FY 2026-27 files for 26 post-2022 districts, "
        "most of which straddle two of NFHS-5's 13."
    )


# --- Tab: trend --------------------------------------------------------

def render_trend():

    df = model.load_state_frame()
    national = model.load_national()

    st.markdown(
        "NFHS-5 (2019-21) and NFHS-6 (2023-24) asked the same household "
        "question about tobacco use by everyone aged 15+, so the two "
        "rounds compare directly."
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Men 15+ using tobacco",
        f"{national['men_tobacco_nfhs6']:.1f}%",
        f"{national['men_tobacco_nfhs6'] - national['men_tobacco_nfhs5']:+.1f} pp",
        delta_color="inverse",
    )
    c2.metric(
        "Women 15+ using tobacco",
        f"{national['women_tobacco_nfhs6']:.1f}%",
        f"{national['women_tobacco_nfhs6'] - national['women_tobacco_nfhs5']:+.1f} pp",
        delta_color="inverse",
    )
    c3.metric(
        "States/UTs where men's use rose",
        f"{(df['men_tobacco_change_pp'] > 0).sum()} of "
        f"{df['men_tobacco_change_pp'].notna().sum()}",
    )

    sex = st.radio(
        "Show", ["Men", "Women"], horizontal=True, key="trend_sex"
    )

    key = sex.lower()

    data = df.dropna(subset=[f"{key}_tobacco_nfhs6"]).sort_values(
        f"{key}_tobacco_change_pp", ascending=False
    )

    fig = go.Figure()

    for _, row in data.iterrows():
        fig.add_trace(go.Scatter(
            x=[row[f"{key}_tobacco_nfhs5"], row[f"{key}_tobacco_nfhs6"]],
            y=[row["state"], row["state"]],
            mode="lines",
            line={"color": NEUTRAL[theme()], "width": 2},
            hoverinfo="skip", showlegend=False,
        ))

    fig.add_trace(go.Scatter(
        x=data[f"{key}_tobacco_nfhs5"], y=data["state"], mode="markers",
        name="NFHS-5 (2019-21)",
        marker={"size": 9, "color": MUTED_TEXT[theme()]},
        hovertemplate="%{y}, 2019-21: %{x:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=data[f"{key}_tobacco_nfhs6"], y=data["state"], mode="markers",
        name="NFHS-6 (2023-24)",
        marker={"size": 10, "color": series_color(sex),
                "line": {"width": 2, "color": NO_DATA[theme()]}},
        customdata=data[f"{key}_tobacco_change_pp"],
        hovertemplate=(
            "%{y}, 2023-24: %{x:.1f}% (%{customdata:+.1f} pp)"
            "<extra></extra>"
        ),
    ))

    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(ticksuffix="%", showgrid=True)

    st.markdown(
        f"##### {sex}: 2019-21 → 2023-24, sorted from largest rise to "
        "largest fall"
    )
    st.plotly_chart(style(fig, 20 * len(data) + 80), width="stretch")

    st.caption(
        "Manipur was not surveyed in NFHS-6. A change of 1-2 points "
        "in a small state can be sampling noise; large changes are more "
        "likely real."
    )

    st.markdown("##### All-India, urban vs rural")

    nfhs5 = model.load_state_tobacco_nfhs5_india()
    nfhs6 = model.load_national_nfhs6_row()

    table = pd.DataFrame([
        {
            "Group": f"{s.capitalize()}, {setting}",
            "NFHS-5 (2019-21)": nfhs5[f"{s}_{setting}_pct"],
            "NFHS-6 (2023-24)": nfhs6[f"{s}_tobacco_{setting}_pct"],
        }
        for s in ("men", "women") for setting in ("urban", "rural")
    ])
    table["Change (pp)"] = (
        table["NFHS-6 (2023-24)"] - table["NFHS-5 (2019-21)"]
    ).round(1)

    st.dataframe(table, hide_index=True, width="stretch")


# --- Tab: who ----------------------------------------------------------

def render_who():

    background = model.load_background()
    products = model.load_products()

    st.markdown(
        "Tobacco use by population group, all-India, NFHS-5 (2019-21), "
        "age 15+, as reported for every household member."
    )

    c1, c2 = st.columns(2)

    with c1:
        dimension = st.selectbox(
            "Compare by",
            ["Wealth quintile", "Schooling", "Age", "Caste/tribe",
             "Religion"],
            key="who_dim",
        )

    with c2:
        residence = st.radio(
            "Residence", ["Total", "Urban", "Rural"], horizontal=True,
            key="who_res",
        )

    column = f"{residence.lower()}_pct"

    order = {
        "Wealth quintile": ["Lowest", "Second", "Middle", "Fourth",
                            "Highest"],
    }

    data = background[background["dimension"] == dimension]

    groups = order.get(dimension, list(dict.fromkeys(data["group"])))

    fig = go.Figure()

    for sex in ("Men", "Women"):
        part = data[data["sex"] == sex].set_index("group").loc[groups]
        fig.add_trace(go.Bar(
            x=groups, y=part[column], name=sex,
            marker_color=series_color(sex), marker_line_width=0,
            text=[f"{v:.1f}%" for v in part[column]],
            textposition="outside",
            customdata=part["respondents"],
            hovertemplate=(
                f"{sex}, %{{x}}: %{{y:.1f}}% "
                "(%{customdata:,} people)<extra></extra>"
            ),
        ))

    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")

    st.plotly_chart(style(fig, 420), width="stretch")

    st.caption(
        "NFHS-5 India Report, Table 2.35. Religion and caste refer to "
        "the household head."
    )

    st.divider()

    st.markdown("##### Which products? (age 15-49, NFHS-5)")

    product_res = st.radio(
        "Residence", ["Total", "Urban", "Rural"], horizontal=True,
        key="prod_res",
    )

    pcol = f"{product_res.lower()}_pct"

    men = products[products["sex"] == "Men"].sort_values(pcol)
    women = products[products["sex"] == "Women"].set_index("product").loc[
        men["product"]
    ].reset_index()

    labels = [f"{p} · {t.lower()}" for p, t in zip(men["product"], men["type"])]

    fig = go.Figure()

    for sex, part in (("Men", men), ("Women", women)):
        fig.add_trace(go.Bar(
            y=labels, x=part[pcol], name=sex, orientation="h",
            marker_color=series_color(sex), marker_line_width=0,
            hovertemplate=f"{sex}, %{{y}}: %{{x:.1f}}%<extra></extra>",
        ))

    fig.update_layout(barmode="group", bargap=0.3)
    fig.update_xaxes(ticksuffix="%")

    st.plotly_chart(style(fig, 440), width="stretch")

    st.caption(
        "NFHS-5 India Report, Table 11.7. People can use more than one "
        "product, so values don't add up to the overall rate. Among "
        "men, gutkha/paan masala is the single most-used product, and "
        "khaini is used more than bidis."
    )


# --- Tab: projection ---------------------------------------------------

PROJECTION_COLUMNS = {
    "state": "State",
    "region": "Region",
    "cases": "Estimated cases",
    "men_cases": "Cases, men",
    "women_cases": "Cases, women",
    "cases_avoided": "Cases avoided (long run)",
    "relative_rate": "Rate vs India (×)",
    "attributable_pct": "% attributable to tobacco",
    "men_prevalence_pct": "Men using tobacco (%)",
    "women_prevalence_pct": "Women using tobacco (%)",
    "smokeless_share_pct": "Smokeless share of users (%)",
    "gats_mix_source": "Product mix taken from (GATS-2)",
}

def render_projection():

    st.markdown(
        "This tab estimates **where India's oral cancer cases occur** "
        "and **how many could be prevented** by reducing tobacco use. "
        "The national total comes from the cancer registry. The model "
        "only splits it between states and estimates the share "
        "attributable to tobacco."
    )

    with st.expander("How the model works, and what changed from the "
                     "earlier version"):
        st.markdown(
            f"""
1. **National cases are measured, not assumed.** NCRP projects
   {model.national_oral_cases(2025, 'Both'):,.0f} new oral cavity
   cancers (tongue + mouth) in 2025. The earlier version multiplied a
   single incidence rate by the 2011 Census population.
2. **Each state gets a relative risk** from its NFHS tobacco
   prevalence, split into smokeless and smoked-only use with the
   state's own GATS-2 product mix:
   `R = 1 + p_smokeless × (RR_smokeless − 1) + p_smoked × (RR_smoked − 1)`.
   Non-users keep a baseline risk of 1. The earlier version gave them
   zero.
3. **Cases are shared out** in proportion to population × R, for men
   and women separately (state sex ratios from NFHS-5).
4. **A scenario** that cuts tobacco use gives a new R′. The share of
   cases avoided is `1 − R′/R`, the tobacco-attributable share. The
   earlier version assumed a 44% cut in use removes 44% of cancers.
   That would only hold if every oral cancer were caused by tobacco.

**Caveats.** The avoided cases are a long-run steady state. Cancer
risk falls over 10-20+ years after quitting, not in the year of the
cut. Areca nut without tobacco, alcohol and HPV also cause oral cancer
but are not modelled. That is one reason the measured registry rates
are highest in west/central India, while this tobacco-only index is
highest in the Northeast and Odisha. State populations are 2011 Census
shares.
"""
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        survey = st.radio(
            "Tobacco prevalence from",
            ["nfhs6", "nfhs5"],
            format_func={
                "nfhs6": "NFHS-6 (2023-24)", "nfhs5": "NFHS-5 (2019-21)"
            }.get,
            key="proj_survey",
        )
        year = st.select_slider(
            "Cases for year (NCRP projection)",
            [2016, 2017, 2018, 2019, 2020, 2025], value=2025,
            key="proj_year",
        )

    with c2:
        rr_slt = st.slider(
            "Relative risk: smokeless tobacco",
            1.0, 10.0, model.DEFAULT_RR_SMOKELESS, 0.01,
            help="Default 4.44: Asthana et al. 2019 meta-analysis, WHO "
                 "South-East Asia Region (reported range 4.44-7.90).",
            key="proj_rr_slt",
        )
        rr_smk = st.slider(
            "Relative risk: smoking only",
            1.0, 6.0, model.DEFAULT_RR_SMOKED, 0.1,
            help="Default 2.6: pooled random-effects odds ratio for "
                 "bidi smoking and oral cancer, 10 Indian case-control "
                 "studies (Rahman et al. 2005).",
            key="proj_rr_smk",
        )

    with c3:
        reduction = st.slider(
            "Reduce tobacco use by (%)", 0, 100,
            model.SWEDEN_BENCHMARK_REDUCTION_PCT, 5,
            help=f"{model.SWEDEN_BENCHMARK_REDUCTION_PCT}% is a policy "
                 "ambition benchmark (Sweden's tobacco-related "
                 "mortality vs. the EU average). It is not a claim "
                 "about snus.",
            key="proj_reduction",
        )
        applies = st.radio(
            "Reduction applies to",
            ["all", "smokeless"],
            format_func={
                "all": "All tobacco use",
                "smokeless": "Smokeless tobacco only",
            }.get,
            key="proj_applies",
        )

    states, summary = model.project(
        year=year, survey=survey, rr_smokeless=rr_slt, rr_smoked=rr_smk,
        reduction_pct=reduction, reduction_applies_to=applies,
    )

    naive = summary["cases"] * reduction / 100

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(f"New oral cavity cancers, {year}", f"{summary['cases']:,.0f}")
    m2.metric(
        "Attributable to tobacco", f"{summary['attributable_pct']:.0f}%"
    )
    m3.metric(
        "Cases avoided per year (long run)",
        f"{summary['cases_avoided']:,.0f}",
        f"{summary['cases_avoided'] / summary['cases'] * 100:.1f}% of cases",
        delta_color="off",
        delta_arrow="off",
    )
    m4.metric(
        "Earlier model's (overstated) estimate",
        f"{naive:,.0f}",
        help="Old method: cases × reduction %, i.e. it assumed every "
             "oral cancer is caused by tobacco.",
    )

    map_choice = st.radio(
        "Map",
        ["relative_rate", "cases", "cases_avoided", "attributable_pct"],
        format_func={
            "relative_rate": "Rate relative to India",
            "cases": "Estimated cases",
            "cases_avoided": "Cases avoided",
            "attributable_pct": "% attributable to tobacco",
        }.get,
        horizontal=True, key="proj_map",
    )

    units = {
        "relative_rate": "x", "cases": "n", "cases_avoided": "n",
        "attributable_pct": "%",
    }

    left, right = st.columns([3, 2])

    with left:
        fig = choropleth(
            states, model.load_geojson("states"), "state", map_choice,
            {
                "relative_rate": "× India", "cases": "Cases",
                "cases_avoided": "Avoided", "attributable_pct": "%",
            }[map_choice],
            units[map_choice],
            hover=[
                ("state", "", None),
                ("cases", "Estimated cases", "n"),
                ("cases_avoided", "Avoided under scenario", "n"),
                ("relative_rate", "Rate vs India", "x"),
                ("attributable_pct", "Attributable to tobacco", "%"),
                ("men_prevalence_pct", "Men using tobacco", "%"),
                ("women_prevalence_pct", "Women using tobacco", "%"),
            ],
            diverging=map_choice == "relative_rate", midpoint=1.0,
            height=600,
        )
        st.plotly_chart(fig, width="stretch", key="proj_map_fig")

    with right:
        st.plotly_chart(
            ranked_bars(
                states, "state", map_choice, units[map_choice],
                series_color("Both"), height=600,
                reference=1.0 if map_choice == "relative_rate" else None,
                reference_label="India",
            ),
            width="stretch", key="proj_bars", config=BARS_CONFIG,
        )

    table = states.assign(
        smokeless_share_pct=states["smokeless_share_of_users"] * 100,
    )[list(PROJECTION_COLUMNS)].rename(columns=PROJECTION_COLUMNS)

    for column in table.columns[2:6]:
        table[column] = table[column].round(0).astype(int)

    table = table.round(2)

    st.dataframe(table, hide_index=True, width="stretch")
    csv_download(table, f"oral_cancer_projection_{year}.csv")


# --- Tab: sources ------------------------------------------------------

def render_sources():

    st.markdown("#### Data sources")

    rows = model.sources()

    header = [c for c in rows[0] if c != "Link"]

    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ] + [
        "| " + " | ".join(
            f"[{row['Source']}]({row['Link']})" if c == "Source" else row[c]
            for c in header
        ) + " |"
        for row in rows
    ]

    st.markdown("\n".join(lines))

    st.caption("Each source name links to the document or dataset.")

    st.markdown(
        """
#### Data-quality issues found and how they were handled

- **Official district fact sheets are offline.** The ~750 PDFs on
  rchiips.org now return 404, so district values come from three
  independent open extractions, cross-checked on every rebuild:
  - The primary (all 707 districts) matches the phase-1 extraction
    exactly on 330 of 331 shared districts.
  - It **wrongly listed Manipur's Chandel under Mizoram in place of
    Saiha**. Saiha is patched from the second full extraction and
    flagged.
  - **9 districts are disputed** (6 in Delhi, plus Mahoba, Mahrajganj
    and Dhule). The extractions disagree, apparently through shifted
    rows or columns, and neither can be checked against the original
    PDFs. They are kept in downloads but left uncoloured on maps.
- **State values are triple-checked.** NFHS-5 state tobacco rates
  parsed from the India Report (Table 2.36) agree within 0.3
  percentage points with the NFHS-5 column printed in the NFHS-6 fact
  sheets, and within 0.5 points with the state fact-sheet extraction.
- **Boundaries now match the surveys.** Maps use NFHS-5's own 36
  states/UTs and 707 districts (DHS Spatial Data Repository).
  Previously Telangana and Ladakh were merged back into 2011-era
  states.
- **Gaps.** NFHS-6 did not survey Manipur. GATS-2 has no row for 4
  small UTs (fallbacks listed in the States tab). Registry incidence
  by city appears only as charts in the NCRP report, so it is not
  used.

#### Rebuilding the data

Every file is produced by a script in `ingestion/` that downloads the
source and parses it, refusing to write partial output. Run
`python3 -m scripts.build_oral_cancer_data` to rebuild everything.
"""
    )


# --- Sections (defined last: they point at the render functions) -------

SECTIONS = {
    "📌 Burden & key findings": render_burden,
    "🗺️ States": render_states,
    "📍 Districts": render_districts,
    "🎯 Risk matrix": render_matrix,
    "💰 Tobacco control budget": render_ntcp,
    "📈 Trend 2019→2024": render_trend,
    "👥 Who uses tobacco": render_who,
    "🧮 Projection model": render_projection,
    "📚 Sources & caveats": render_sources,
}
