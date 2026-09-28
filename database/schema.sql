CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,
    description TEXT,

    source TEXT NOT NULL,
    source_url TEXT,

    organization TEXT,
    ministry TEXT,
    department TEXT,

    category TEXT,
    subcategory TEXT,

    geographic_level TEXT,
    granularity TEXT,

    start_date TEXT,
    end_date TEXT,

    format TEXT,

    api_available INTEGER DEFAULT 0,
    api_url TEXT,

    download_available INTEGER DEFAULT 0,
    download_url TEXT,

    access_type TEXT,

    catalogue_available INTEGER DEFAULT 1,

    keywords TEXT,

    external_id TEXT,

    last_updated TEXT,

    metadata_json TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_datasets_name
ON datasets(name);

CREATE INDEX IF NOT EXISTS idx_datasets_source
ON datasets(source);

CREATE INDEX IF NOT EXISTS idx_datasets_category
ON datasets(category);

CREATE INDEX IF NOT EXISTS idx_datasets_keywords
ON datasets(keywords);