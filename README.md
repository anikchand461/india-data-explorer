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

Run the app:

```bash
streamlit run app.py
```

