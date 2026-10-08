"""
2011 Census population for the 36 CURRENT states/UTs, derived from
data/reference/state_population_2011.csv (undivided 2011 boundaries)
by splitting the units that were reorganized after 2011:

  - Andhra Pradesh (undivided) -> Andhra Pradesh 49,577,103 +
    Telangana 35,003,674 (2011 Census figures for the post-2014
    districts; they sum exactly to the undivided total).
  - Jammu and Kashmir (undivided) -> Ladakh 274,289 (2011 Census: Leh
    133,487 + Kargil 140,802) + Jammu & Kashmir (the remainder).
  - Dadra and Nagar Haveli + Daman and Diu -> merged into one UT (2020).

The oral cancer model only uses these to split national totals
between states, so what matters is each state's SHARE -- a 2011 share
is an approximation (states have grown at different rates since).

Output: data/reference/oral_cancer/state_population_2011_current.csv
"""

import csv
from pathlib import Path

from ingestion.state_names import CANONICAL_STATES, canonical_state

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"

OUT_PATH = REFERENCE_DIR / "oral_cancer" / "state_population_2011_current.csv"

TELANGANA_2011 = 35_003_674
LADAKH_2011 = 133_487 + 140_802


def build():

    with open(
        REFERENCE_DIR / "state_population_2011.csv", encoding="utf-8"
    ) as file:
        undivided = {
            row["state"]: int(row["population"])
            for row in csv.DictReader(file)
        }

    population = {}

    for name, value in undivided.items():

        if name in ("Daman and Diu", "Dadra and Nagar Haveli"):
            key = "Dadra & Nagar Haveli and Daman & Diu"
            population[key] = population.get(key, 0) + value
            continue

        population[canonical_state(name)] = value

    population["Telangana"] = TELANGANA_2011
    population["Andhra Pradesh"] -= TELANGANA_2011

    population["Ladakh"] = LADAKH_2011
    population["Jammu & Kashmir"] -= LADAKH_2011

    if sorted(population) != sorted(CANONICAL_STATES):
        raise ValueError("Population file doesn't cover the 36 units")

    if sum(population.values()) != sum(undivided.values()):
        raise ValueError("Split populations don't sum to the original")

    return population


def run():

    population = build()

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["state", "population_2011"])
        for state in sorted(population):
            writer.writerow([state, population[state]])

    print(f"✓ {len(population)} states/UTs -> {OUT_PATH.name}")


if __name__ == "__main__":
    run()
