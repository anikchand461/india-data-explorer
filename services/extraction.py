import pandas as pd

from ingestion.data_gov import DataGovClient


def extract_data_gov(
    resource_id,
    limit=100,
    offset=0,
    filters=None
):

    client = DataGovClient()

    records = client.get_records(
        resource_id=resource_id,
        limit=limit,
        offset=offset,
        filters=filters
    )

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)