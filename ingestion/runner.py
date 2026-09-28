from database.database import get_connection


def save_dataset(dataset):

    conn = get_connection()

    cursor = conn.cursor()

    query = """
    INSERT INTO datasets (
        name,
        description,
        source,
        source_url,
        organization,
        ministry,
        department,
        category,
        subcategory,
        geographic_level,
        granularity,
        start_date,
        end_date,
        format,
        api_available,
        api_url,
        download_available,
        download_url,
        access_type,
        catalogue_available,
        keywords,
        external_id,
        last_updated,
        metadata_json
    )
    VALUES (
        :name,
        :description,
        :source,
        :source_url,
        :organization,
        :ministry,
        :department,
        :category,
        :subcategory,
        :geographic_level,
        :granularity,
        :start_date,
        :end_date,
        :format,
        :api_available,
        :api_url,
        :download_available,
        :download_url,
        :access_type,
        :catalogue_available,
        :keywords,
        :external_id,
        :last_updated,
        :metadata_json
    )
    ON CONFLICT(source, external_id)
    DO UPDATE SET
        name = excluded.name,
        description = excluded.description,
        source_url = excluded.source_url,
        organization = excluded.organization,
        ministry = excluded.ministry,
        department = excluded.department,
        category = excluded.category,
        subcategory = excluded.subcategory,
        geographic_level = excluded.geographic_level,
        granularity = excluded.granularity,
        start_date = excluded.start_date,
        end_date = excluded.end_date,
        format = excluded.format,
        api_available = excluded.api_available,
        api_url = excluded.api_url,
        download_available = excluded.download_available,
        download_url = excluded.download_url,
        access_type = excluded.access_type,
        catalogue_available = excluded.catalogue_available,
        keywords = excluded.keywords,
        last_updated = excluded.last_updated,
        metadata_json = excluded.metadata_json,
        updated_at = CURRENT_TIMESTAMP
    """

    cursor.execute(query, dataset)

    conn.commit()

    conn.close()