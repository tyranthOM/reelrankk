"""
ReelRank — SQLite connection helper.

Pure stdlib (`sqlite3`) — no dependencies to install. This is the one
module every other script (seed_data.py, verify.py, and later the FastAPI
app) imports to get a connection.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "reelrank.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection with sane defaults: row access by column name,
    and foreign keys enforced (SQLite has them off by default per-connection)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH, reset: bool = False) -> sqlite3.Connection:
    """Create the database file and apply schema.sql. If reset=True, deletes
    any existing .db file first (used by seed_data.py for a clean reseed)."""
    if reset and db_path.exists():
        db_path.unlink()

    conn = get_connection(db_path)
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    return conn
