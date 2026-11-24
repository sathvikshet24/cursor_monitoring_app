"""CRUD for monitored servers (local SQLite registry only)."""

import sqlite3
from datetime import datetime, timezone

from app.db import get_db

_SERVER_COLUMNS = (
    "id, hostname, label, ssh_username, ssh_password, ssh_key_path, ssh_port, created_at"
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()  # noqa: UP017


def list_servers() -> list[dict]:
    rows = get_db().execute(
        f"SELECT {_SERVER_COLUMNS} FROM servers ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_server(server_id: int) -> dict | None:
    row = get_db().execute(
        f"SELECT {_SERVER_COLUMNS} FROM servers WHERE id = ?",
        (server_id,),
    ).fetchone()
    return dict(row) if row else None


def add_server(
    hostname: str,
    label: str | None = None,
    *,
    ssh_username: str,
    ssh_password: str | None = None,
    ssh_key_path: str | None = None,
    ssh_port: int = 22,
) -> tuple[bool, str | None]:
    """Insert a server with per-host SSH credentials. Returns (success, error_message)."""
    hostname = hostname.strip()
    try:
        get_db().execute(
            """
            INSERT INTO servers (
                hostname, label, ssh_username, ssh_password, ssh_key_path, ssh_port, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hostname,
                label,
                ssh_username,
                ssh_password,
                ssh_key_path,
                ssh_port,
                _utc_now_iso(),
            ),
        )
        get_db().commit()
        return True, None
    except sqlite3.IntegrityError:
        get_db().rollback()
        return False, "That hostname or IP is already registered."


def remove_server(server_id: int) -> bool:
    """Remove a server from the local registry only. Returns True if a row was deleted."""
    cursor = get_db().execute("DELETE FROM servers WHERE id = ?", (server_id,))
    get_db().commit()
    return cursor.rowcount > 0
