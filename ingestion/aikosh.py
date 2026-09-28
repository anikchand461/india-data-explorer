import json
import os

import requests


class AIKoshClient:
    """
    Client for AIKosh (aikosh.indiaai.gov.in). The published "User
    Manual for AIKosh" documents a *different* host/path (used for
    the model-upload flow) than datasets actually use -- the real
    dataset endpoints were confirmed by copying the exact curl
    command AIKosh's own "Download APIs for metadata and data" modal
    generates for a real dataset:

    - GET https://aikosha-api.indiaai.gov.in/akp/idp/api/v1/datasets/metadata
          ?datasetIdentifier=<id>
      headers: accept: */*, access-key: <API_KEY>
      (NOT Authorization: Bearer, NOT x-api-key -- both were tried
      and rejected before the real header name was found)

    Response shape: {"header": {...}, "data": {<actual fields>}}.
    No file-level detail is returned by this endpoint -- that
    requires the separate (not yet implemented) file-list-fetcher /
    download endpoints shown in the same modal
    (.../akp/idp/api/v2/dataset-public/...).

    A personal API key is created via My Profile -> Account Settings
    -> Generate API Key on the portal. A specific dataset's
    identifier is found via that dataset's page -> "Download APIs"
    modal.
    """

    METADATA_URL = (
        "https://aikosha-api.indiaai.gov.in"
        "/akp/idp/api/v1/datasets/metadata"
    )

    def __init__(self, api_key=None, timeout=30):

        self.api_key = api_key or os.getenv("AIKOSH_API_KEY")

        if not self.api_key:
            raise ValueError(
                "AIKOSH_API_KEY environment variable is not set."
            )

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update({
            "accept": "*/*",
            "access-key": self.api_key
        })

    def get_metadata(self, dataset_identifier):

        response = self.session.get(
            self.METADATA_URL,
            params={"datasetIdentifier": dataset_identifier},
            timeout=self.timeout
        )

        response.raise_for_status()

        body = response.json()

        if body.get("header", {}).get("error"):

            raise requests.RequestException(
                body["header"].get("msg", "AIKosh API error")
            )

        return body.get("data", {})


def fetch_all(dataset_ids):
    """
    Registers configured AIKosh datasets as catalogue entries.

    `dataset_ids` is the `aikosh.dataset_ids` list from
    config/sources.yaml -- each entry must be a real datasetIdentifier
    copied from a dataset's version-tab "API" option on the AIKosh
    portal. Unlike data.gov.in, AIKosh's metadata endpoint returns
    real dataset description fields, so those are used directly
    instead of being hand-entered in config.
    """

    if not dataset_ids:
        return []

    client = AIKoshClient()

    datasets = []

    for dataset_id in dataset_ids:

        try:
            meta = client.get_metadata(dataset_id)

        except requests.RequestException as exc:

            print(
                f"⚠ Skipping AIKosh dataset {dataset_id} "
                f"(unreachable): {exc}"
            )

            continue

        datasets.append({

            "name": meta.get("datasetName", dataset_id),

            "description": (
                meta.get("shortDescription")
                or meta.get("longDescription", "")
            ),

            "source": "AI Kosh",

            "source_url":
                "https://aikosh.indiaai.gov.in/web/datasets/"
                f"details/{dataset_id}.html",

            "organization": meta.get("sourceOrg", ""),

            "ministry": "",

            "department": meta.get("author", ""),

            "category": meta.get("sector", "Other"),

            "subcategory": "",

            "geographic_level":
                meta.get("geographicalCoverage", "India"),

            "granularity": meta.get("timeGranularity", ""),

            "start_date": "",

            "end_date": "",

            "format": meta.get("datasetType", ""),

            # False, not True: AIKosh's actual download mechanism is
            # a separate file-list/file-download API (not yet
            # implemented -- see class docstring), not the
            # queryable-records shape services/extraction.py expects
            # for data.gov.in. Setting this True would show a UI
            # button that calls the wrong client for this source.
            "api_available": False,

            "api_url":
                f"{AIKoshClient.METADATA_URL}"
                f"?datasetIdentifier={dataset_id}",

            # "Open" is AIKosh's public-visibility value (confirmed
            # from a live response), not "Public".
            "download_available":
                meta.get("visibility") == "Open",

            "download_url": "",

            "access_type":
                meta.get("visibility", "Restricted"),

            "catalogue_available": True,

            "keywords": ", ".join(meta.get("tags", [])),

            "external_id": dataset_id,

            "last_updated": "",

            "metadata_json": json.dumps(
                meta,
                ensure_ascii=False
            )
        })

    return datasets
