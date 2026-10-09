"""
Downloads National Health Mission district Records of Proceedings
(RoPs) and extracts each district's sanctioned National Tobacco Control
Programme (NTCP) budget.

Actual NTCP expenditure is not published below state level; the RoPs
are the finest public figure, and they are approvals ("budget
sanctioned"), not money spent. Every RoP lists NTCP under NCD.4 with
the same FMR activity codes:

    104  Implementation of COTPA 2003 (enforcement squads, IEC, training)
    105  Implementation of ToFEI guidelines (tobacco-free schools)
    106  Tobacco cessation (cessation centres, medicines, training)

Only these activity lines are summed. NTCP staff salaries sit in each
RoP's human-resources section under a different code, and are left out
so that states are compared like for like.

States covered, and why the others are not (yet):

    Haryana       FY 2024-25, 22 district PDFs (layout text)
    Sikkim        FY 2024-25, one workbook; 6 current districts are
                  summed into NFHS-5's 4 (Pakyong was carved from East,
                  Soreng from West, in 2021)
    Meghalaya     FY 2024-25, one workbook with a state (SPMU) column
    Uttarakhand   FY 2024-25, 13 district PDFs
    Odisha        FY 2024-25 (from 2024-26 approvals), 30 district PDFs

    Assam publishes a dedicated NTCP district sheet, but its totals row
    shifts columns from page to page; Rajasthan's district annexures
    have no NTCP folder; Andhra Pradesh's 26 post-2022 districts do not
    map onto NFHS-5's 13.

Outputs (data/reference/oral_cancer/):
    ntcp_district_budget.csv  one row per NFHS-5 district
    ntcp_state_split.csv      state-HQ vs district share, where the
                              RoP shows both (Sikkim, Meghalaya)
"""

import csv
import io
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import openpyxl
import requests
from pypdf import PdfReader

OUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "data" / "reference" / "oral_cancer"
)

DISTRICT_PATH = OUT_DIR / "ntcp_district_budget.csv"
SPLIT_PATH = OUT_DIR / "ntcp_state_split.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

CODES = ("104", "105", "106")

# --- Haryana -----------------------------------------------------------

HARYANA_PAGE = "https://nhmharyana.gov.in/page?id=284"

# RoP file name -> NFHS-5 district name, where they differ.
HARYANA_NAMES = {
    "CharkhiDadri": "Charkhi Dadri",
    "Gurugram": "Gurgaon",
    "Narnaul": "Mahendragarh",
}

# --- Sikkim ------------------------------------------------------------

SIKKIM_PAGE = "https://nhmsikkim.org/pip-rops/rops"

# Current district -> NFHS-5 district it was part of in 2019-21.
SIKKIM_NAMES = {
    "Gangtok": "East District",
    "Pakyong": "East District",
    "Gyalshing": "West District",
    "Soreng": "West District",
    "Mangan": "North  District",
    "Namchi": "South District",
}

# --- Meghalaya ---------------------------------------------------------

MEGHALAYA_PAGE = "https://nhmmeghalaya.nic.in/ROPs.html"

MEGHALAYA_NAMES = {
    "EKH": "East Khasi Hills",
    "WKH": "West Khasi Hills",
    "SWKH": "South West Khasi Hills",
    "WJH": "West Jaintia Hills",
    "EJH": "East Jantia Hills",
    "RB": "Ribhoi",
    "WGH": "West Garo Hills",
    "SWGH": "South West Garo Hills",
    "EGH": "East Garo Hills",
    "NGH": "North Garo Hills",
    "SGH": "South Garo Hills",
}

# --- Odisha ------------------------------------------------------------

ODISHA_PAGE = "https://nhmodisha.gov.in/pips/"

ODISHA_AJAX = "https://nhmodisha.gov.in/wp-admin/admin-ajax.php"

