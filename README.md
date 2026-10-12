# 🇮🇳 India Data Explorer

A searchable catalogue and extraction interface for
Indian government datasets.

## Goal

Create a unified discovery layer for Indian public
datasets across multiple government data platforms.

## Initial Sources

- data.gov.in
- Microdata.gov.in
- NDAP
- AI Kosh

## Features

- Dataset catalogue
- Dataset search
- Category filtering
- Source filtering
- Granularity filtering
- Dataset metadata
- API availability
- Data extraction
- CSV export
- Government source links

## Oral Cancer & Tobacco page

A dashboard on oral cavity cancer and the tobacco use behind it, with
every number rebuilt from public sources. Sections are chosen with the
buttons at the top of the page:

| Section | What it shows |
|---|---|
| Burden & key findings | National oral cancer cases (NCRP) and headline findings |
| States | State tobacco use, product mix and modelled risk |
| Districts | NFHS-5 indicators for all 707 districts |
| Risk matrix | District cross-matrix: estimated smokeless use, risk tier × oral cancer screening (110 priority districts: high risk, below-national screening), modelled oral cancer cases, budgets, and a snus / nicotine-pouch switching scenario |
| Tobacco control budget | Sanctioned NTCP activity budget per district (FY 2024-25) from NHM district RoPs: 145 districts in 7 states |
| Trend 2019→2024 | NFHS-5 to NFHS-6 change in tobacco use |
| Who uses tobacco | Use by age, wealth, schooling, caste/tribe and religion, plus product mix |
| Projection model | Attributable-fraction projection of cases avoided |
| Sources & caveats | Every source, and data-quality issues found |

**Tobacco control budget coverage.** Haryana, Odisha, Rajasthan,
Sikkim, Meghalaya, Uttarakhand and Assam. These are sanctioned
amounts, not spending, and cover NTCP activity lines only (FMR
104-106). Rajasthan's districts created in 2023 are folded into the
NFHS-5 district that held most of their 2011 population, and each
affected district carries a `mapping_note`. Dholpur's RoP was
published without its amounts. Andhra Pradesh is not yet included:
its only district RoPs are FY 2026-27 scans for 26 post-2022
districts.

**Risk matrix: modelled parts.** Oral cancer cases per district are
modelled: each state's projected cases (NCRP) are shared out by
district population (WorldPop 2020) × risk. They are to be checked
against cancer registry data. The switching upside is a scenario with
adjustable assumptions: the share of smokeless users who switch, and
the product's risk, which defaults to 1.0 from Swedish snus studies.
District smokeless use is estimated from total tobacco use × the
state's GATS-2 smokeless share, until the NFHS-5 microdata (requested
from the DHS Program) arrives.

## Architecture

Government Data Sources
        ↓
Ingestion Layer
        ↓
SQLite
        ↓
Service Layer
        ↓
Streamlit
        ↓
User

## Tech Stack

- Python
- Streamlit
- SQLite
- Pandas
- Requests
- PyYAML

## Data Source Status

| Source | Status | Notes |
|---|---|---|
| MoSPI Microdata Portal | **Live** | Public catalogue scrape, ~150 datasets, no key needed. |
| Open Government Data Platform India (data.gov.in) | **Live** (empty until configured) | Self-service API key; add real `resource_id` entries under `data_gov.resources` in `config/sources.yaml`. |
| NDAP | Blocked | Client-side-rendered SPA with no discoverable public API — see `config/sources.yaml`. |
| AI Kosh | Blocked | Needs an API key and endpoint docs not yet obtained — see `config/sources.yaml`. |
| CoWIN (vaccination) | Unavailable | Client is implemented against the documented public API, which currently returns HTTP 503. |
| NPCI UPI statistics | Unavailable | Page blocks scripted access (HTTP 403); only ever publishes aggregate monthly stats, never microdata, in any case. |
| Land Records | Excluded (by design) | No unified API; bulk-collecting personal property records raises privacy/legal concerns. |
| ECI booth-level election data | Excluded (by design) | Only published as scanned per-constituency PDFs, not a bulk API. |
| NFHS full microdata | Excluded (by design) | Distributed by the DHS Program behind a manual research-approval process, not self-service. |

## Setup

Create virtual environment:

```bash
uv venv
source .venv/bin/activate
```

Install dependencies:

```bash
uv pip install -r requirements.txt
```

Configure API keys:

```bash
cp .env.example .env
# then edit .env and fill in DATA_GOV_API_KEY (and any others you obtain)
```

Run ingestion (populates the local SQLite catalogue from every enabled
source in `config/sources.yaml`):

```bash
python3 -m scripts.ingest
```

Rebuild the Oral Cancer & Tobacco page's data (downloads and parses
the NFHS-5 report, NFHS-6 fact sheets, NFHS-5 district fact sheets,
GATS-2, NCRP 2020, the NFHS-5 survey boundaries and the NHM district
RoPs for the budget section; see `data/reference/SOURCES.md`). The
RoP step can take several minutes, because some state NHM servers are
slow:

```bash
python3 -m scripts.build_oral_cancer_data
```

Run the app:

```bash
streamlit run app.py
```

