"""
Parses the tobacco tables out of the NFHS-5 India Report PDF (the same
DHS Program PDF ingestion/nfhs5_tobacco.py downloads) -- the granular
breakdowns the oral cancer page uses beyond a single per-state rate.

Tables parsed (page numbers are the report's own):
  - Table 2.36 (p.78): tobacco use, age 15+, by state x sex x
    urban/rural -- on NFHS-5's own current 36-unit boundaries.
  - Table 2.35 (p.77): tobacco use, age 15+, by sex x urban/rural x
    age group / schooling / religion / caste / wealth quintile.
  - Table 11.7 (p.461): which tobacco products are used, by sex x
    urban/rural (women 15-49, men 15-49) -- national only.
  - Table 11.10 (p.466): among current users, % who tried to quit in
    the past year and % advised to quit by a health provider; among
    everyone, % exposed to second-hand smoke -- by state x sex.

Outputs (data/reference/oral_cancer/):
  nfhs5_state_tobacco.csv, nfhs5_tobacco_by_background.csv,
  nfhs5_tobacco_products.csv, nfhs5_quitting_by_state.csv

Every parser refuses to write output if it recovers fewer rows than
the table has, rather than silently producing a partial file.
"""

import csv
import io
import re
from pathlib import Path

from pypdf import PdfReader

from ingestion.nfhs5_tobacco import download_report
from ingestion.state_names import canonical_state

OUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "data" / "reference" / "oral_cancer"
)

NUM = r"(?:\d+\.\d+|\d+|nc|na)"

REGION_HEADER_LINES = {
    "North", "Central", "East", "Northeast", "West", "South",
}


def _num(value):

    if value in ("nc", "na"):
        return None

    return float(value.replace(",", ""))


def page_texts(pdf_bytes):

    reader = PdfReader(io.BytesIO(pdf_bytes))

    return [page.extract_text() or "" for page in reader.pages]


def pages_with(texts, *markers):

    return [
        text for text in texts
        if all(marker in text for marker in markers)
    ]


def parse_state_rows(text, n_values, include_india=False):
    """
    Returns {canonical state: [n_values numbers]} from a by-state table
    page. A state name that wraps onto a second line ("Andaman &
    Nicobar\\nIslands 36.4 ...") is held and joined to the next line.
    include_india also keeps the national "India" row.
    """

    row_re = re.compile(
        rf"^(?P<name>[A-Za-z&.\-' ]+?)\s+"
        + r"\s+".join([f"(?P<v{i}>{NUM})" for i in range(n_values)])
        + r"\s*$"
    )

    rows = {}
    pending = ""

    for raw_line in text.split("\n"):

        line = raw_line.strip()

        if not line or line in REGION_HEADER_LINES:
            pending = ""
            continue

        candidate = f"{pending} {line}".strip()

        match = row_re.match(candidate)

        if match:

            name = re.sub(r"\s+", " ", match.group("name")).strip()

            state = canonical_state(name)

            if include_india and name == "India":
                state = "India"

            if state:
                rows[state] = [
                    _num(match.group(f"v{i}")) for i in range(n_values)
                ]

            pending = ""
            continue

        if not re.search(r"\d", line) and len(line) < 45:
            pending = candidate
        else:
            pending = ""

    return rows


def parse_table_2_36(texts):

    rows = {}

    for text in pages_with(texts, "Table 2.36", "Mizoram"):
        rows.update(parse_state_rows(text, 6, include_india=True))

    if len(rows) != 37:
        raise ValueError(f"Table 2.36: parsed {len(rows)} of India + 36")

    return [
        {
            "state": state,
            "women_urban_pct": v[0], "women_rural_pct": v[1],
            "women_pct": v[2],
            "men_urban_pct": v[3], "men_rural_pct": v[4],
            "men_pct": v[5],
        }
        for state, v in _india_first(rows)
    ]


def _india_first(rows):

    return [("India", rows["India"])] + sorted(
        (s, v) for s, v in rows.items() if s != "India"
    )


BACKGROUND_SECTIONS = {
    "Age": "Age",
    "Schooling": "Schooling",
    "Religion of household head": "Religion",
    "Caste/tribe of household head": "Caste/tribe",
    "Wealth quintile": "Wealth quintile",
}


