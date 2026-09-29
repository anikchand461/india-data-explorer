"""
HPV vaccination population-impact simulation.

This is a SIMULATION, not a measurement. It combines:

  REAL DATA (loaded from files in data/reference/ -- see
  data/reference/SOURCES.md for exact provenance of every value):
    - State boundaries: 2011 Census (PC11) state polygons, downloaded
      from AI Kosh (Development Data Lab / SHRUG dataset).
    - State population: 2011 Census of India official totals
      (data/reference/state_population_2011.csv), using the SAME
      undivided state boundaries as the geometry.

  MODELING ASSUMPTIONS (clearly separated, not sourced from our
  dataset catalogue -- standard public-health reference values,
  loaded from data/reference/reference_constants.json, cited in
  data/reference/SOURCES.md):
    - Share of population that is girls aged 9-14 (the WHO-recommended
      primary HPV vaccination cohort): ~5.8% of total population,
      an approximation, not a measured per-state figure.
    - Baseline cervical cancer incidence: 18 per 100,000 women per
      year, India's national age-standardized rate (GLOBOCAN 2020).
      Reliable state-by-state incidence rates are not available from
      a single consistent source, so this national rate is applied
      UNIFORMLY across all states. Geographic variation in the map
      therefore reflects real population differences, not
      differential regional health risk.
    - Vaccine efficacy: 90%, within published clinical trial ranges.
"""

import csv
import json
from pathlib import Path

REFERENCE_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "reference"
)


def _load_state_population():

    path = REFERENCE_DIR / "state_population_2011.csv"

    population = {}

    with open(path, "r", encoding="utf-8", newline="") as file:

        for row in csv.DictReader(file):
            population[row["state"]] = int(row["population"])

    return population


def _load_constants():

    path = REFERENCE_DIR / "reference_constants.json"

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


STATE_POPULATION_2011 = _load_state_population()

_constants = _load_constants()

GIRLS_9_14_SHARE_OF_POPULATION = (
    _constants["girls_9_14_share_of_population"]
)

FEMALE_SHARE_OF_POPULATION = (
    _constants["female_share_of_population"]
)

CERVICAL_CANCER_INCIDENCE_PER_100K_WOMEN = (
    _constants["cervical_cancer_incidence_per_100k_women"]
)

VACCINE_EFFICACY = _constants["hpv_vaccine_efficacy"]


def eligible_girls(state_name):
    population = STATE_POPULATION_2011.get(state_name, 0)
    return population * GIRLS_9_14_SHARE_OF_POPULATION


def simulate(coverage_pct):
    """
    coverage_pct: assumed vaccination coverage, 0-100.

    Returns a dict per state with the eligible cohort size and the
    estimated annual cervical cancer cases avoided at steady state
    (i.e. once a vaccinated cohort reaches the ages where cervical
    cancer risk applies) under this coverage scenario. This is a
    simplified, transparent annualized estimate -- not a longitudinal
    cohort model with time lags, mortality competing risks, or
    catch-up vaccination dynamics.
    """

    coverage = max(0.0, min(100.0, coverage_pct)) / 100.0

    results = {}

    for state_name, population in STATE_POPULATION_2011.items():

        girls = population * GIRLS_9_14_SHARE_OF_POPULATION

        vaccinated = girls * coverage

        female_population = population * FEMALE_SHARE_OF_POPULATION

        baseline_annual_cases = (
            female_population
            * (CERVICAL_CANCER_INCIDENCE_PER_100K_WOMEN / 100_000)
        )

        cases_avoided = (
            coverage * VACCINE_EFFICACY * baseline_annual_cases
        )

        results[state_name] = {
            "population": population,
            "eligible_girls": round(girls),
            "vaccinated_girls": round(vaccinated),
            "baseline_annual_cases": round(baseline_annual_cases, 1),
            "cases_avoided_per_year": round(cases_avoided, 1),
        }

    return results
