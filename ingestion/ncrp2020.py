"""
Downloads the ICMR-NCDIR "Report of National Cancer Registry Programme
2020" (registry data 2012-2016) and parses:

  - Table 14.1: projected number of new cancer cases in India by site
    and sex, 2016-2020 and 2025. Only Tongue (C01-C02) and Mouth
    (C03-C06) are kept -- together, oral cavity cancer. These national
    totals anchor the oral cancer page's case estimates instead of an
    incidence rate x 2011 Census population.
  - Table 9.2.1: clinical extent of disease at diagnosis for mouth
    cancer (localised / locoregional / distant), from the hospital
    registries -- how late cases are caught.

Outputs (data/reference/oral_cancer/):
  ncrp_oral_cancer_projections.csv   site, sex, year, cases
  ncrp_mouth_cancer_stage.csv        stage, men/women/both n and %
"""

import csv
import io
import re
from pathlib import Path

import requests
from pypdf import PdfReader

REPORT_URL = (
    "https://ncdirindia.org/All_Reports/Report_2020/resources/"
    "NCRP_2020_2012_16.pdf"
)

OUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "data" / "reference" / "oral_cancer"
)

PROJECTION_YEARS = [2016, 2017, 2018, 2019, 2020, 2025]

STAGES = ["Localised only", "Locoregional", "Distant Metastasis", "Unknown"]


def download(timeout=300):

    # ncdirindia.org serves an incomplete certificate chain; the report
    # is public, so verification is skipped for this host only.
    response = requests.get(REPORT_URL, timeout=timeout, verify=False)

    response.raise_for_status()

    return response.content


def parse_projections(texts):

    page = next(
        (t for t in texts if "Table 14.1 Projected Number" in t), None
    )

    if page is None:
        raise ValueError("NCRP Table 14.1 not found")

    rows = []

    for site in ("Tongue", "Mouth"):

        line = next(
            l for l in page.split("\n") if l.startswith(f"{site} ")
        )

        numbers = [int(n) for n in re.findall(r"\d+", line)]

        if len(numbers) != 18:
            raise ValueError(f"Table 14.1 {site}: {len(numbers)} values")

        for s_index, sex in enumerate(("Men", "Women", "Both")):

            for y_index, year in enumerate(PROJECTION_YEARS):

                rows.append({
                    "site": site,
                    "sex": sex,
                    "year": year,
                    "cases": numbers[s_index * 6 + y_index],
                })

    # Men + women must equal "both sexes" in every column.
    by_key = {(r["site"], r["sex"], r["year"]): r["cases"] for r in rows}

    for site in ("Tongue", "Mouth"):
        for year in PROJECTION_YEARS:
            total = by_key[(site, "Men", year)] + by_key[(site, "Women", year)]
            if abs(total - by_key[(site, "Both", year)]) > 2:
                raise ValueError(f"Table 14.1 {site} {year}: sexes don't sum")

    return rows


def parse_stage(texts):

    page = next(
        (t for t in texts if "Table 9.2.1 Number (n)" in t), None
    )

    if page is None:
        raise ValueError("NCRP Table 9.2.1 not found")

    section = page[page.index("Table 9.2.1"):]

    rows = []

    for stage in STAGES:

        line = next(
            l for l in section.split("\n") if l.startswith(stage)
        )

        values = re.findall(r"\d+\.\d+|\d+", line[len(stage):])

        men_n, men_pct, women_n, women_pct, both_n, both_pct = values[:6]

        rows.append({
            "stage": stage,
            "men_n": int(men_n), "men_pct": float(men_pct),
            "women_n": int(women_n), "women_pct": float(women_pct),
            "both_n": int(both_n), "both_pct": float(both_pct),
        })

    return rows


def write_rows(name, rows):

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_DIR / name, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ NCRP: {len(rows)} rows -> {name}")


def run(pdf_bytes=None):

    if pdf_bytes is None:
        print(f"Downloading {REPORT_URL} ...")
        pdf_bytes = download()

    reader = PdfReader(io.BytesIO(pdf_bytes))

    texts = [page.extract_text() or "" for page in reader.pages]

    write_rows("ncrp_oral_cancer_projections.csv", parse_projections(texts))
    write_rows("ncrp_mouth_cancer_stage.csv", parse_stage(texts))


if __name__ == "__main__":
    run()
