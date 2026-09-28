import os

import requests


class CoWINClient:
    """
    Client for the public CoWIN / Universal Immunization Program API
    served via apisetu.gov.in (documented base:
    https://cdn-api.co-vin.in/api/v2). Historically key-less for GET
    endpoints; COWIN_API_KEY is sent as a header only if set, in case
    a specific deployment requires a subscription key.

    Verified live during this integration: the API currently returns
    HTTP 503 (see config/sources.yaml -> cowin.unavailable_reason).
    This client is correct against the documented API shape and will
    work again with no code change if/when the service is restored.
    """

    BASE_URL = "https://cdn-api.co-vin.in/api/v2"

    def __init__(self, timeout=15):

        self.timeout = timeout

        self.session = requests.Session()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            ),
            "Accept-Language": "en_US"
        }

        api_key = os.getenv("COWIN_API_KEY")

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self.session.headers.update(headers)

    def get_states(self):

        response = self.session.get(
            f"{self.BASE_URL}/admin/location/states",
            timeout=self.timeout
        )

        response.raise_for_status()

        return response.json().get("states", [])


def fetch_all():
    """
    Registers the CoWIN public API as a single catalogue entry
    describing its availability, rather than pretending it has data
    right now. Returns [] with a printed reason when the API is
    unreachable, so the multi-source ingestion run can continue.
    """

    client = CoWINClient()

    try:

        client.get_states()

    except requests.RequestException as exc:

        print(
            "⚠ CoWIN public API is currently unreachable "
            f"({exc}). Skipping -- see config/sources.yaml "
            "cowin.unavailable_reason."
        )

        return []

    return [{

        "name": "CoWIN Vaccination Session Data (Public API)",

        "description": (
            "Public API for vaccination session/center "
            "availability, originally built for COVID-19 "
            "vaccination and repurposed for India's Universal "
            "Immunization Program."
        ),

        "source": "CoWIN / Universal Immunization Program",

        "source_url": "https://apisetu.gov.in/public/marketplace",

        "organization":
            "Ministry of Health and Family Welfare",

        "ministry": "MoHFW",

        "department": "",

        "category": "Health",

        "subcategory": "Vaccination",

        "geographic_level": "India",

        "granularity": "Session / Center",

        "start_date": "",

        "end_date": "",

        "format": "API",

        "api_available": False,

        "api_url": f"{CoWINClient.BASE_URL}",

        "download_available": False,

        "download_url": "",

        "access_type": "Public API (apisetu.gov.in)",

        "catalogue_available": True,

        "keywords": "vaccination, cowin, immunization, health",

        "external_id": "cowin-public-v2",

        "last_updated": "",

        "metadata_json": "{}"

    }]