# Approved district plans for 2024-26 (Odisha publishes its district
# RoPs as "PIP"s headed "Approval 2024-26"). File stem -> NFHS-5 name;
# the listing also carries hospitals, medical colleges and city health
# societies, which are left out.
ODISHA_NAMES = {
    "Angul": "Anugul", "Balasore": "Baleshwar", "Baragarh": "Bargarh",
    "Bhadrak": "Bhadrak", "Bolangir": "Balangir", "Boudh": "Baudh",
    "Cuttack": "Cuttack", "Deogarh": "Debagarh", "Dhenkanal": "Dhenkanal",
    "Gajapati": "Gajapati", "Ganjam": "Ganjam",
    "Jagatsingpur": "Jagatsinghapur", "Jajapur": "Jajapur",
    "Jharsuguda": "Jharsuguda", "Kalahandi": "Kalahandi",
    "Kandhamal": "Kandhamal", "Kendrapada": "Kendrapara",
    "Keonjhar": "Kendujhar", "Khurda": "Khordha", "Koraput": "Koraput",
    "Malkangiri": "Malkangiri", "Mayurbhanj": "Mayurbhanj",
    "Nawrangpur": "Nabarangapur", "Nayagarh": "Nayagarh",
    "Nuapada": "Nuapada", "Puri": "Puri", "Rayagada": "Rayagada",
    "Sambalpur": "Sambalpur", "Sonepur": "Subarnapur",
    "Sundargarh": "Sundargarh",
}

# --- Uttarakhand -------------------------------------------------------

UTTARAKHAND_PAGE = "https://nhm.uk.gov.in/document-category/nhm-rop/"

# District name printed on the RoP cover -> NFHS-5 district name.
UTTARAKHAND_NAMES = {
    "Haridwar": "Hardwar",
    "Pauri Garhwal": "Garhwal",
}


def get(url, timeout=300, attempts=4):

    # State NHM servers (Haryana especially) stall mid-download now and
    # then; a retry almost always succeeds.
    for attempt in range(1, attempts + 1):

        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException:
            if attempt == attempts:
                raise
            print(f"    retry {attempt} for {url}")
            time.sleep(5 * attempt)


def links(page_url, pattern):
    """Absolute URLs of every href on a page matching pattern."""

    html = get(page_url, timeout=60).text

    found = re.findall(r'href="([^"]+)"', html)

    return [
        urljoin(page_url, href) for href in dict.fromkeys(found)
        if re.search(pattern, href)
    ]


def number(value):

    if value in (None, ""):
        return 0.0

    return float(value)


def row(state, district, fy, amounts, units, source):

    return {
        "state": state,
        "district": district,
        "fy": fy,
        "cotpa_104": round(amounts.get("104", 0.0), 2),
        "tofei_105": round(amounts.get("105", 0.0), 2),
        "cessation_106": round(amounts.get("106", 0.0), 2),
        "ntcp_activity_total": round(sum(amounts.values()), 2),
        "rop_units": units,
        "source_url": source,
    }


# --- Parsers -----------------------------------------------------------

def parse_haryana_pdf(pdf_bytes):
    """
    {code: lakh} from the "Summary of Approval" pool table, where the
    NCD.4 block reads (layout text):

        NCD.4  National Tobacco Control  104  Implementation of COTPA  6.45
                                         106  Tobacco Cessation        2.20
        NCD.5  ...
    """

    reader = PdfReader(io.BytesIO(pdf_bytes))

    for page in reader.pages[:40]:

        text = page.extract_text(extraction_mode="layout") or ""

        if "NCD.4" not in text:
            continue

        block = text[text.index("NCD.4"):]
        block = block[:block.index("NCD.5")]

        amounts = {}

        for line in block.splitlines():

            match = re.search(
                r"\b(10[4-6])\s+\S.*?\s(\d+\.\d+)\s*$", line
            )

            if match:
                amounts[match.group(1)] = float(match.group(2))

        if not amounts:
            raise ValueError("Haryana RoP: NCD.4 block has no amounts")

        return amounts

    raise ValueError("Haryana RoP: NCD.4 summary not found")


