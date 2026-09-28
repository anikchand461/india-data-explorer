from database.database import get_connection


def get_dataset(dataset_id):

    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM datasets
        WHERE id = ?
        """,
        (dataset_id,)
    ).fetchone()

    connection.close()

    return row


def get_categories():

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT DISTINCT category
        FROM datasets
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
        """
    ).fetchall()

    connection.close()

    return [
        row["category"]
        for row in rows
    ]


def get_sources():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT source
        FROM datasets
        WHERE source IS NOT NULL
        ORDER BY source
        """
    )

    sources = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()

    return sources


def get_statistics():

    connection = get_connection()

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM datasets
        """
    ).fetchone()[0]

    sources = connection.execute(
        """
        SELECT COUNT(DISTINCT source)
        FROM datasets
        """
    ).fetchone()[0]

    categories = connection.execute(
        """
        SELECT COUNT(DISTINCT category)
        FROM datasets
        WHERE category IS NOT NULL
        """
    ).fetchone()[0]

    api_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM datasets
        WHERE api_available = 1
        """
    ).fetchone()[0]

    connection.close()

    return {
        "total": total,
        "sources": sources,
        "categories": categories,
        "api_count": api_count
    }