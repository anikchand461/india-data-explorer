"""
NFHS-5 (2019-21) state and district fact-sheet indicators for the oral
cancer page: tobacco use by sex, alcohol use by sex, and the share of
adults ever screened for oral cancer.

WHY THIRD-PARTY EXTRACTIONS: the official fact sheets are ~750
separate PDFs that were hosted at rchiips.org/nfhs, which now returns
404 (the NFHS portal moved to nfhsiips.in, which no longer links
them). So this uses openly licensed CSV extractions of those PDFs and
CROSS-VALIDATES them against each other instead of trusting any one:

  STATES   pratapvardhan/NFHS-5 NFHS-5-States.csv (CC BY 4.0,
           doi:10.7910/DVN/42WNZF). Its tobacco totals are checked
           against our own parse of NFHS-5 report Table 2.36.

  DISTRICTS (primary)   sthejas87/nfhs5DistrictAmenityAnalysis
           -- all 707 districts, 104 indicators plus sample sizes.
  DISTRICTS (check A)   pratapvardhan/NFHS-5 NFHS-5-Districts.csv --
           phase-1 only (21 states, ~340 districts).
  DISTRICTS (check B)   sgrsharma016-ctrl/nfhs5-ncd-ecological-analysis
           -- all 707 districts, tobacco/alcohol only.

Validation outcome (re-checked on every run, see validate_districts):
  - Primary vs check A: identical tobacco values on every shared
    district except Dhule (see DISPUTED).
  - Primary has one corrupt row: Mizoram's "Saiha" is missing and a
    copy of Manipur's "Chandel" row sits in its place. Check B has
    Saiha's real row, so it is patched from there and flagged.
  - Primary vs check B disagree on 8 districts (6 in Delhi, plus
    Mahoba/Mahrajganj in UP) in a pattern that looks like rows
    shifted in one of the two -- but neither can be confirmed against
    the (offline) originals, so those 8 (plus Dhule, below) are kept but marked
    disputed=True and the page leaves them uncoloured on maps.

Outputs (data/reference/oral_cancer/):
  nfhs5_state_screening.csv   state, oral screening women/men 30-49,
                              alcohol women/men 15+, sex ratio
  nfhs5_district_indicators.csv  one row per district, keyed to
                              data/geo/nfhs5_districts.geojson ids
"""

import csv
import io
import json
import re
from pathlib import Path

import pandas as pd
import requests

from ingestion.state_names import canonical_state

ROOT = Path(__file__).resolve().parent.parent

OUT_DIR = ROOT / "data" / "reference" / "oral_cancer"

DISTRICT_GEOJSON = ROOT / "data" / "geo" / "nfhs5_districts.geojson"

RAW = "https://raw.githubusercontent.com"

STATES_URL = f"{RAW}/pratapvardhan/NFHS-5/master/NFHS-5-States.csv"

DISTRICTS_PRIMARY_URL = (
    f"{RAW}/sthejas87/nfhs5DistrictAmenityAnalysis/HEAD/"
    "NFHS_5_India_Districts_Factsheet_Data.csv"
)

DISTRICTS_CHECK_A_URL = (
    f"{RAW}/pratapvardhan/NFHS-5/master/NFHS-5-Districts.csv"
)

DISTRICTS_CHECK_B_URL = (
    f"{RAW}/sgrsharma016-ctrl/nfhs5-ncd-ecological-analysis/HEAD/"
    "nfhs5_district_ncd.csv"
)

PRIMARY_COLUMNS = {
    "Women age 15 years and above who use any kind of tobacco (%)":
        "women_tobacco_pct",
    "Men age 15 years and above who use any kind of tobacco (%)":
        "men_tobacco_pct",
    "Women age 15 years and above who consume alcohol (%)":
        "women_alcohol_pct",
    "Men age 15 years and above who consume alcohol (%)":
        "men_alcohol_pct",
    "Women (age 30-49 years) Ever undergone an oral cavity "
    "examination for oral cancer (%)":
        "women_oral_screening_pct",
    "Female population age 6 years and above who ever attended "
    "school (%)":
        "female_ever_schooled_pct",
    "Number of Households surveyed": "households_surveyed",
    "Number of Women age 15-49 years interviewed": "women_interviewed",
    "Number of Men age 15-54 years interviewed": "men_interviewed",
}

# District spellings that differ between the fact-sheet extraction
# and the DHS boundary file: (state, fact-sheet name) -> boundary name.
BOUNDARY_ALIASES = {
    ("Andhra Pradesh", "Sri Potti Sriramulu Nello"):
        "Sri Potti Sriramulu Nellore",
    ("Bihar", "Buxar"): "Buxer",
    ("Ladakh", "Leh(Ladakh)"): "Leh",
    ("Uttar Pradesh", "Mahrajganj"): "Maharajganj",
    ("Uttar Pradesh", "Sant Ravidas Nagar (Bhadohi)"):
        "Sant Ravidas Nagar",
    ("West Bengal", "North Twenty Four Pargana"):
        "North Twenty Four Parganas",
    ("West Bengal", "South Twenty Four Pargana"):
        "South Twenty Four Parganas",
}

