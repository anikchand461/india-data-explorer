"""
HPV vaccination population-impact simulation.

This is a SIMULATION, not a measurement. It combines:

  REAL DATA:
    - State boundaries: 2011 Census (PC11) state polygons, downloaded
      from AI Kosh (Development Data Lab / SHRUG dataset,
      identifier 8fdfa814-c876-4570-ae76-906c636e3584).
    - State population: 2011 Census of India official totals, using
      the SAME undivided state boundaries as the geometry (pre-2014
      Andhra Pradesh/Telangana split, pre-2019 Jammu & Kashmir/Ladakh
      split, pre-2020 Daman & Diu / Dadra & Nagar Haveli merger) so
      population and geometry refer to the same 35 units.

  MODELING ASSUMPTIONS (clearly separated, not sourced from our
  dataset catalogue -- these are standard public-health reference
  values, cited below):
    - Share of population that is girls aged 9-14 (the WHO-recommended
      primary HPV vaccination cohort): estimated at ~5.8% of total
      population, derived from the 2011 Census age structure (~29%
      of India's population was aged 0-14; assuming an even
      distribution across 15 one-year age bands and a ~50/50 sex
      split gives roughly 29% / 15 * 6 * 0.5 ~= 5.8%). This is an
      approximation, not a measured per-state figure.
    - Baseline cervical cancer incidence: 18 per 100,000 women per
      year, India's national age-standardized incidence rate per
      GLOBOCAN 2020. Reliable state-by-state incidence rates are not
      available from a single consistent source, so this national
      rate is applied UNIFORMLY across all states. Geographic
      variation in the map therefore reflects real population
      differences, not differential regional health risk.
    - Vaccine efficacy: 90%, a conservative figure consistent with
      published clinical trial ranges for HPV vaccines against the
      HPV strains they cover.

None of the modeling constants below are downloaded data -- they are
external public-health reference figures, kept separate from the
`STATE_POPULATION_2011` dict (which IS real Census data) precisely so
the two are never confused.
"""

GIRLS_9_14_SHARE_OF_POPULATION = 0.058

# 2011 Census sex ratio was ~940 females per 1000 males nationally
# -> female share of total population = 940 / 1940.
FEMALE_SHARE_OF_POPULATION = 940 / 1940

# GLOBOCAN 2020's rate is per 100,000 WOMEN, not per 100,000 total
# population -- it must be applied to the female population, not the
# whole state population, or female-specific risk is understated.
CERVICAL_CANCER_INCIDENCE_PER_100K_WOMEN = 18

VACCINE_EFFICACY = 0.90

# 2011 Census of India, official totals, undivided-state boundaries
# matching the PC11 state geometry (source: Registrar General & Census
# Commissioner of India; cross-checked via public references for the
# undivided AP/J&K/Daman-Diu totals since most modern tables report
# the post-reorganization split figures instead).
STATE_POPULATION_2011 = {
    "Jammu and Kashmir": 12_541_302,
    "Himachal Pradesh": 6_864_602,
    "Punjab": 27_743_338,
    "Chandigarh": 1_055_450,
    "Uttarakhand": 10_086_292,
    "Haryana": 25_351_462,
    "NCT Of Delhi": 16_787_941,
    "Rajasthan": 68_548_437,
    "Uttar Pradesh": 199_812_341,
    "Bihar": 104_099_452,
    "Sikkim": 610_577,
    "Arunachal Pradesh": 1_383_727,
    "Nagaland": 1_978_502,
    "Manipur": 2_570_390,
    "Mizoram": 1_097_206,
    "Tripura": 3_673_917,
    "Meghalaya": 2_966_889,
    "Assam": 31_205_576,
    "West Bengal": 91_276_115,
    "Jharkhand": 32_988_134,
    "Odisha": 41_974_219,
    "Chhattisgarh": 25_545_198,
    "Madhya Pradesh": 72_626_809,
    "Gujarat": 60_439_692,
    "Daman and Diu": 242_911,
    "Dadra and Nagar Haveli": 342_853,
    "Maharashtra": 112_374_333,
    "Andhra Pradesh": 84_580_777,
    "Karnataka": 61_095_297,
    "Goa": 1_458_545,
    "Lakshadweep": 64_473,
    "Kerala": 33_406_061,
    "Tamil Nadu": 72_147_030,
    "Puducherry": 1_247_953,
    "Andaman and Nicobar Islands": 380_581,
}


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
