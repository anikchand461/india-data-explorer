"""
Downloads the real NFHS-5 India Report PDF from the DHS Program (the
primary government-survey publisher) and parses Table 2.36 ("Use of
tobacco by the population age 15 and over by state/union territory")
directly out of it -- replacing what was previously a hand-typed CSV
with a reproducible download-and-parse pipeline.

AI Kosh also lists an NFHS-5 factsheet dataset in our catalogue, but
it isn't in AI Kosh's bulk-downloadable set (confirmed: absent from
both a name search and an organization/owner search of all 1,178
listed datasets), and its file-download endpoint's required
"version" parameter could not be determined without guessing. The
DHS Program PDF fetched here is the actual primary source NFHS-5
data derives from either way.

Output: data/reference/nfhs5_tobacco_use_by_state.csv, mapped onto
the SAME undivided 2011-era state boundaries used by our map
geometry (see services/hpv_simulation.py and
data/reference/SOURCES.md) -- Andhra Pradesh/Telangana and Jammu &
Kashmir/Ladakh are population-weighted back into their pre-split
undivided totals.
"""

import csv
import re
from pathlib import Path

import requests
from pypdf import PdfReader

REPORT_URL = "https://dhsprogram.com/pubs/pdf/FR375/FR375.pdf"

REFERENCE_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "reference"
)

RAW_CSV_PATH = (
    REFERENCE_DIR / "nfhs5_tobacco_use_by_state_raw.csv"
)

MAPPED_CSV_PATH = (
    REFERENCE_DIR / "nfhs5_tobacco_use_by_state.csv"
)

# Real 2011 Census population for the CURRENT (post-split) units
# used only to weight-average NFHS-5's Andhra Pradesh/Telangana and
# J&K/Ladakh rows back into undivided totals -- these are the same
# figures documented in data/reference/SOURCES.md.
CURRENT_UNIT_POPULATION_2011 = {
    "Andhra Pradesh": 49_577_103,
    "Telangana": 35_003_674,
    "Jammu & Kashmir": 12_267_032,
    "Ladakh": 274_000,
}

REGION_HEADER_LINES = {
    "North", "Central", "East", "Northeast", "West", "South",
}

STATE_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z&.\-' ]+?)\s+"
    r"(?P<w_urban>[\d.]+)\s+(?P<w_rural>[\d.]+)\s+(?P<w_total>[\d.]+)\s+"
    r"(?P<m_urban>[\d.]+)\s+(?P<m_rural>[\d.]+)\s+(?P<m_total>[\d.]+)$"
)


def download_report(timeout=60):

    response = requests.get(REPORT_URL, timeout=timeout)

    response.raise_for_status()

    return response.content


def find_table_page(pdf_bytes):

    reader = PdfReader(__import__("io").BytesIO(pdf_bytes))

    for page in reader.pages:

        text = page.extract_text() or ""

        if "Table 2.36" in text and "Mizoram" in text and "India " in text:

            return text

    raise ValueError(
        "Could not find Table 2.36 in the downloaded PDF -- the "
        "report's structure may have changed."
    )


def parse_table(page_text):
    """
    Parses NFHS-5's real, current-boundary state rows out of the
    Table 2.36 page text. Handles the one two-line state name
    ("Dadra & Nagar Haveli and\\nDaman & Diu") by joining
    continuation lines that have no trailing numbers onto the next
    line before matching.
    """

    lines = [
        line.strip()
        for line in page_text.split("\n")
        if line.strip()
    ]

    raw = {}

    pending_name = ""

    for line in lines:

        if line in REGION_HEADER_LINES:
            # A bare region-section heading ("North", "East", ...) --
            # never part of a state name. Skip it outright so it
            # can't get glued onto the next real state line.
            continue

        candidate = f"{pending_name} {line}".strip()

        match = STATE_LINE_RE.match(candidate)

        if match:

            name = re.sub(r"\s+", " ", match.group("name")).strip()

            raw[name] = {
                "women": float(match.group("w_total")),
                "men": float(match.group("m_total")),
            }

            pending_name = ""

            continue

        # A state name that wraps onto the next line has no
        # trailing digits of its own -- hold it and retry combined
        # with the next line.
        if not re.search(r"\d", line) and len(line) < 60:
            pending_name = candidate
        else:
            pending_name = ""

    if len(raw) < 30:
        raise ValueError(
            f"Only parsed {len(raw)} state rows out of an expected "
            "~36 -- the table layout may not match what this parser "
            "expects. Not writing output, to avoid silently "
            "producing bad data."
        )

    return raw


def merge_to_undivided_boundaries(raw):

    mapped = dict(raw)

    def weighted(unit_a, unit_b, key):

        pop_a = CURRENT_UNIT_POPULATION_2011[unit_a]
        pop_b = CURRENT_UNIT_POPULATION_2011[unit_b]

        return (
            raw[unit_a][key] * pop_a + raw[unit_b][key] * pop_b
        ) / (pop_a + pop_b)

    if "Andhra Pradesh" in raw and "Telangana" in raw:

        mapped["Andhra Pradesh"] = {
            "men": round(
                weighted("Andhra Pradesh", "Telangana", "men"), 1
            ),
            "women": round(
                weighted("Andhra Pradesh", "Telangana", "women"), 1
            ),
        }

        mapped.pop("Telangana", None)

    if "Jammu & Kashmir" in raw and "Ladakh" in raw:

        mapped["Jammu and Kashmir"] = {
            "men": round(
                weighted("Jammu & Kashmir", "Ladakh", "men"), 1
            ),
            "women": round(
                weighted("Jammu & Kashmir", "Ladakh", "women"), 1
            ),
        }

        mapped.pop("Jammu & Kashmir", None)
        mapped.pop("Ladakh", None)

    dnh_dd_key = next(
        (k for k in raw if "Dadra" in k and "Daman" in k), None
    )

    if dnh_dd_key:

        rates = mapped.pop(dnh_dd_key)

        mapped["Daman and Diu"] = rates
        mapped["Dadra and Nagar Haveli"] = rates

    if "Delhi" in mapped:
        mapped["NCT Of Delhi"] = mapped.pop("Delhi")

    if "Andaman & Nicobar Islands" in mapped:
        # The source PDF spells this with "&"; our population/geometry
        # data spells it "and" -- without this rename the two never
        # match and this state silently drops out of every map.
        mapped["Andaman and Nicobar Islands"] = mapped.pop(
            "Andaman & Nicobar Islands"
        )

    return mapped


def write_csv(path, data):

    with open(path, "w", encoding="utf-8", newline="") as file:

        writer = csv.writer(file)

        writer.writerow(["state", "men_pct", "women_pct"])

        for state in sorted(data):

            writer.writerow(
                [state, data[state]["men"], data[state]["women"]]
            )


def run():

    print(f"Downloading {REPORT_URL} ...")

    pdf_bytes = download_report()

    print(f"✓ Downloaded {len(pdf_bytes):,} bytes")

    print("Locating and parsing Table 2.36 ...")

    page_text = find_table_page(pdf_bytes)

    raw = parse_table(page_text)

    print(f"✓ Parsed {len(raw)} state/UT rows")

    write_csv(RAW_CSV_PATH, raw)

    print(f"✓ Wrote raw (current-boundary) data to {RAW_CSV_PATH}")

    mapped = merge_to_undivided_boundaries(raw)

    write_csv(MAPPED_CSV_PATH, mapped)

    print(
        f"✓ Wrote map-ready (2011-boundary) data to {MAPPED_CSV_PATH}"
    )

    return mapped


if __name__ == "__main__":
    run()
