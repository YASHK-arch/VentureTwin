"""
Normalized data record store with provenance tracking.

Stores integration records from all connectors in a provenance-aware SQLite table
so agents can query across integrations without caring about raw API shape.
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


def _init_normalized_db() -> None:
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_records (
                id              TEXT PRIMARY KEY,
                company_id      TEXT NOT NULL DEFAULT 'default',
                integration     TEXT NOT NULL,
                agent_domain    TEXT NOT NULL,
                entity_type     TEXT NOT NULL,
                entity_id       TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                provenance_type TEXT NOT NULL,
                provenance_source TEXT NOT NULL,
                payload_json    TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ir_domain ON integration_records(agent_domain)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ir_integration ON integration_records(integration)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ir_company ON integration_records(company_id)")
        conn.commit()


def upsert_records(records: List[Dict[str, Any]]) -> int:
    """
    Upsert a list of normalized records (from make_normalized_record).
    Returns number of records written.
    """
    _init_normalized_db()
    written = 0
    with _get_connection() as conn:
        for rec in records:
            provenance = rec.get("provenance", {})
            rec_id = rec.get("entity_id") or str(uuid.uuid4())
            # Composite key: integration + entity_type + entity_id + company_id
            compound_id = f"{rec.get('integration','?')}:{rec.get('entity_type','?')}:{rec_id}:{rec.get('company_id','default')}"
            conn.execute("""
                INSERT INTO integration_records
                    (id, company_id, integration, agent_domain, entity_type, entity_id,
                     timestamp, provenance_type, provenance_source, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    timestamp        = excluded.timestamp,
                    provenance_type  = excluded.provenance_type,
                    provenance_source = excluded.provenance_source,
                    payload_json     = excluded.payload_json
            """, (
                compound_id,
                rec.get("company_id", "default"),
                rec.get("integration", ""),
                rec.get("agent_domain", ""),
                rec.get("entity_type", ""),
                rec.get("entity_id", ""),
                rec.get("timestamp", datetime.now(timezone.utc).isoformat()),
                provenance.get("type", "real_api"),
                provenance.get("source", "unknown"),
                json.dumps(rec.get("payload", {})),
            ))
            written += 1
        conn.commit()
    return written


def get_records_by_domain(
    agent_domain: str,
    company_id: str = "default",
    limit: int = 500
) -> List[Dict[str, Any]]:
    _init_normalized_db()
    with _get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM integration_records
               WHERE agent_domain = ? AND company_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (agent_domain, company_id, limit)
        ).fetchall()
        return _rows_to_dicts(rows)


def get_records_by_integration(
    connector_id: str,
    company_id: str = "default",
    limit: int = 500
) -> List[Dict[str, Any]]:
    _init_normalized_db()
    with _get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM integration_records
               WHERE integration = ? AND company_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (connector_id, company_id, limit)
        ).fetchall()
        return _rows_to_dicts(rows)


def get_latest_records(
    agent_domain: str,
    entity_types: Optional[List[str]] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    _init_normalized_db()
    with _get_connection() as conn:
        if entity_types:
            placeholders = ",".join("?" * len(entity_types))
            rows = conn.execute(
                f"""SELECT * FROM integration_records
                   WHERE agent_domain = ? AND entity_type IN ({placeholders})
                   ORDER BY timestamp DESC LIMIT ?""",
                [agent_domain, *entity_types, limit]
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM integration_records
                   WHERE agent_domain = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (agent_domain, limit)
            ).fetchall()
        return _rows_to_dicts(rows)


def clear_synthetic_records(connector_id: str, company_id: str = "default") -> int:
    """Remove all synthetic records for a given connector + company."""
    _init_normalized_db()
    with _get_connection() as conn:
        cursor = conn.execute(
            """DELETE FROM integration_records
               WHERE integration = ? AND company_id = ?
               AND provenance_type IN ('synthetic_external', 'synthetic_internal')""",
            (connector_id, company_id)
        )
        conn.commit()
        return cursor.rowcount


def _rows_to_dicts(rows) -> List[Dict[str, Any]]:
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["payload"] = json.loads(d.pop("payload_json", "{}"))
        except Exception:
            d["payload"] = {}
        result.append(d)
    return result
