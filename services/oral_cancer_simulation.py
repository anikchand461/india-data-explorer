"""
Oral cancer risk projection driven by real, state-level tobacco-use
data -- built to replace the earlier HPV simulation's flat national
rate with actual geographic variation.

All real numbers are loaded from files in data/reference/, not
hardcoded here -- see data/reference/SOURCES.md for the exact
provenance and confidence level of every value:
  - data/reference/nfhs5_tobacco_use_by_state.csv: NFHS-5 (2019-21)
    Table 2.36, transcribed directly from the official DHS/MoHFW
    report.
  - data/reference/reference_constants.json: national oral cancer
    baseline (NCRP), national tobacco averages (NFHS-5), and the
    Sweden benchmark figure.
  - data/reference/state_population_2011.csv: 2011 Census totals
    (shared with services/hpv_simulation.py).

MODELING ASSUMPTION: oral cancer risk is assumed to scale linearly
with a state's tobacco-use prevalence relative to the national
average, applied to the national baseline incidence rate. Tobacco
is the established dominant driver of oral cancer in India, but no
consistent state-by-state oral cancer incidence dataset exists to
measure this directly -- so this is a transparent proxy, not a
measured state-level cancer rate.

ON THE "SWEDEN" BENCHMARK: the literature does NOT support "snus
reduces oral cancer" as a direct mechanism -- pooled prospective
studies of Swedish snus users show a NULL association with oral
cancer specifically. Sweden's real, documented achievement is 44%
lower tobacco-related mortality than the EU average, via smokers
substituting snus for cigarettes. That figure is used here as a
labeled POLICY-AMBITION BENCHMARK -- what a comparable reduction in
India's own real oral-cancer driver (smokeless tobacco use) would
project to -- not a claim that snus itself lowers oral cancer risk.
See data/reference/SOURCES.md for the full caveat.
"""

import csv
import json
from pathlib import Path

REFERENCE_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "reference"
)


def _load_state_tobacco_use():

    path = REFERENCE_DIR / "nfhs5_tobacco_use_by_state.csv"

    tobacco_use = {}

    with open(path, "r", encoding="utf-8", newline="") as file:

        for row in csv.DictReader(file):

            tobacco_use[row["state"]] = {
                "men": float(row["men_pct"]),
                "women": float(row["women_pct"]),
            }

    return tobacco_use


def _load_constants():

    path = REFERENCE_DIR / "reference_constants.json"

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


STATE_TOBACCO_USE = _load_state_tobacco_use()

_constants = _load_constants()

NATIONAL_ORAL_CANCER_INCIDENCE_PER_100K = (
    _constants["national_oral_cancer_incidence_per_100k"]
)

NATIONAL_TOBACCO_USE_MEN = _constants["national_tobacco_use_men_pct"]

NATIONAL_TOBACCO_USE_WOMEN = (
    _constants["national_tobacco_use_women_pct"]
)

SWEDEN_BENCHMARK_REDUCTION_PCT = (
    _constants["sweden_benchmark_reduction_pct"]
)


def simulate(reduction_pct, sex="combined"):
    """
    reduction_pct: assumed reduction in tobacco use, 0-100 (Sweden's
      documented achievement was 44 -- see module docstring).
    sex: "men", "women", or "combined" (population-weighted).

    Returns a dict per state with the real tobacco-use rate used,
    the relative-risk-scaled baseline oral cancer incidence, and the
    projected annual cases avoided under the reduction scenario.
    """

    from services.hpv_simulation import (
        STATE_POPULATION_2011,
        FEMALE_SHARE_OF_POPULATION,
    )

    reduction = max(0.0, min(100.0, reduction_pct)) / 100.0

    results = {}

    for state_name, population in STATE_POPULATION_2011.items():

        rates = STATE_TOBACCO_USE.get(state_name)

        if not rates:
            continue

        female_share = FEMALE_SHARE_OF_POPULATION
        male_share = 1 - female_share

        if sex == "men":
            state_rate = rates["men"]
            national_rate = NATIONAL_TOBACCO_USE_MEN
            at_risk_population = population * male_share

        elif sex == "women":
            state_rate = rates["women"]
            national_rate = NATIONAL_TOBACCO_USE_WOMEN
            at_risk_population = population * female_share

        else:
            state_rate = (
                rates["men"] * male_share
                + rates["women"] * female_share
            )
            national_rate = (
                NATIONAL_TOBACCO_USE_MEN * male_share
                + NATIONAL_TOBACCO_USE_WOMEN * female_share
            )
            at_risk_population = population

        relative_risk = state_rate / national_rate

        state_incidence_per_100k = (
            NATIONAL_ORAL_CANCER_INCIDENCE_PER_100K * relative_risk
        )

        baseline_annual_cases = (
            at_risk_population * (state_incidence_per_100k / 100_000)
        )

        cases_avoided = baseline_annual_cases * reduction

        results[state_name] = {
            "tobacco_use_pct": round(state_rate, 1),
            "relative_risk": round(relative_risk, 2),
            "incidence_per_100k": round(state_incidence_per_100k, 1),
            "baseline_annual_cases": round(baseline_annual_cases, 1),
            "cases_avoided_per_year": round(cases_avoided, 1),
        }

    return results
