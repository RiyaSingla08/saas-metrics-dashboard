"""
Initializes the DuckDB database using sql/schema.sql.

Run this once (or any time you want to reset the database):
    python scripts/init_db.py
"""

import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
DB_PATH = PROJECT_ROOT / "data" / "saas_metrics.duckdb"


def init_db():
    schema_sql = SCHEMA_PATH.read_text()
    con = duckdb.connect(str(DB_PATH))
    con.execute(schema_sql)

    tables = con.execute("SHOW TABLES").fetchall()
    print(f"Database created at: {DB_PATH}")
    print("Tables:")
    for (table_name,) in tables:
        print(f"  - {table_name}")

    con.close()


if __name__ == "__main__":
    init_db()