"""
Downloads the Global Adult Tobacco Survey 2 (GATS-2, India, 2016-17)
report from the National Tobacco Control Programme (MoHFW) and parses
Table 4.6: current tobacco users split into smoked-only,
smokeless-only, and both, by state.

NFHS-5 gives "any tobacco" per state but not smokeless vs smoking, and
smokeless tobacco (gutkha, khaini, paan with tobacco) -- not smoking --
is the dominant driver of oral cancer in India. GATS-2 is the most
recent survey with that split per state; the oral cancer model applies
each state's GATS-2 *mix* to its NFHS-5/6 prevalence.

GATS-2 predates the 2019-20 reorganizations and omits four small UTs
(Andaman & Nicobar, Lakshadweep, Dadra & Nagar Haveli and Daman & Diu,
and Ladakh, then part of J&K) -- 32 of the 36 current units. The model
falls back to J&K's mix for Ladakh and the national mix for the rest.

Output: data/reference/oral_cancer/gats2_tobacco_type_by_state.csv
"""

import csv
import io
from pathlib import Path

import requests
from pypdf import PdfReader

from ingestion.nfhs5_report_tables import parse_state_rows

REPORT_URL = (
    "https://ntcp.mohfw.gov.in/assets/document/"
    "surveys-reports-publications/"
    "Global-Adult-Tobacco-Survey-Second-Round-India-2016-2017.pdf"
)

OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "reference" / "oral_cancer"
    / "gats2_tobacco_type_by_state.csv"
)


def download(timeout=180):

    # ntcp.mohfw.gov.in serves an incomplete certificate chain; the
    # report is public, so verification is skipped for this host only.
    response = requests.get(REPORT_URL, timeout=timeout, verify=False)

    response.raise_for_status()

    return response.content


def parse(pdf_bytes):

    reader = PdfReader(io.BytesIO(pdf_bytes))

    for page in reader.pages:

        text = page.extract_text() or ""

        if "Table 4.6" in text and "Smokeless" in text and "Odisha" in text:

            rows = parse_state_rows(text, 6)

            national = next(
                line for line in text.split("\n")
                if line.startswith("India ")
            ).split()[1:5]

            break

    else:
        raise ValueError("GATS-2 Table 4.6 not found")

    if len(rows) != 32:
        raise ValueError(f"GATS-2 Table 4.6: parsed {len(rows)} of 32")

    def row(state, values):

        current, smoked, smokeless, both = values[:4]

        # Each row's three types must add up to "current user".
        if abs(smoked + smokeless + both - current) > 0.25:
            raise ValueError(f"GATS-2 {state}: types don't sum")

        return {
            "state": state,
            "current_user_pct": current,
            "smoked_only_pct": smoked,
            "smokeless_only_pct": smokeless,
            "both_pct": both,
        }

    return [row("India", [float(v) for v in national])] + [
        row(state, values) for state, values in sorted(rows.items())
    ]


def run(pdf_bytes=None):

    if pdf_bytes is None:
        print(f"Downloading {REPORT_URL} ...")
        pdf_bytes = download()

    rows = parse(pdf_bytes)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ GATS-2: {len(rows)} rows -> {OUT_PATH.name}")


if __name__ == "__main__":
    run()
