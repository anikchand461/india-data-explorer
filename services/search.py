from database.database import get_connection


def search_datasets(
    query="",
    source=None,
    category=None,
    granularity=None,
    access_type=None
):

    connection = get_connection()

    sql = """
        SELECT *
        FROM datasets
        WHERE 1 = 1
    """

    parameters = []

    if query:

        sql += """
            AND (
                name LIKE ?
                OR description LIKE ?
                OR keywords LIKE ?
                OR organization LIKE ?
                OR category LIKE ?
            )
        """

        value = f"%{query}%"

        parameters.extend([
            value,
            value,
            value,
            value,
            value
        ])

    if source:

        sql += """
            AND source = ?
        """

        parameters.append(
            source
        )

    if category:

        sql += """
            AND category = ?
        """

        parameters.append(
            category
        )

    if granularity:

        sql += """
            AND granularity = ?
        """

        parameters.append(
            granularity
        )

    if access_type:

        sql += """
            AND access_type = ?
        """

        parameters.append(
            access_type
        )

    sql += """
        ORDER BY name ASC
    """

    rows = connection.execute(
        sql,
        parameters
    ).fetchall()

    connection.close()

    return rows