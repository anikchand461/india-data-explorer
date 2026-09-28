from dataclasses import dataclass
from typing import Optional


@dataclass
class Dataset:
    name: str
    description: Optional[str] = None

    source: Optional[str] = None
    source_url: Optional[str] = None

    organization: Optional[str] = None
    ministry: Optional[str] = None
    department: Optional[str] = None

    category: Optional[str] = None
    subcategory: Optional[str] = None

    geographic_level: Optional[str] = None
    granularity: Optional[str] = None

    start_date: Optional[str] = None
    end_date: Optional[str] = None

    format: Optional[str] = None

    api_available: bool = False
    api_url: Optional[str] = None

    download_available: bool = False
    download_url: Optional[str] = None

    access_type: Optional[str] = None

    keywords: Optional[str] = None

    external_id: Optional[str] = None

    last_updated: Optional[str] = None

    metadata_json: Optional[str] = None