def parse_table_2_35(texts):

    pages = pages_with(
        texts, "Table 2.35 Use of tobacco", "Wealth quintile"
    )

    if not pages:
        raise ValueError("Table 2.35 page not found")

    text = pages[0][pages[0].index("Table 2.35 Use of tobacco"):]

    row_re = re.compile(
        rf"^(?P<label>.+?)\s+(?P<wu>{NUM})\s+(?P<wr>{NUM})\s+"
        rf"(?P<wt>{NUM})\s+(?P<wn>[\d,]+)\s+(?P<mu>{NUM})\s+"
        rf"(?P<mr>{NUM})\s+(?P<mt>{NUM})\s+(?P<mn>[\d,]+)\s*$"
    )

    rows = []
    section = None

    for raw_line in text.split("\n"):

        line = raw_line.strip()

        if line in BACKGROUND_SECTIONS:
            section = BACKGROUND_SECTIONS[line]
            continue

        match = row_re.match(line)

        if not match or section is None:
            continue

        label = match.group("label").strip()

        if label == "Total":
            section = None
            continue

        if label.startswith("Don't know"):
            continue

        for sex, prefix in (("Women", "w"), ("Men", "m")):
            rows.append({
                "dimension": section,
                "group": label,
                "sex": sex,
                "urban_pct": _num(match.group(f"{prefix}u")),
                "rural_pct": _num(match.group(f"{prefix}r")),
                "total_pct": _num(match.group(f"{prefix}t")),
                "respondents": int(
                    match.group(f"{prefix}n").replace(",", "")
                ),
            })

    # 5 age + 6 schooling + 7 religion + 4 caste + 5 wealth = 27
    # groups, x 2 sexes.
    if len(rows) != 54:
        raise ValueError(f"Table 2.35: parsed {len(rows)} of 54 rows")

    return rows


PRODUCT_ROWS = {
    "Smokes cigarettes": ("Cigarettes", "Smoked"),
    "Smokes bidis": ("Bidis", "Smoked"),
    "Smokes cigars": ("Cigars", "Smoked"),
    "Smokes a pipe": ("Pipe", "Smoked"),
    "Smokes a hookah": ("Hookah", "Smoked"),
    "Chews paan masala or gutkha": ("Paan masala / gutkha", "Smokeless"),
    "Uses khaini": ("Khaini", "Smokeless"),
    "Chews paan with tobacco": ("Paan with tobacco", "Smokeless"),
    "Other chewing tobacco": ("Other chewing tobacco", "Smokeless"),
    "Uses snuff": ("Snuff", "Smokeless"),
}


def parse_table_11_7(texts):

    pages = pages_with(
        texts, "Table 11.7 Tobacco use by women and men", "Smokes bidis"
    )

    if not pages:
        raise ValueError("Table 11.7 page not found")

    text = pages[0]

    row_re = re.compile(
        rf"^(?P<label>[A-Za-z ]+?)\s+(?P<wu>{NUM})\s+(?P<wr>{NUM})\s+"
        rf"(?P<wt>{NUM})\s+(?P<mu>{NUM})\s+(?P<mr>{NUM})\s+"
        rf"(?P<mt>{NUM})\s+(?P<m54>{NUM})\s*$"
    )

    rows = []

    for raw_line in text.split("\n"):

        match = row_re.match(raw_line.strip())

        if not match or match.group("label") not in PRODUCT_ROWS:
            continue

        product, kind = PRODUCT_ROWS[match.group("label")]

        for sex, prefix in (("Women", "w"), ("Men", "m")):
            rows.append({
                "product": product,
                "type": kind,
                "sex": sex,
                "urban_pct": _num(match.group(f"{prefix}u")),
                "rural_pct": _num(match.group(f"{prefix}r")),
                "total_pct": _num(match.group(f"{prefix}t")),
            })

    if len(rows) != 2 * len(PRODUCT_ROWS):
        raise ValueError(f"Table 11.7: parsed {len(rows)} rows")

    return rows


def parse_table_11_10(texts):

    rows = {}

    for text in pages_with(
        texts, "Table 11.10 Quitting tobacco", "by state/union territory"
    ):
        rows.update(parse_state_rows(text, 6, include_india=True))

    if len(rows) != 37:
        raise ValueError(f"Table 11.10: parsed {len(rows)} of India + 36")

    return [
        {
            "state": state,
            "women_tried_to_quit_pct": v[0],
            "women_advised_to_quit_pct": v[1],
            "women_secondhand_smoke_pct": v[2],
            "men_tried_to_quit_pct": v[3],
            "men_advised_to_quit_pct": v[4],
            "men_secondhand_smoke_pct": v[5],
        }
        for state, v in _india_first(rows)
    ]


def write_rows(name, rows):

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    path = OUT_DIR / name

    with open(path, "w", encoding="utf-8", newline="") as file:

        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ {len(rows)} rows -> {path.relative_to(OUT_DIR.parent.parent.parent)}")


def run(pdf_bytes=None):

    if pdf_bytes is None:
        print("Downloading NFHS-5 India Report ...")
        pdf_bytes = download_report()

    texts = page_texts(pdf_bytes)

    write_rows("nfhs5_state_tobacco.csv", parse_table_2_36(texts))
    write_rows("nfhs5_tobacco_by_background.csv", parse_table_2_35(texts))
    write_rows("nfhs5_tobacco_products.csv", parse_table_11_7(texts))
    write_rows("nfhs5_quitting_by_state.csv", parse_table_11_10(texts))


if __name__ == "__main__":
    run()
