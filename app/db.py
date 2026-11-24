"""SQLite helpers for the local server registry."""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT NOT NULL UNIQUE,
    label TEXT,
    ssh_username TEXT,
    ssh_password TEXT,
    ssh_key_path TEXT,
    ssh_port INTEGER NOT NULL DEFAULT 22,
    created_at TEXT NOT NULL
);
"""

# Columns added after the initial demo schema
_EXTRA_COLUMNS = {
    "ssh_username": "TEXT",
    "ssh_password": "TEXT",
    "ssh_key_path": "TEXT",
    "ssh_port": "INTEGER NOT NULL DEFAULT 22",
}


def _db_path() -> str:
    return current_app.config["DATABASE_PATH"]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = _db_path()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(_exception=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(servers)").fetchall()
    }
    for name, col_type in _EXTRA_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE servers ADD COLUMN {name} {col_type}")


def init_db(app) -> None:
    """Create the database file and schema if missing; migrate new columns."""
    path = app.config["DATABASE_PATH"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()
