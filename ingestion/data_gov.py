import json
import os

import requests


class DataGovClient:

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("DATA_GOV_API_KEY")

        if not self.api_key:
            raise ValueError(
                "DATA_GOV_API_KEY environment variable is not set."
            )

        self.base_url = "https://api.data.gov.in/resource"

    def fetch_resource(
        self,
        resource_id,
        limit=100,
        offset=0,
        filters=None
    ):
        url = f"{self.base_url}/{resource_id}"

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
            "offset": offset
        }

        if filters:
            params.update(filters)

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def get_records(
        self,
        resource_id,
        limit=100,
        offset=0,
        filters=None
    ):
        data = self.fetch_resource(
            resource_id=resource_id,
            limit=limit,
            offset=offset,
            filters=filters
        )

        return data.get("records", [])

    def get_total_records(self, resource_id):
        data = self.fetch_resource(
            resource_id=resource_id,
            limit=1
        )

        return data.get("total", 0)


def fetch_all(resources):
    """
    Registers configured data.gov.in resources as catalogue entries.

    `resources` is the `data_gov.resources` list from
    config/sources.yaml -- each entry must carry a real resource_id
    copied from a dataset's "API" tab on data.gov.in. This does not
    pull the resource's row-level data into the catalogue (that stays
    metadata-only, consistent with every other source); it registers
    the dataset with api_available=True so the existing "Extract Data"
    button in ui/dataset.py can call extract_data_gov() against it.
    """

    if not resources:
        return []

    client = DataGovClient()

    datasets = []

    for entry in resources:

        resource_id = entry.get("resource_id")

        if not resource_id:
            continue

        try:
            client.get_total_records(resource_id)

        except requests.RequestException as exc:

            print(
                f"⚠ Skipping resource {resource_id} "
                f"(unreachable): {exc}"
            )

            continue

        datasets.append({

            "name": entry.get("name", resource_id),

            "description": entry.get("description", ""),

            "source": "Open Government Data Platform India",

            "source_url":
                f"https://www.data.gov.in/resource/{resource_id}",

            "organization": entry.get("organization", ""),

            "ministry": entry.get("ministry", ""),

            "department": entry.get("department", ""),

            "category": entry.get("category", "Other"),

            "subcategory": entry.get("subcategory", ""),

            "geographic_level": entry.get("geographic_level", "India"),

            "granularity": entry.get("granularity", ""),

            "start_date": entry.get("start_date", ""),

            "end_date": entry.get("end_date", ""),

            "format": "Tabular (API)",

            "api_available": True,

            "api_url":
                f"{client.base_url}/{resource_id}",

            "download_available": False,

            "download_url": "",

            "access_type": "Open API (data.gov.in)",

            "catalogue_available": True,

            "keywords": entry.get("keywords", ""),

            "external_id": resource_id,

            "last_updated": "",

            "metadata_json": json.dumps(
                {"resource_id": resource_id},
                ensure_ascii=False
            )
        })

    return datasets