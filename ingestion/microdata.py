import json
import re
import urllib3
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# The Microdata server is currently presenting a certificate
# chain that Python requests cannot verify.
urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


class MicrodataClient:

    BASE_URL = "https://microdata.gov.in"

    CATALOG_URL = (
        "https://microdata.gov.in/NADA/index.php/catalog"
    )

    def __init__(self, timeout=30):

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

    def fetch_page(self, url):

        response = self.session.get(
            url,
            timeout=self.timeout,
            verify=False
        )

        response.raise_for_status()

        return response.text

    def get_soup(self, url):

        html = self.fetch_page(url)

        return BeautifulSoup(
            html,
            "html.parser"
        )

    def fetch_catalog(self, max_pages=10):

        datasets = []

        for page in range(1, max_pages + 1):

            if page == 1:
                url = self.CATALOG_URL
            else:
                url = (
                    f"{self.CATALOG_URL}"
                    f"?page={page}"
                )

            print(
                f"Fetching catalogue page {page}..."
            )

            try:

                soup = self.get_soup(url)

            except requests.RequestException as exc:

                print(
                    f"⚠ Failed to fetch page {page}:"
                )

                print(exc)

                break

            page_datasets = (
                self.parse_catalog_page(soup)
            )

            if not page_datasets:

                print(
                    "No datasets found on this page."
                )

                break

            datasets.extend(
                page_datasets
            )

            print(
                f"  Found "
                f"{len(page_datasets)} datasets"
            )

        return self.remove_duplicates(
            datasets
        )

    def parse_catalog_page(self, soup):

        datasets = []

        links = soup.find_all(
            "a",
            href=True
        )

        seen = set()

        for link in links:

            href = link.get(
                "href",
                ""
            ).strip()

            if "/catalog/" not in href:
                continue

            parts = (
                href
                .split("/catalog/")[-1]
                .strip("/")
                .split("/")
            )

            # Only actual dataset pages
            #
            # /catalog/284
            #
            # not:
            # /catalog/284/variable/V1
            # /catalog/284/get-microdata

            if len(parts) != 1:
                continue

            dataset_id = parts[0]

            if not dataset_id.isdigit():
                continue

            full_url = urljoin(
                self.BASE_URL,
                href
            )

            if full_url in seen:
                continue

            seen.add(full_url)

            title = link.get_text(
                " ",
                strip=True
            )

            if not title:
                continue

            parent = (
                link.find_parent("div")
                or link.find_parent("li")
                or link.parent
            )

            text = ""

            if parent:

                text = parent.get_text(
                    " ",
                    strip=True
                )

            dataset = (
                self.parse_dataset_text(
                    dataset_id,
                    title,
                    text,
                    full_url
                )
            )

            datasets.append(dataset)

        return datasets

    def parse_dataset_text(
        self,
        dataset_id,
        title,
        text,
        url
    ):

        collection = ""

        match = re.search(
            r"Collection:\s*(.+?)"
            r"(?:\s+ID:|\s+Last modified:|$)",
            text,
            re.IGNORECASE
        )

        if match:

            collection = (
                match.group(1)
                .strip()
            )

        reference_id = ""

        match = re.search(
            r"ID:\s*(\S+)",
            text
        )

        if match:

            reference_id = (
                match.group(1)
                .strip()
            )

        last_modified = ""

        match = re.search(
            r"Last modified:\s*(.+?)"
            r"(?:\s+Views:|$)",
            text,
            re.IGNORECASE
        )

        if match:

            last_modified = (
                match.group(1)
                .strip()
            )

        public_use = (
            "Public use data files"
            in text
        )

        if public_use:

            access_type = (
                "Public-use data"
            )

            download_available = True

            download_url = (
                f"{url}/get-microdata"
            )

        else:

            access_type = (
                "Catalogue / access varies"
            )

            download_available = False

            download_url = ""

        category = (
            self.infer_category(
                title,
                collection
            )
        )

        keywords = (
            self.extract_keywords(
                title,
                collection
            )
        )

        return {

            "name": title,

            "description": (
                f"{collection}. "
                "Dataset listed in the "
                "official MoSPI "
                "Microdata Portal."
            ),

            "source":
                "MoSPI Microdata Portal",

            "source_url": url,

            "organization":
                "Ministry of Statistics and "
                "Programme Implementation",

            "ministry":
                "MoSPI",

            "department":
                "National Statistical Office",

            "category": category,

            "subcategory":
                collection,

            "geographic_level":
                "India",

            "granularity":
                "Microdata / Survey",

            "start_date": "",

            "end_date": "",

            "format": "Microdata",

            "api_available": False,

            "api_url": "",

            "download_available":
                download_available,

            "download_url":
                download_url,

            "access_type":
                access_type,

            "catalogue_available": True,

            "keywords":
                ", ".join(keywords),

            "external_id":
                reference_id
                or dataset_id,

            "last_updated":
                last_modified,

            "metadata_json":
                json.dumps(
                    {
                        "nada_id":
                            dataset_id,

                        "reference_id":
                            reference_id,

                        "collection":
                            collection,

                        "public_use":
                            public_use,

                        "catalogue_url":
                            url
                    },
                    ensure_ascii=False
                )
        }

    @staticmethod
    def infer_category(
        title,
        collection
    ):

        text = (
            f"{title} {collection}"
        ).lower()

        categories = {

            "Health": [
                "health",
                "hospital",
                "medical",
                "morbidity",
                "immunization",
                "vaccination",
                "nutrition"
            ],

            "Employment": [
                "employment",
                "labour",
                "labor",
                "plfs",
                "worker"
            ],

            "Industry": [
                "industry",
                "industries",
                "asi",
                "manufacturing"
            ],

            "Agriculture": [
                "agriculture",
                "agricultural",
                "livestock",
                "land holding",
                "crop"
            ],

            "Education": [
                "education",
                "school",
                "literacy",
                "student"
            ],

            "Consumer Expenditure": [
                "consumer expenditure",
                "household consumption",
                "consumption expenditure",
                "durable goods"
            ],

            "Population": [
                "population",
                "demographic"
            ],

            "Enterprises": [
                "enterprise",
                "asuse",
                "unincorporated",
                "economic census"
            ]
        }

        for category, words in categories.items():

            for word in words:

                if word in text:

                    return category

        return "Other"

    @staticmethod
    def extract_keywords(
        title,
        collection
    ):

        words = []

        for value in [
            title,
            collection
        ]:

            if not value:
                continue

            words.extend(
                re.findall(
                    r"[A-Za-z]{3,}",
                    value.lower()
                )
            )

        return sorted(
            set(words)
        )

    @staticmethod
    def remove_duplicates(
        datasets
    ):

        unique = {}

        for dataset in datasets:

            key = (
                dataset.get(
                    "external_id"
                )
                or dataset.get(
                    "source_url"
                )
            )

            if key:

                unique[key] = dataset

        return list(
            unique.values()
        )