"""
Oral cancer risk projection driven by real, state-level tobacco-use
data -- built to replace the earlier HPV simulation's flat national
rate with actual geographic variation.

REAL DATA:
  - Tobacco use prevalence by state/UT, separately for men and
    women: NFHS-5 (2019-21) official India Report, Table 2.36
    ("Use of tobacco by the population age 15 and over by
    state/union territory"), Ministry of Health & Family Welfare /
    DHS Program (https://dhsprogram.com/pubs/pdf/FR375/FR375.pdf,
    page 79-80). Transcribed directly from the published table.
  - National baseline oral cancer incidence: 10.4 per 100,000
    (age-standardized rate), National Cancer Registry Programme
    (NCRP), India.
  - State population: 2011 Census totals (same source/values as
    services/hpv_simulation.py), used to weight-average NFHS-5
    figures across state boundaries that have since split (see
    below), and to convert incidence rates into case counts.

STATE BOUNDARY RECONCILIATION (NFHS-5 uses CURRENT state boundaries,
our map geometry is 2011-era undivided boundaries -- see
services/hpv_simulation.py for why):
  - Andhra Pradesh (undivided) = population-weighted average of
    NFHS-5's separate Andhra Pradesh and Telangana figures.
  - Jammu and Kashmir (undivided, includes Ladakh) =
    population-weighted average of NFHS-5's separate J&K and
    Ladakh figures.
  - Daman and Diu / Dadra and Nagar Haveli: NFHS-5 already reports
    these as one merged UT ("Dadra & Nagar Haveli and Daman & Diu");
    that single rate is applied to both of our shapefile's separate
    2011-era entries, since the merged figure cannot be
    disaggregated back into two.

MODELING ASSUMPTION (clearly separated from the real data above):
  Oral cancer risk is assumed to scale linearly with a state's
  tobacco-use prevalence relative to the national average, applied
  to the national baseline incidence rate. This is standard
  practice given tobacco/smokeless tobacco is the dominant,
  well-established driver of oral cancer in India (NCRP, multiple
  peer-reviewed sources) -- but it IS a modeling simplification, not
  a directly measured state-level cancer rate (no consistent
  state-by-state oral cancer incidence source exists).

ON THE "SWEDEN" BENCHMARK:
  The literature does NOT support "snus reduces oral cancer" as a
  direct mechanism -- multiple pooled prospective studies of
  Swedish snus users show a NULL association with oral cancer risk
  specifically (relative risk ~0.86-1.1). What Sweden DID achieve,
  genuinely and well-documented, is a 44% lower tobacco-related
  mortality and 41% fewer cancer cases than the EU average, driven
  by smokers substituting snus for cigarettes (smoking prevalence
  fell from 35%/28% in 1980 to 5.8% by 2022). That 44% figure is
  used here as a labeled POLICY-AMBITION BENCHMARK -- "what a
  comparable tobacco-reduction success would mean for India's own,
  real, oral-cancer-driving product (smokeless tobacco)" -- not as
  a claim that snus itself lowers oral cancer risk.
"""

NATIONAL_ORAL_CANCER_INCIDENCE_PER_100K = 10.4

NATIONAL_TOBACCO_USE_MEN = 38.0
NATIONAL_TOBACCO_USE_WOMEN = 8.9

SWEDEN_BENCHMARK_REDUCTION_PCT = 44

# NFHS-5 Table 2.36, state/UT totals (%), men and women separately.
# Keys match services.hpv_simulation.STATE_POPULATION_2011 exactly.
STATE_TOBACCO_USE = {
    "Jammu and Kashmir": {"men": 38.4, "women": 3.6},
    "Himachal Pradesh": {"men": 32.2, "women": 1.7},
    "Punjab": {"men": 12.8, "women": 0.4},
    "Chandigarh": {"men": 11.9, "women": 0.6},
    "Uttarakhand": {"men": 33.7, "women": 4.6},
    "Haryana": {"men": 29.1, "women": 2.6},
    "NCT Of Delhi": {"men": 26.2, "women": 2.2},
    "Rajasthan": {"men": 41.9, "women": 6.9},
    "Uttar Pradesh": {"men": 44.0, "women": 8.5},
    "Bihar": {"men": 48.9, "women": 5.0},
    "Sikkim": {"men": 41.5, "women": 11.6},
    "Arunachal Pradesh": {"men": 50.3, "women": 18.8},
    "Nagaland": {"men": 48.4, "women": 13.7},
    "Manipur": {"men": 58.0, "women": 43.3},
    "Mizoram": {"men": 73.1, "women": 61.7},
    "Tripura": {"men": 57.2, "women": 50.5},
    "Meghalaya": {"men": 57.8, "women": 28.3},
    "Assam": {"men": 51.9, "women": 22.2},
    "West Bengal": {"men": 48.1, "women": 10.8},
    "Jharkhand": {"men": 47.4, "women": 8.4},
    "Odisha": {"men": 51.7, "women": 26.1},
    "Chhattisgarh": {"men": 43.1, "women": 17.3},
    "Madhya Pradesh": {"men": 46.4, "women": 10.3},
    "Gujarat": {"men": 41.2, "women": 8.7},
    "Daman and Diu": {"men": 38.5, "women": 2.9},
    "Dadra and Nagar Haveli": {"men": 38.5, "women": 2.9},
    "Maharashtra": {"men": 33.8, "women": 11.0},
    "Andhra Pradesh": {"men": 22.5, "women": 4.6},
    "Karnataka": {"men": 27.3, "women": 8.6},
    "Goa": {"men": 18.1, "women": 2.6},
    "Lakshadweep": {"men": 28.5, "women": 17.5},
    "Kerala": {"men": 16.9, "women": 2.2},
    "Tamil Nadu": {"men": 20.0, "women": 4.9},
    "Puducherry": {"men": 14.8, "women": 2.6},
    "Andaman and Nicobar Islands": {"men": 58.7, "women": 31.2},
}


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
