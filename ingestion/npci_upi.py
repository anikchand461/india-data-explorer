import requests


class NPCIClient:
    """
    Client for NPCI's public UPI ecosystem statistics page
    (aggregate monthly volume/value only -- NPCI/RBI do not publish
    transaction- or individual-level UPI data anywhere).

    Verified live during this integration: the page returns HTTP 403
    to a plain scripted request (bot/WAF protection). This project
    does not attempt to bypass that protection -- no fingerprint
    spoofing beyond the same browser User-Agent already used for
    microdata.gov.in. See config/sources.yaml -> npci_upi.
    """

    STATS_URL = (
        "https://www.npci.org.in/product/ecosystem-statistics/upi"
    )

    def __init__(self, timeout=15):

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            )
        })

    def fetch_page(self):

        response = self.session.get(
            self.STATS_URL,
            timeout=self.timeout
        )

        response.raise_for_status()

        return response.text


def fetch_all():
    """
    Registers the NPCI UPI statistics page as a single catalogue
    entry. Returns [] with a printed reason if the page is blocked,
    so the multi-source ingestion run can continue.
    """

    client = NPCIClient()

    try:

        client.fetch_page()

    except requests.RequestException as exc:

        print(
            "⚠ NPCI UPI statistics page is currently blocked "
            f"to scripted access ({exc}). Skipping -- see "
            "config/sources.yaml npci_upi.unavailable_reason."
        )

        return []

    return [{

        "name": "NPCI UPI Ecosystem Statistics",

        "description": (
            "Aggregate monthly UPI transaction volume and value "
            "figures published by NPCI. Aggregate-only -- no "
            "transaction- or individual-level microdata is "
            "published for UPI by any Indian government body."
        ),

        "source": "National Payments Corporation of India",

        "source_url": NPCIClient.STATS_URL,

        "organization":
            "National Payments Corporation of India",

        "ministry": "",

        "department": "",

        "category": "Other",

        "subcategory": "Digital Payments",

        "geographic_level": "India",

        "granularity": "National / Monthly",

        "start_date": "",

        "end_date": "",

        "format": "HTML / Dashboard",

        "api_available": False,

        "api_url": "",

        "download_available": False,

        "download_url": "",

        "access_type": "Public page (aggregate only)",

        "catalogue_available": True,

        "keywords": "upi, payments, npci, transactions",

        "external_id": "npci-upi-ecosystem-statistics",

        "last_updated": "",

        "metadata_json": "{}"

    }]