def haryana():

    urls = links(HARYANA_PAGE, r"DistrictROP2024-25/[A-Za-z]+_\d+\.pdf$")

    if len(urls) != 22:
        raise ValueError(f"Haryana: found {len(urls)} of 22 district RoPs")

    rows = []

    for url in urls:

        name = re.search(r"/([A-Za-z]+)_\d+\.pdf$", url).group(1)

        print(f"  Haryana: {name}")

        amounts = parse_haryana_pdf(get(url).content)

        rows.append(row(
            "Haryana", HARYANA_NAMES.get(name, name), "2024-25",
            amounts, name, url,
        ))

    return rows, []


def sikkim():

    url = next(iter(
        links(SIKKIM_PAGE, r"districtwise-rop_2024_25\.xlsx$")
    ), None)

    if url is None:
        raise ValueError("Sikkim: 2024-25 district RoP workbook not found")

    print("  Sikkim: workbook 2024-25")

    book = openpyxl.load_workbook(
        io.BytesIO(get(url).content), data_only=True
    )

    rows = list(book["NCD_Flexipool"].iter_rows(values_only=True))

    # Row 2 opens the "Financial (Lakh)" block; row 3 names its columns.
    start = list(rows[1]).index("Financial (Lakh)")
    names = [str(c).strip() if c else "" for c in rows[2][start:]]

    by_unit = {}
    state_level = 0.0

    for values in rows[3:]:

        code = str(values[2]).strip()

        if code not in CODES:
            continue

        financial = dict(zip(names, values[start:]))

        if number(financial.get("Urban")):
            raise ValueError(f"Sikkim {code}: unexpected urban allocation")

        parts = [number(financial[n]) for n in SIKKIM_NAMES]
        state = number(financial["State"])

        if abs(sum(parts) + state - number(values[6])) > 0.01:
            raise ValueError(f"Sikkim {code}: columns don't sum to total")

        for name in SIKKIM_NAMES:
            by_unit.setdefault(name, {})[code] = number(financial[name])

        state_level += state

    rows_out = []

    for district in dict.fromkeys(SIKKIM_NAMES.values()):

        units = [u for u, d in SIKKIM_NAMES.items() if d == district]

        amounts = {}

        for unit in units:
            for code, value in by_unit[unit].items():
                amounts[code] = amounts.get(code, 0.0) + value

        rows_out.append(row(
            "Sikkim", district, "2024-25", amounts,
            " + ".join(units), url,
        ))

    districts = sum(r["ntcp_activity_total"] for r in rows_out)

    split = [{
        "state": "Sikkim",
        "fy": "2024-25",
        "state_level_lakh": round(state_level, 2),
        "district_level_lakh": round(districts, 2),
        "source_url": url,
    }]

    return rows_out, split


