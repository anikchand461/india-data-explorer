"""
Downloads the NFHS-6 (2023-24) India & State/UT Fact Sheets PDF
published by IIPS (May 2026) and parses the tobacco and alcohol
indicators for every state, giving a real NFHS-5 -> NFHS-6 trend.

Each state's fact sheet has a "<State> - Key Indicators" header and
rows like:
  98. Women age 15 years and above who use any kind of tobacco (%)
      4.6  10.0  8.4    8.9
whose four numbers are NFHS-6 urban, rural, total, then the NFHS-5
total for comparison. (Indicator numbers 98-101 in NFHS-6; the
NFHS-5 fact sheets numbered the same indicators differently.)

NFHS-6 did not survey Manipur, so it has 35 of the 36 states/UTs.
NFHS-6 has no cancer-screening indicator.

Output: data/reference/oral_cancer/nfhs6_state_tobacco.csv
"""

import csv
import io
import re
from pathlib import Path

import requests
from pypdf import PdfReader

from ingestion.state_names import canonical_state

FACTSHEET_URL = (
    "https://www.nfhsiips.in/nfhsuser/assets/"
    "National%20Family%20Health%20Survey%20(NFHS-6)%202023-2024"
    "%20Fact%20Sheets.pdf"
)

OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "reference" / "oral_cancer" / "nfhs6_state_tobacco.csv"
)

INDICATORS = {
    "Women age 15 years and above who use any kind of tobacco":
        "women_tobacco",
    "Men age 15 years and above who use any kind of tobacco":
        "men_tobacco",
    "Women age 15 years and above who consume alcohol":
        "women_alcohol",
    "Men age 15 years and above who consume alcohol":
        "men_alcohol",
}

NUM = r"\(?(\d+\.\d+|\d+|na|\*)\)?"

HEADER_RE = re.compile(r"^\s*(?P<name>.+?)\s+-\s+Key Indicators", re.M)


def download(timeout=180):

    # nfhsiips.in serves an incomplete certificate chain; the PDF is
    # public, so certificate verification is skipped for this host
    # only.
    response = requests.get(FACTSHEET_URL, timeout=timeout, verify=False)

    response.raise_for_status()

    return response.content


def _value(text):

    return None if text in ("na", "*") else float(text)


def parse(pdf_bytes):

    reader = PdfReader(io.BytesIO(pdf_bytes))

    rows = {}
    current = None

    for page in reader.pages:

        text = page.extract_text() or ""

        header = HEADER_RE.search(text[:300])

        if header:
            name = header.group("name").strip()
            current = "India" if name == "India" else canonical_state(name)

        if current is None:
            continue

        for line in text.split("\n"):

            for label, key in INDICATORS.items():

                if label not in line:
                    continue

                # The fact sheet is followed by annex pages (e.g.
                # standard errors) that reuse the same indicator
                # wording; only the first occurrence is the fact sheet.
                if f"{key}_pct" in rows.get(current, {}):
                    continue

                numbers = re.findall(NUM, line.split("(%)", 1)[-1])

                if len(numbers) < 4:
                    raise ValueError(
                        f"{current}: expected 4 numbers in {line!r}"
                    )

                urban, rural, total, nfhs5 = (
                    _value(n) for n in numbers[:4]
                )

                row = rows.setdefault(current, {"state": current})

                row[f"{key}_urban_pct"] = urban
                row[f"{key}_rural_pct"] = rural
                row[f"{key}_pct"] = total
                row[f"{key}_nfhs5_pct"] = nfhs5

    complete = {
        state: row for state, row in rows.items()
        if len(row) == 1 + 4 * len(INDICATORS)
    }

    # India + 35 states/UTs (Manipur not surveyed).
    if len(complete) != 36 or "Manipur" in complete:
        raise ValueError(
            f"NFHS-6: parsed {len(complete)} complete fact sheets, "
            "expected India + 35 states/UTs."
        )

    return [complete["India"]] + [
        complete[s] for s in sorted(complete) if s != "India"
    ]


def write(rows):

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as file:

        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(pdf_bytes=None):

    if pdf_bytes is None:
        print(f"Downloading {FACTSHEET_URL} ...")
        pdf_bytes = download()

    rows = parse(pdf_bytes)

    write(rows)

    print(f"✓ NFHS-6: {len(rows)} rows -> {OUT_PATH.name}")


if __name__ == "__main__":
    run()
