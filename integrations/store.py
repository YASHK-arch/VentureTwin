"""
SQLite-backed store for integration connection states and sync history.

Uses the same database file as the rest of the app: venturetwin_auth.db
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "venturetwin_auth.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_integration_db() -> None:
    """Create integration tables if they don't already exist."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_connections (
                connector_id        TEXT PRIMARY KEY,
                company_id          TEXT NOT NULL DEFAULT 'default',
                status              TEXT NOT NULL DEFAULT 'not_connected',
                credentials_configured INTEGER NOT NULL DEFAULT 0,
                last_sync           TEXT,
                error               TEXT,
                updated_at          TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_sync_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                connector_id    TEXT NOT NULL,
                sync_start      TEXT NOT NULL,
                sync_end        TEXT,
                records_fetched INTEGER NOT NULL DEFAULT 0,
                records_created INTEGER NOT NULL DEFAULT 0,
                status          TEXT NOT NULL,
                error_message   TEXT
            )
        """)
        conn.commit()


def save_connection_state(
    connector_id: str,
    status: str,
    credentials_configured: bool,
    last_sync: Optional[str] = None,
    error: Optional[str] = None,
    company_id: str = "default",
) -> None:
    init_integration_db()
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO integration_connections
                (connector_id, company_id, status, credentials_configured, last_sync, error, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(connector_id) DO UPDATE SET
                company_id              = excluded.company_id,
                status                  = excluded.status,
                credentials_configured  = excluded.credentials_configured,
                last_sync               = excluded.last_sync,
                error                   = excluded.error,
                updated_at              = excluded.updated_at
        """, (connector_id, company_id, status, int(credentials_configured), last_sync, error, now))
        conn.commit()


def get_connection_state(connector_id: str) -> Optional[Dict[str, Any]]:
    init_integration_db()
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM integration_connections WHERE connector_id = ?",
            (connector_id,)
        ).fetchone()
        if row:
            return dict(row)
    return None


def get_all_connection_states() -> List[Dict[str, Any]]:
    init_integration_db()
    with _get_connection() as conn:
        rows = conn.execute("SELECT * FROM integration_connections ORDER BY connector_id").fetchall()
        return [dict(r) for r in rows]


def save_sync_record(
    connector_id: str,
    sync_start: str,
    sync_end: Optional[str],
    records_fetched: int,
    records_created: int,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    init_integration_db()
    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO integration_sync_history
                (connector_id, sync_start, sync_end, records_fetched, records_created, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (connector_id, sync_start, sync_end, records_fetched, records_created, status, error_message))
        conn.commit()


def get_sync_history(connector_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    init_integration_db()
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM integration_sync_history WHERE connector_id = ? ORDER BY id DESC LIMIT ?",
            (connector_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
