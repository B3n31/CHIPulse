import sqlite3
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")


def get_conn() -> sqlite3.Connection:
    """Open a new SQLite connection with Row objects."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def run_sql(sql: str, params=()):
    """Run a SELECT query and return all rows as a list of sqlite3.Row."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return rows
    finally:
        conn.close()