DISPUTED = {
    ("Delhi", "North"), ("Delhi", "North East"), ("Delhi", "North West"),
    ("Delhi", "South"), ("Delhi", "South East"), ("Delhi", "South West"),
    ("Uttar Pradesh", "Mahoba"), ("Uttar Pradesh", "Mahrajganj"),
    # Both check extractions shift Dhule's values one column (giving
    # women's alcohol use 38.2% / women's tobacco 0.0%); the primary's
    # values fit neighbouring districts but can't be confirmed either.
    ("Maharashtra", "Dhule"),
}


def _key(name):

    return re.sub(r"[^a-z]", "", str(name).lower().replace("&", "and"))


def fetch_csv(url, timeout=120):

    response = requests.get(url, timeout=timeout)

    response.raise_for_status()

    return pd.read_csv(io.StringIO(response.text))


# --- States -----------------------------------------------------------

STATE_INDICATORS = {
    "3.": "sex_ratio_females_per_1000",
    "113.": "women_oral_screening_pct",
    "114.": "men_oral_screening_pct",
    "128.": "women_tobacco_pct",
    "129.": "men_tobacco_pct",
    "130.": "women_alcohol_pct",
    "131.": "men_alcohol_pct",
}


def build_states(states_df, report_tobacco):
    """
    report_tobacco: {state: (women_pct, men_pct)} from our own parse of
    NFHS-5 report Table 2.36, used to validate this extraction.
    """

    rows = {}

    for _, row in states_df.iterrows():

        prefix = str(row["indicator"]).split(" ", 1)[0]

        if prefix not in STATE_INDICATORS:
            continue

        name = row["state"]

        state = "India" if name == "India" else canonical_state(name)

        if state is None:
            raise ValueError(f"Unknown state {name!r}")

        rows.setdefault(state, {"state": state})[
            STATE_INDICATORS[prefix]
        ] = row["nfhs5_total"]

    mismatches = [
        state for state, (women, men) in report_tobacco.items()
        if abs(rows[state]["women_tobacco_pct"] - women) > 0.5
        or abs(rows[state]["men_tobacco_pct"] - men) > 0.5
    ]

    if mismatches:
        raise ValueError(
            "State fact-sheet tobacco disagrees with NFHS-5 report "
            f"Table 2.36 by >0.5pp for: {mismatches}"
        )

    if len(rows) != 37:
        raise ValueError(f"Expected India + 36 states, got {len(rows)}")

    return [rows["India"]] + [
        rows[s] for s in sorted(rows) if s != "India"
    ]


# --- Districts --------------------------------------------------------

def prepare_primary(primary):

    primary.columns = [c.strip() for c in primary.columns]

    df = primary.rename(columns=PRIMARY_COLUMNS)

    df["state"] = df["State/UT"].map(canonical_state)
    df["district"] = df["District Names"].str.strip()

    if df["state"].isna().any():
        raise ValueError(
            "Unknown states in district file: "
            f"{df.loc[df['state'].isna(), 'State/UT'].unique()}"
        )

    for column in PRIMARY_COLUMNS.values():
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df[["state", "district", *PRIMARY_COLUMNS.values()]].copy()


def prepare_check_b(check_b):

    df = check_b.rename(columns={
        "State": "state_raw", "District": "district",
        "tobacco_women_pct": "women_tobacco_pct",
        "tobacco_men_pct": "men_tobacco_pct",
        "alcohol_women_pct": "women_alcohol_pct",
        "alcohol_men_pct": "men_alcohol_pct",
    })

    df["state"] = df["state_raw"].map(canonical_state)

    return df


def patch_saiha(primary, check_b):
    """
    The primary extraction lists 'Chandel' (a Manipur district) under
    Mizoram, duplicating Manipur's Chandel row, and has no Saiha.
    Replace it with Saiha's row from check B.
    """

    bad = (primary["state"] == "Mizoram") & (
        primary["district"] == "Chandel"
    )

    if not bad.any():
        return primary, False

    saiha = check_b[
        (check_b["state"] == "Mizoram") & (check_b["district"] == "Saiha")
    ]

    if len(saiha) != 1:
        raise ValueError("Saiha not found in check-B extraction")

    index = primary.index[bad][0]

    for column in primary.columns:
        if column not in ("state",):
            primary.at[index, column] = None

    primary.at[index, "district"] = "Saiha"

    for column in (
        "women_tobacco_pct", "men_tobacco_pct",
        "women_alcohol_pct", "men_alcohol_pct",
    ):
        primary.at[index, column] = saiha.iloc[0][column]

    return primary, True


