"""
Data loading and the oral cancer burden model behind the Oral Cancer
page. Every number comes from a file under data/reference/oral_cancer/,
each produced by a download-and-parse script in ingestion/ (run them
all with `python3 -m scripts.build_oral_cancer_data`); provenance and
confidence notes are in data/reference/SOURCES.md.

THE MODEL (replaces the earlier services/oral_cancer_simulation.py)

The earlier projection scaled a national incidence rate linearly by
each state's tobacco prevalence. That implies non-users carry zero
risk (Punjab women, 0.4% tobacco use -> ~0 cases) and that cutting
tobacco use by 44% removes 44% of all oral cancer. Both are wrong.

This one uses the standard population-attributable-fraction set-up:

  1. National totals are measured, not modelled: NCRP's projected new
     oral cavity cancers (tongue C01-02 + mouth C03-06) per year, by
     sex (ICMR-NCDIR, NCRP 2020 Table 14.1).
  2. Each state x sex gets a relative risk index
         R = 1 + p_smokeless * (RR_smokeless - 1)
               + p_smoked_only * (RR_smoked - 1)
     where p is the NFHS tobacco prevalence (age 15+) split into
     smokeless (incl. dual users) and smoked-only using that state's
     GATS-2 product mix. Non-users keep a baseline risk of 1.
  3. National cases are shared out in proportion to population x R.
  4. A scenario that cuts prevalence to p' gives R'. The long-run
     fraction of cases avoided is 1 - R'/R -- the attributable share,
     not the raw percentage cut, and only after the decades-long lag
     between exposure and cancer.

Default relative risks (both adjustable on the page):
  - Smokeless tobacco: 4.44 -- Asthana et al. 2019, Nicotine & Tobacco
    Research 21(9):1162-71, pooled risk for the WHO South-East Asia
    Region (the lower end of its reported 4.44-7.90 range).
  - Smoking: 2.6 -- random-effects pooled odds ratio for bidi smoking
    and oral cancer across 10 Indian case-control studies (Rahman et
    al., Preventive Medicine, 2005).
"""

import csv
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ingestion.state_names import STATE_REGION

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data" / "reference" / "oral_cancer"

GEO_DIR = ROOT / "data" / "geo"

DEFAULT_RR_SMOKELESS = 4.44
DEFAULT_RR_SMOKED = 2.6

SWEDEN_BENCHMARK_REDUCTION_PCT = json.loads(
    (ROOT / "data" / "reference" / "reference_constants.json").read_text()
)["sweden_benchmark_reduction_pct"]

# GATS-2 (2016-17) has no row for these units; use the closest
# available product mix instead (flagged in the state frame).
GATS_FALLBACK = {
    "Ladakh": "Jammu & Kashmir",
    "Andaman & Nicobar Islands": "India",
    "Lakshadweep": "India",
    "Dadra & Nagar Haveli and Daman & Diu": "India",
}


def _read(name):

    return pd.read_csv(DATA_DIR / name)