def meghalaya():

    url = next(iter(
        links(MEGHALAYA_PAGE, r"DROP%20NHM%20Meghalaya%202024-26\.xlsx$|"
                              r"DROP NHM Meghalaya 2024-26\.xlsx$")
    ), None)

    if url is None:
        raise ValueError("Meghalaya: 2024-26 district RoP workbook not found")

    url = url.replace(" ", "%20")

    print("  Meghalaya: workbook 2024-26 (sheet 2024-25)")

    book = openpyxl.load_workbook(
        io.BytesIO(get(url).content), data_only=True
    )

    rows = list(book["2024-25"].iter_rows(values_only=True))

    header = next(r for r in rows if "SPMU" in r)
    column = {str(c).strip(): i for i, c in enumerate(header) if c}

    # FMR 104-106 rows inside the NTCP block.
    start = next(
        i for i, r in enumerate(rows)
        if r[1] and "National Tobacco Control" in str(r[1])
    )

    by_code = {}

    for values in rows[start + 1:]:

        code = str(values[0]).strip()

        if code not in CODES:
            if by_code:
                break
            continue

        by_code[code] = values

    if set(by_code) != set(CODES):
        raise ValueError(f"Meghalaya: found NTCP codes {sorted(by_code)}")

    for code, values in by_code.items():

        parts = sum(number(values[column[a]]) for a in MEGHALAYA_NAMES)

        if abs(parts + number(values[column["SPMU"]])
               - number(values[column["Total"]])) > 0.01:
            raise ValueError(f"Meghalaya {code}: columns don't sum")

    rows_out = [
        row(
            "Meghalaya", district, "2024-25",
            {c: number(v[column[abbr]]) for c, v in by_code.items()},
            abbr, url,
        )
        for abbr, district in MEGHALAYA_NAMES.items()
    ]

    split = [{
        "state": "Meghalaya",
        "fy": "2024-25",
        "state_level_lakh": round(sum(
            number(v[column["SPMU"]]) for v in by_code.values()
        ), 2),
        "district_level_lakh": round(
            sum(r["ntcp_activity_total"] for r in rows_out), 2
        ),
        "source_url": url,
    }]

    return rows_out, split


def parse_uttarakhand_pdf(pdf_bytes):
    """
    {code: lakh} from a district RoP. The pool summary near the front
    gives the NTCP main-RoP total, on the same line or the next:

        NCD.4  National Tobacco Control Programme   8.93  0  0  0  0.8  9.73
        NCD.4  National Tobacco Control
                                                   15.92

    and the programme's approval annexure lists each activity:

        NCD 4  National   104   Implementatio   3.38   Rs. 1.60 lakhs ...
                          105   Implementaito   3.40   Rs. 3.40 lakhs ...

    The activity lines must add up to the summary total. In 2026-27 a
    second 104 row (office expenses) belongs to programme management,
    outside the main-RoP total, so only the first row per code is kept.
    """

    reader = PdfReader(io.BytesIO(pdf_bytes))

    total = None
    amounts = {}

    for page in reader.pages:

        text = page.extract_text(extraction_mode="layout") or ""

        if "Tobacco" not in text:
            continue

        lines = text.splitlines()

        for i, line in enumerate(lines):

            if total is None and re.search(
                r"NCD\.\s?4\s+National Tobacco Control", line
            ):
                found = re.search(
                    r"(\d+\.\d+)", " ".join(lines[i:i + 3])
                )
                if found:
                    total = float(found.group(1))

            # Code, activity text, then the first decimal amount.
            match = re.match(
                r"^\s*(?:NCD\.?\s*4\b[^\d]*?)?(10[4-6])\s+"
                r"[A-Za-z].*?\s(\d+\.\d+)\s",
                line,
            )

            if match:
                amounts.setdefault(match.group(1), float(match.group(2)))

    if total is None:
        raise ValueError("Uttarakhand: NCD.4 summary total not found")

    if abs(sum(amounts.values()) - total) > 0.01:
        raise ValueError(
            f"Uttarakhand: NTCP lines {amounts} don't sum to the NCD.4 "
            f"total {total}"
        )

    return amounts


def uttarakhand():

    # The listing is paginated and lays titles out loosely, so every
    # PDF linked near a "RoP_24-25" title is fetched and identified by
    # its cover ("DISTRICT: PAURI GARHWAL / FY 2024-25") instead.
    candidates = []

    for page in range(1, 20):

        url = UTTARAKHAND_PAGE + (f"page/{page}/" if page > 1 else "")

        response = requests.get(url, headers=HEADERS, timeout=60)

        if response.status_code == 404:
            break

        response.raise_for_status()
        html = response.text

        for title in re.finditer(r"RoP_24-25", html):
            window = html[max(0, title.start() - 1500):title.end() + 1500]
            candidates += re.findall(r'href="([^"]+\.pdf)"', window)

    rows = {}

    for url in dict.fromkeys(candidates):

        pdf_bytes = get(url).content

        cover = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
        printed = re.search(
            r"DISTRICT:\s*([A-Z][A-Z .]+?)\s*\n\s*FY\s*(\d{4}-\d{2})",
            cover or "",
        )

        if not printed or printed.group(2) != "2024-25":
            continue

        name = printed.group(1).strip().title()
        district = UTTARAKHAND_NAMES.get(name, name)

        if district in rows:
            continue

        print(f"  Uttarakhand: {name}")

        rows[district] = row(
            "Uttarakhand", district, "2024-25",
            parse_uttarakhand_pdf(pdf_bytes), name, url,
        )

    if len(rows) != 13:
        raise ValueError(
            f"Uttarakhand: found {len(rows)} of 13 district RoPs for "
            f"2024-25: {sorted(rows)}"
        )

    return list(rows.values()), []