def validate_districts(primary, check_a, check_b):

    report = {}

    # Check A: phase-1 extraction, long format.
    a = check_a[check_a["Indicator"].str.startswith(("101.", "102."))]
    a = a.pivot_table(
        index=["State", "District"], columns="Indicator",
        values="NFHS-5", aggfunc="first",
    ).reset_index()
    a.columns = ["state_raw", "district", "women_a", "men_a"]
    a["state"] = a["state_raw"].map(canonical_state)

    merged = primary.assign(k=primary["district"].map(_key)).merge(
        a.assign(k=a["district"].map(_key)), on=["state", "k"],
    )

    a_diff = merged[
        (abs(merged["women_tobacco_pct"] - merged["women_a"]) > 0.05)
        | (abs(merged["men_tobacco_pct"] - merged["men_a"]) > 0.05)
    ]

    report["check_a_shared"] = len(merged)
    report["check_a_disagreements"] = sorted(
        zip(a_diff["state"], a_diff["district_x"])
    )

    # Check B: full extraction.
    merged_b = primary.assign(k=primary["district"].map(_key)).merge(
        check_b.assign(k=check_b["district"].map(_key)),
        on=["state", "k"], suffixes=("", "_b"),
    )

    b_diff = merged_b[
        (abs(merged_b["women_tobacco_pct"]
             - merged_b["women_tobacco_pct_b"]) > 0.05)
        | (abs(merged_b["men_tobacco_pct"]
               - merged_b["men_tobacco_pct_b"]) > 0.05)
    ]

    report["check_b_shared"] = len(merged_b)
    report["check_b_disagreements"] = sorted(
        zip(b_diff["state"], b_diff["district"])
    )

    unexpected = (
        set(report["check_a_disagreements"])
        | set(report["check_b_disagreements"])
    ) - DISPUTED

    if unexpected:
        raise ValueError(
            "New disagreements between district extractions: "
            f"{sorted(unexpected)}"
        )

    return report


def attach_boundary_ids(primary):

    with open(DISTRICT_GEOJSON, "r", encoding="utf-8") as file:
        geo = json.load(file)

    lookup = {
        (f["properties"]["state"], _key(f["properties"]["district"])):
            f["properties"]["district_id"]
        for f in geo["features"]
    }

    ids = []
    unmatched = []

    for state, district in zip(primary["state"], primary["district"]):

        name = BOUNDARY_ALIASES.get((state, district), district)

        district_id = lookup.get((state, _key(name)))

        if district_id is None:
            unmatched.append((state, district))

        ids.append(district_id)

    if unmatched:
        raise ValueError(f"Districts with no boundary match: {unmatched}")

    if len(set(ids)) != len(ids):
        raise ValueError("Two fact-sheet rows matched the same boundary")

    primary.insert(0, "district_id", ids)

    return primary


def write_rows(name, rows):

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_DIR / name, "w", encoding="utf-8", newline="") as file:

        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run():

    report_tobacco = {}

    with open(OUT_DIR / "nfhs5_state_tobacco.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            report_tobacco[row["state"]] = (
                float(row["women_pct"]), float(row["men_pct"])
            )

    print("Downloading NFHS-5 state fact-sheet extraction ...")
    states = build_states(fetch_csv(STATES_URL), report_tobacco)
    write_rows("nfhs5_state_screening.csv", states)
    print(f"✓ {len(states)} rows (validated against Table 2.36)")

    print("Downloading NFHS-5 district fact-sheet extractions ...")
    primary = prepare_primary(fetch_csv(DISTRICTS_PRIMARY_URL))
    check_a = fetch_csv(DISTRICTS_CHECK_A_URL)
    check_b = prepare_check_b(fetch_csv(DISTRICTS_CHECK_B_URL))

    primary, patched = patch_saiha(primary, check_b)

    report = validate_districts(primary, check_a, check_b)

    print(
        f"✓ check A: {report['check_a_shared']} shared districts, "
        f"{len(report['check_a_disagreements'])} known disputed"
    )
    print(
        f"✓ check B: {report['check_b_shared']} shared districts, "
        f"{len(report['check_b_disagreements'])} known disputed"
    )

    primary["disputed"] = [
        (s, d) in DISPUTED
        for s, d in zip(primary["state"], primary["district"])
    ]
    primary["patched_from_check_b"] = (
        patched
        & (primary["state"] == "Mizoram")
        & (primary["district"] == "Saiha")
    )

    primary = attach_boundary_ids(primary)

    rows = primary.astype(object).where(primary.notna(), None)
    write_rows(
        "nfhs5_district_indicators.csv", rows.to_dict(orient="records")
    )

    print(f"✓ {len(primary)} districts matched to boundaries")


if __name__ == "__main__":
    run()