@lru_cache(maxsize=None)
def load_geojson(level):
    """level: "states" or "districts"."""

    with open(GEO_DIR / f"nfhs5_{level}.geojson", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def load_state_frame():
    """
    One row per current state/UT (36), joining every state-level
    source. Column names say which survey round each value is from.
    """

    nfhs5 = _read("nfhs5_state_tobacco.csv").rename(columns={
        "women_pct": "women_tobacco_nfhs5",
        "men_pct": "men_tobacco_nfhs5",
        "women_urban_pct": "women_tobacco_urban_nfhs5",
        "women_rural_pct": "women_tobacco_rural_nfhs5",
        "men_urban_pct": "men_tobacco_urban_nfhs5",
        "men_rural_pct": "men_tobacco_rural_nfhs5",
    })

    nfhs6 = _read("nfhs6_state_tobacco.csv").rename(columns={
        "women_tobacco_pct": "women_tobacco_nfhs6",
        "men_tobacco_pct": "men_tobacco_nfhs6",
        "women_tobacco_urban_pct": "women_tobacco_urban_nfhs6",
        "women_tobacco_rural_pct": "women_tobacco_rural_nfhs6",
        "men_tobacco_urban_pct": "men_tobacco_urban_nfhs6",
        "men_tobacco_rural_pct": "men_tobacco_rural_nfhs6",
        "women_alcohol_pct": "women_alcohol_nfhs6",
        "men_alcohol_pct": "men_alcohol_nfhs6",
    })[[
        "state", "women_tobacco_nfhs6", "men_tobacco_nfhs6",
        "women_tobacco_urban_nfhs6", "women_tobacco_rural_nfhs6",
        "men_tobacco_urban_nfhs6", "men_tobacco_rural_nfhs6",
        "women_alcohol_nfhs6", "men_alcohol_nfhs6",
    ]]

    screening = _read("nfhs5_state_screening.csv").rename(columns={
        "women_oral_screening_pct": "women_oral_screening_nfhs5",
        "men_oral_screening_pct": "men_oral_screening_nfhs5",
        "women_alcohol_pct": "women_alcohol_nfhs5",
        "men_alcohol_pct": "men_alcohol_nfhs5",
    }).drop(columns=["women_tobacco_pct", "men_tobacco_pct"])

    quitting = _read("nfhs5_quitting_by_state.csv")

    population = _read("state_population_2011_current.csv")

    gats = _read("gats2_tobacco_type_by_state.csv").set_index("state")

    df = (
        population
        .merge(nfhs5, on="state")
        .merge(nfhs6, on="state", how="left")
        .merge(screening, on="state")
        .merge(quitting, on="state")
    )

    df.insert(1, "region", df["state"].map(STATE_REGION))

    mix_source = [
        GATS_FALLBACK.get(s, s) if s not in gats.index else s
        for s in df["state"]
    ]

    df["gats_mix_source"] = mix_source

    df["smokeless_share_of_users"] = [
        (gats.at[s, "smokeless_only_pct"] + gats.at[s, "both_pct"])
        / gats.at[s, "current_user_pct"]
        for s in mix_source
    ]

    df["smokeless_only_pct_gats2"] = [
        gats.at[s, "smokeless_only_pct"] if s in gats.index else None
        for s in df["state"]
    ]
    df["smoked_only_pct_gats2"] = [
        gats.at[s, "smoked_only_pct"] if s in gats.index else None
        for s in df["state"]
    ]
    df["both_pct_gats2"] = [
        gats.at[s, "both_pct"] if s in gats.index else None
        for s in df["state"]
    ]

    df["female_share"] = (
        df["sex_ratio_females_per_1000"]
        / (1000 + df["sex_ratio_females_per_1000"])
    )

    for sex in ("men", "women"):
        df[f"{sex}_tobacco_change_pp"] = (
            df[f"{sex}_tobacco_nfhs6"] - df[f"{sex}_tobacco_nfhs5"]
        )
        df[f"{sex}_tobacco_rural_urban_gap_pp"] = (
            df[f"{sex}_tobacco_rural_nfhs5"]
            - df[f"{sex}_tobacco_urban_nfhs5"]
        )

    return df


@lru_cache(maxsize=None)
def load_national():
    """India-level rows from each state-level source, for headlines."""

    nfhs6 = _read("nfhs6_state_tobacco.csv").set_index("state")
    screening = _read("nfhs5_state_screening.csv").set_index("state")
    gats = _read("gats2_tobacco_type_by_state.csv").set_index("state")

    return {
        "men_tobacco_nfhs5": nfhs6.at["India", "men_tobacco_nfhs5_pct"],
        "women_tobacco_nfhs5": nfhs6.at["India", "women_tobacco_nfhs5_pct"],
        "men_tobacco_nfhs6": nfhs6.at["India", "men_tobacco_pct"],
        "women_tobacco_nfhs6": nfhs6.at["India", "women_tobacco_pct"],
        "women_oral_screening": screening.at[
            "India", "women_oral_screening_pct"
        ],
        "men_oral_screening": screening.at["India", "men_oral_screening_pct"],
        "gats_smokeless_only": gats.at["India", "smokeless_only_pct"],
        "gats_smoked_only": gats.at["India", "smoked_only_pct"],
        "gats_both": gats.at["India", "both_pct"],
        "gats_current": gats.at["India", "current_user_pct"],
    }


@lru_cache(maxsize=None)
def load_state_tobacco_nfhs5_india():
    """NFHS-5 Table 2.36's national row, with urban/rural."""

    df = _read("nfhs5_state_tobacco.csv").set_index("state")

    return df.loc["India"].to_dict()


@lru_cache(maxsize=None)
def load_national_nfhs6_row():

    df = _read("nfhs6_state_tobacco.csv").set_index("state")

    return df.loc["India"].to_dict()


@lru_cache(maxsize=None)
def load_district_frame():

    df = _read("nfhs5_district_indicators.csv")

    states = load_state_frame().set_index("state")

    df["smokeless_share_of_users"] = df["state"].map(
        states["smokeless_share_of_users"]
    )

    df["region"] = df["state"].map(STATE_REGION)

    return df


@lru_cache(maxsize=None)
def load_background():

    return _read("nfhs5_tobacco_by_background.csv")


@lru_cache(maxsize=None)
def load_products():

    return _read("nfhs5_tobacco_products.csv")


@lru_cache(maxsize=None)
def load_ncrp_projections():

    df = _read("ncrp_oral_cancer_projections.csv")

    oral = (
        df.groupby(["sex", "year"], as_index=False)["cases"].sum()
        .assign(site="Oral cavity (tongue + mouth)")
    )

    return pd.concat([df, oral], ignore_index=True)


@lru_cache(maxsize=None)
def load_stage():

    return _read("ncrp_mouth_cancer_stage.csv")


def national_oral_cases(year, sex):
    """NCRP projected tongue + mouth cases; sex "Men"/"Women"/"Both"."""

    df = load_ncrp_projections()

    row = df[
        (df["site"] == "Oral cavity (tongue + mouth)")
        & (df["sex"] == sex) & (df["year"] == year)
    ]

    return float(row["cases"].iloc[0])


def risk_index(prevalence_pct, smokeless_share, rr_smokeless, rr_smoked):
    """
    Levin-style relative risk of a population vs. one with no tobacco
    use. Works element-wise on pandas Series.
    """

    p = prevalence_pct / 100.0

    return (
        1
        + p * smokeless_share * (rr_smokeless - 1)
        + p * (1 - smokeless_share) * (rr_smoked - 1)
    )


def project(
    year=2025,
    survey="nfhs6",
    rr_smokeless=DEFAULT_RR_SMOKELESS,
    rr_smoked=DEFAULT_RR_SMOKED,
    reduction_pct=0,
    reduction_applies_to="all",
):
    """
    Returns (per-state DataFrame, national summary dict).

    survey: "nfhs6" uses NFHS-6 (2023-24) prevalence where it exists
      (NFHS-5 for Manipur, which NFHS-6 didn't survey); "nfhs5" uses
      NFHS-5 (2019-21) throughout.
    reduction_applies_to: "all" cuts all tobacco use by reduction_pct;
      "smokeless" cuts only smokeless use (the oral-cancer-specific
      lever).
    """

    df = load_state_frame().copy()

    reduction = max(0.0, min(100.0, reduction_pct)) / 100.0

    rows = []

    for sex, label in (("men", "Men"), ("women", "Women")):

        if survey == "nfhs6":
            prevalence = df[f"{sex}_tobacco_nfhs6"].fillna(
                df[f"{sex}_tobacco_nfhs5"]
            )
        else:
            prevalence = df[f"{sex}_tobacco_nfhs5"]

        share = df["smokeless_share_of_users"]

        r_now = risk_index(prevalence, share, rr_smokeless, rr_smoked)

        if reduction_applies_to == "smokeless":
            # Fewer smokeless users; smoked-only users unchanged.
            p_slt = prevalence * share * (1 - reduction)
            p_smk = prevalence * (1 - share)
            new_prevalence = p_slt + p_smk
            new_share = (p_slt / new_prevalence).fillna(0)
            r_new = risk_index(
                new_prevalence, new_share, rr_smokeless, rr_smoked
            )
        else:
            r_new = risk_index(
                prevalence * (1 - reduction), share,
                rr_smokeless, rr_smoked,
            )

        sex_share = (
            df["female_share"] if sex == "women" else 1 - df["female_share"]
        )

        weight = df["population_2011"] * sex_share * r_now

        cases = national_oral_cases(year, label) * weight / weight.sum()

        rows.append(pd.DataFrame({
            "state": df["state"],
            "sex": label,
            "prevalence_pct": prevalence,
            "risk_index": r_now,
            "attributable_pct": (1 - 1 / r_now) * 100,
            "cases": cases,
            "cases_avoided": cases * (1 - r_new / r_now),
        }))

    long = pd.concat(rows, ignore_index=True)

    wide = long.pivot(index="state", columns="sex")
    wide.columns = [f"{sex.lower()}_{col}" for col, sex in wide.columns]
    wide = wide.reset_index()

    wide["cases"] = wide["men_cases"] + wide["women_cases"]
    wide["cases_avoided"] = (
        wide["men_cases_avoided"] + wide["women_cases_avoided"]
    )
    wide["attributable_pct"] = (
        (wide["men_cases"] * wide["men_attributable_pct"]
         + wide["women_cases"] * wide["women_attributable_pct"])
        / wide["cases"]
    )

    # Cases per 100k relative to India (1.00 = national average). A
    # relative index rather than an absolute rate, because the only
    # state populations available are 2011 Census counts.
    population = df.set_index("state")["population_2011"]
    per_capita = wide.set_index("state")["cases"] / population
    national_per_capita = wide["cases"].sum() / population.sum()
    wide["relative_rate"] = wide["state"].map(
        per_capita / national_per_capita
    )

    wide = wide.merge(
        df[["state", "region", "population_2011", "gats_mix_source",
            "smokeless_share_of_users"]],
        on="state",
    )

    total = wide["cases"].sum()

    summary = {
        "year": year,
        "cases": total,
        "men_cases": wide["men_cases"].sum(),
        "women_cases": wide["women_cases"].sum(),
        "cases_avoided": wide["cases_avoided"].sum(),
        "attributable_pct": (
            (wide["cases"] * wide["attributable_pct"]).sum() / total
        ),
    }

    return wide.sort_values("cases", ascending=False), summary


def district_risk(sex, rr_smokeless=DEFAULT_RR_SMOKELESS,
                  rr_smoked=DEFAULT_RR_SMOKED):
    """
    District relative risk index vs. India, from district NFHS-5
    prevalence and the state's GATS-2 product mix.
    """

    df = load_district_frame().copy()

    national = load_national()

    if sex == "combined":
        prevalence = (
            df["men_tobacco_pct"] + df["women_tobacco_pct"]
        ) / 2
        national_prevalence = (
            national["men_tobacco_nfhs5"] + national["women_tobacco_nfhs5"]
        ) / 2
    else:
        prevalence = df[f"{sex}_tobacco_pct"]
        national_prevalence = national[f"{sex}_tobacco_nfhs5"]

    national_share = (
        national["gats_smokeless_only"] + national["gats_both"]
    ) / national["gats_current"]

    district = risk_index(
        prevalence, df["smokeless_share_of_users"], rr_smokeless, rr_smoked
    )

    india = risk_index(
        pd.Series([national_prevalence]), pd.Series([national_share]),
        rr_smokeless, rr_smoked,
    ).iloc[0]

    return district / india


def sources():
    """Rows for the page's sources table."""

    with open(DATA_DIR / "SOURCES.csv", encoding="utf-8") as file:
        return list(csv.DictReader(file))
