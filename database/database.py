import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "india_data.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def get_connection():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_connection()

    with open(
        SCHEMA_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        schema = file.read()

    connection.executescript(schema)

    connection.commit()
    connection.close()