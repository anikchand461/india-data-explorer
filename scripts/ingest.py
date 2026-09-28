from pathlib import Path

import yaml
from dotenv import load_dotenv

from database.database import initialize_database
from ingestion.runner import save_dataset
from ingestion.microdata import MicrodataClient
from ingestion import (
    data_gov,
    ndap,
    aikosh,
    cowin,
    npci_upi,
    land_records,
    eci_election,
    nfhs_microdata,
)


load_dotenv()

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "config" / "sources.yaml"
)


def load_sources_config():

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config.get("sources", {})


def fetch_microdata(config):
    return MicrodataClient().fetch_catalog(max_pages=10)


FETCHERS = {
    "microdata": fetch_microdata,
    "data_gov": lambda cfg: data_gov.fetch_all(
        cfg.get("resources", [])
    ),
    "ndap": lambda cfg: ndap.fetch_all(),
    "aikosh": lambda cfg: aikosh.fetch_all(
        cfg.get("dataset_ids", [])
    ),
    "cowin": lambda cfg: cowin.fetch_all(),
    "npci_upi": lambda cfg: npci_upi.fetch_all(),
    "land_records": lambda cfg: land_records.fetch_all(),
    "eci_election": lambda cfg: eci_election.fetch_all(),
    "nfhs_microdata": lambda cfg: nfhs_microdata.fetch_all(),
}


def main():

    print("=" * 60)
    print("India Data Explorer - Data Ingestion")
    print("=" * 60)

    print("\nInitializing database...")
    initialize_database()
    print("✓ Database ready")

    sources = load_sources_config()

    summary = []

    for key, fetcher in FETCHERS.items():

        source_config = sources.get(key, {})

        name = source_config.get("name", key)

        if not source_config.get("enabled", False):

            reason = (
                source_config.get("blocked_reason")
                or source_config.get("excluded_reason")
            )

            print(f"\n— {name}: disabled, skipping")

            if reason:
                print(f"  reason: {reason.strip()}")

            continue

        print(f"\nFetching from {name}...")

        try:
            datasets = fetcher(source_config)

        except Exception as exc:

            print(f"⚠ {name} failed: {exc}")

            summary.append((name, 0, "error"))

            continue

        imported = 0

        for dataset in datasets:

            try:
                save_dataset(dataset)
                imported += 1

            except Exception as exc:

                print(
                    f"⚠ Failed to save "
                    f"{dataset.get('name', 'Unknown')}: {exc}"
                )

        print(
            f"✓ {imported} dataset(s) imported/updated "
            f"from {name}"
        )

        summary.append((name, imported, "ok"))

    print("\n" + "=" * 60)
    print("Ingestion summary:")

    for name, count, status in summary:

        marker = "✓" if status == "ok" else "⚠"

        print(f"  {marker} {name}: {count} dataset(s)")

    print("=" * 60)


if __name__ == "__main__":
    main()
