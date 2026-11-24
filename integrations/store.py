"""
Persistent storage for integration connections and sync cycles.
Stores Nango connection metadata, provider configuration keys, and sync logs in SQLite (venturetwin_auth.db).
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "venturetwin_auth.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_integration_db() -> None:
    """Create integration connection and sync history tables."""
    with _get_connection() as conn:
        # Schema migration check: if table exists with legacy schema without integration_id, recreate
        existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(integration_connections)").fetchall()]
        if existing_cols and "integration_id" not in existing_cols:
            conn.execute("DROP TABLE IF EXISTS integration_connections")
            conn.execute("DROP TABLE IF EXISTS integration_syncs")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_connections (
                id                      TEXT PRIMARY KEY,
                company_id              TEXT NOT NULL DEFAULT 'default',
                integration_id          TEXT NOT NULL,
                provider_name           TEXT NOT NULL,
                nango_connection_id     TEXT,
                provider_config_key     TEXT NOT NULL,
                authentication_type     TEXT NOT NULL DEFAULT 'oauth',
                environment             TEXT NOT NULL DEFAULT 'test',
                connection_status       TEXT NOT NULL DEFAULT 'not_connected',
                connected_at            TEXT,
                last_synced_at          TEXT,
                metadata_json           TEXT NOT NULL DEFAULT '{}',
                UNIQUE(company_id, integration_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_syncs (
                id                  TEXT PRIMARY KEY,
                company_id          TEXT NOT NULL DEFAULT 'default',
                integration_id      TEXT NOT NULL,
                sync_status         TEXT NOT NULL,
                started_at          TEXT NOT NULL,
                completed_at        TEXT,
                records_fetched     INTEGER NOT NULL DEFAULT 0,
                records_created     INTEGER NOT NULL DEFAULT 0,
                records_updated     INTEGER NOT NULL DEFAULT 0,
                error_message       TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ic_company ON integration_connections(company_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ic_integration ON integration_connections(integration_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_is_integration ON integration_syncs(integration_id)")
        conn.commit()


def save_connection_state(
    connector_id: str,
    status: str,
    credentials_configured: bool = False,
    last_sync: Optional[str] = None,
    error: Optional[str] = None,
    company_id: str = "default",
    provider_name: Optional[str] = None,
    nango_connection_id: Optional[str] = None,
    provider_config_key: Optional[str] = None,
    authentication_type: str = "oauth",
    environment: str = "test",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Upsert an integration connection record."""
    init_integration_db()
    now = datetime.now(timezone.utc).isoformat()
    record_id = f"conn_{company_id}_{connector_id}"
    meta_json = json.dumps(metadata or {})
    p_name = provider_name or connector_id.capitalize()
    p_key = provider_config_key or connector_id

    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO integration_connections (
                id, company_id, integration_id, provider_name,
                nango_connection_id, provider_config_key, authentication_type,
                environment, connection_status, connected_at, last_synced_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id, integration_id) DO UPDATE SET
                provider_name = excluded.provider_name,
                nango_connection_id = COALESCE(excluded.nango_connection_id, integration_connections.nango_connection_id),
                provider_config_key = excluded.provider_config_key,
                authentication_type = excluded.authentication_type,
                environment = excluded.environment,
                connection_status = excluded.connection_status,
                connected_at = CASE WHEN excluded.connection_status IN ('connected', 'sandbox_connected') THEN excluded.connected_at ELSE integration_connections.connected_at END,
                last_synced_at = COALESCE(excluded.last_synced_at, integration_connections.last_synced_at),
                metadata_json = excluded.metadata_json
        """, (
            record_id, company_id, connector_id, p_name,
            nango_connection_id, p_key, authentication_type,
            environment, status, now if status in ("connected", "sandbox_connected") else None,
            last_sync, meta_json
        ))
        conn.commit()

    return get_connection_state(connector_id, company_id) or {}


def get_connection_state(connector_id: str, company_id: str = "default") -> Optional[Dict[str, Any]]:
    """Retrieve connection record for a specific connector and company."""
    init_integration_db()
    with _get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM integration_connections
            WHERE company_id = ? AND integration_id = ?
        """, (company_id, connector_id)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        return d


def get_connection(
    company_id: str = "default",
    integration_id: Optional[str] = None,
    connector_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Alias for get_connection_state supporting integration_id / connector_id kwargs."""
    cid = integration_id or connector_id or ""
    return get_connection_state(connector_id=cid, company_id=company_id)


def get_all_connection_states(company_id: str = "default") -> List[Dict[str, Any]]:
    """Retrieve all connection records for a company."""
    init_integration_db()
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM integration_connections WHERE company_id = ?
        """, (company_id,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["metadata"] = json.loads(d.get("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
            results.append(d)
        return results


def save_sync_record(
    record_or_dict: Any,
    company_id: str = "default"
) -> None:
    """Record a sync execution log."""
    init_integration_db()
    sync_id = f"sync_{uuid.uuid4().hex[:12]}"
    if hasattr(record_or_dict, "connector_id"):
        cid = record_or_dict.connector_id
        start = record_or_dict.sync_start
        end = record_or_dict.sync_end
        fetched = record_or_dict.records_fetched
        created = record_or_dict.records_created
        status = record_or_dict.status
        err = record_or_dict.error_message
    else:
        cid = record_or_dict.get("connector_id", "unknown")
        start = record_or_dict.get("sync_start", datetime.now(timezone.utc).isoformat())
        end = record_or_dict.get("sync_end")
        fetched = record_or_dict.get("records_fetched", 0)
        created = record_or_dict.get("records_created", 0)
        status = record_or_dict.get("status", "unknown")
        err = record_or_dict.get("error_message")

    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO integration_syncs (
                id, company_id, integration_id, sync_status,
                started_at, completed_at, records_fetched, records_created, records_updated, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sync_id, company_id, cid, status, start, end, fetched, created, 0, err))
        conn.commit()


def get_sync_history(connector_id: str, company_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recent sync execution logs."""
    init_integration_db()
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM integration_syncs
            WHERE company_id = ? AND integration_id = ?
            ORDER BY started_at DESC LIMIT ?
        """, (company_id, connector_id, limit)).fetchall()
        return [dict(r) for r in rows]