def parse_odisha_pdf(pdf_bytes):
    """
    {code: lakh} for FY 2024-25 from the "NCD-4_NTCP" approval table:

        Total NTCP                              28.49     33.83
        104  Implementation of COTPA - 2003     24.05     28.97
        105  Implementation of ToEFI Guideline
        106  Tobacco Cessation                   4.44      4.85

    The first amount is 2024-25; a code with no amount was not
    approved. The lines must add up to "Total NTCP".
    """

    reader = PdfReader(io.BytesIO(pdf_bytes))

    total = None
    amounts = {}

    for page in reader.pages:

        text = page.extract_text(extraction_mode="layout") or ""

        if total is None and "Total NTCP" not in text:
            continue

        for line in text.splitlines():

            if total is None:
                found = re.search(r"Total NTCP\s+(\d+\.\d+)", line)
                if found:
                    total = float(found.group(1))
                continue

            match = re.match(
                r"^\s*(10[4-6])\s+[A-Za-z].*?\s(\d+\.\d+)\s", line
            )

            if match:
                amounts.setdefault(match.group(1), float(match.group(2)))

        # 106 is the table's last line; anything further on (targets,
        # annexures) can reuse the same codes for other things.
        if "106" in amounts:
            break

    if total is None:
        raise ValueError("Odisha: Total NTCP row not found")

    # Lines are rounded to two decimals, so their sum can miss the
    # printed total by a paisa or two (Kendrapada: 14.81 vs 14.82).
    if abs(sum(amounts.values()) - total) > 0.02:
        raise ValueError(
            f"Odisha: NTCP lines {amounts} don't sum to Total NTCP {total}"
        )

    return amounts


def odisha():

    # The listing is filled in by a form post (category 193 = 2024-26).
    html = requests.post(
        ODISHA_AJAX,
        data={"categorypips": "193", "action": "myfiltercategorypips"},
        headers=HEADERS, timeout=120,
    ).text

    files = {}

    for url in re.findall(r'href="([^"]+?\.pdf)\s*"', html):

        stem = re.search(r"/([A-Za-z]+)[-_]PIP-2024-26\.pdf$", url)

        if stem and stem.group(1) in ODISHA_NAMES:
            files[stem.group(1)] = url.strip()

    if len(files) != 30:
        raise ValueError(f"Odisha: found {len(files)} of 30 district plans")

    rows = []

    for name, url in sorted(files.items()):

        print(f"  Odisha: {name}")

        rows.append(row(
            "Odisha", ODISHA_NAMES[name], "2024-25",
            parse_odisha_pdf(get(url).content), name, url,
        ))

    return rows, []


STATES = [haryana, sikkim, meghalaya, uttarakhand, odisha]


def write(path, rows):

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run():

    districts, splits = [], []

    for state in STATES:
        rows, split = state()
        districts += rows
        splits += split

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write(DISTRICT_PATH, districts)
    write(SPLIT_PATH, splits)

    print(
        f"✓ NTCP district RoPs: {len(districts)} districts -> "
        f"{DISTRICT_PATH.name}, {SPLIT_PATH.name}"
    )


if __name__ == "__main__":
    run()
