"""
Rebuilds every data file behind the Oral Cancer & Tobacco page, in
dependency order, from fresh downloads:

    python3 -m scripts.build_oral_cancer_data

Each step downloads its source and refuses to write partial output, so
a failure leaves the previous files untouched.
"""

import urllib3

from ingestion import (
    district_population,
    gats2,
    ncrp2020,
    nfhs5_boundaries,
    nfhs5_factsheets,
    nfhs5_report_tables,
    nfhs6_factsheets,
    ntcp_district_rop,
    state_population,
)

# Three government hosts serve incomplete certificate chains; those
# downloads skip verification (see each module) -- don't spam warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STEPS = [
    ("NFHS-5 survey boundaries (DHS SDR)", nfhs5_boundaries.run),
    ("2011 Census population, current units", state_population.run),
    ("District population 2020 (WorldPop grid)", district_population.run),
    ("NFHS-5 India Report tables", nfhs5_report_tables.run),
    ("NFHS-6 fact sheets", nfhs6_factsheets.run),
    ("NFHS-5 state + district fact sheets", nfhs5_factsheets.run),
    ("GATS-2 tobacco type by state", gats2.run),
    ("NCRP 2020 projections and stage", ncrp2020.run),
    ("NTCP sanctioned budgets (NHM district RoPs)", ntcp_district_rop.run),
]


def main():

    for name, step in STEPS:
        print(f"\n== {name}")
        step()

    print("\nAll oral cancer data rebuilt.")


if __name__ == "__main__":
    main()
