import os
import json
import sqlite3
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "venturetwin_auth.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_company_context_db() -> None:
    """Initialize company_contexts table in the SQLite database."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_contexts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                company_name TEXT NOT NULL,
                industry TEXT NOT NULL,
                business_model TEXT NOT NULL,
                description TEXT NOT NULL,
                products_services TEXT NOT NULL,
                target_customers TEXT NOT NULL,
                revenue_model TEXT NOT NULL,
                geographic_presence TEXT,
                stage TEXT NOT NULL,
                strategic_goals TEXT NOT NULL,
                major_challenges TEXT,
                key_competitors TEXT,
                website_url TEXT,
                provenance_json TEXT NOT NULL DEFAULT '{}',
                uploaded_documents_json TEXT NOT NULL DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["provenance"] = json.loads(d.get("provenance_json") or "{}")
    except Exception:
        d["provenance"] = {}
    try:
        d["uploaded_documents"] = json.loads(d.get("uploaded_documents_json") or "[]")
    except Exception:
        d["uploaded_documents"] = []
    return d


def save_company_context(data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Saves or updates a company context profile.
    Supports multiple profiles; sets the saved profile as active.
    """
    init_company_context_db()
    context_id = data.get("id") or f"ctx_{secrets.token_hex(8)}"
    now = datetime.now(timezone.utc).isoformat()

    provenance_json = json.dumps(data.get("provenance", {}))
    uploaded_docs_json = json.dumps(data.get("uploaded_documents", []))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # If setting as active, mark other profiles for this user (or globally) as inactive
        cursor.execute("""
            UPDATE company_contexts
            SET is_active = 0
            WHERE user_id = ? OR (? IS NULL AND user_id IS NULL)
        """, (user_id, user_id))

        cursor.execute("""
            INSERT INTO company_contexts (
                id, user_id, company_name, industry, business_model,
                description, products_services, target_customers, revenue_model,
                geographic_presence, stage, strategic_goals, major_challenges,
                key_competitors, website_url, provenance_json, uploaded_documents_json,
                is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                company_name = excluded.company_name,
                industry = excluded.industry,
                business_model = excluded.business_model,
                description = excluded.description,
                products_services = excluded.products_services,
                target_customers = excluded.target_customers,
                revenue_model = excluded.revenue_model,
                geographic_presence = excluded.geographic_presence,
                stage = excluded.stage,
                strategic_goals = excluded.strategic_goals,
                major_challenges = excluded.major_challenges,
                key_competitors = excluded.key_competitors,
                website_url = excluded.website_url,
                provenance_json = excluded.provenance_json,
                uploaded_documents_json = excluded.uploaded_documents_json,
                is_active = 1,
                updated_at = excluded.updated_at
        """, (
            context_id,
            user_id,
            data.get("company_name", "").strip(),
            data.get("industry", "").strip(),
            data.get("business_model", "").strip(),
            data.get("description", "").strip(),
            data.get("products_services", "").strip(),
            data.get("target_customers", "").strip(),
            data.get("revenue_model", "").strip(),
            (data.get("geographic_presence") or "").strip(),
            data.get("stage", "").strip(),
            data.get("strategic_goals", "").strip(),
            (data.get("major_challenges") or "").strip(),
            (data.get("key_competitors") or "").strip(),
            (data.get("website_url") or "").strip(),
            provenance_json,
            uploaded_docs_json,
            now,
            now
        ))
        conn.commit()

        cursor.execute("SELECT * FROM company_contexts WHERE id = ?", (context_id,))
        row = cursor.fetchone()
        return row_to_dict(row)


def get_active_company_context(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns the currently active company context profile."""
    init_company_context_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT * FROM company_contexts
                WHERE (user_id = ? OR user_id IS NULL) AND is_active = 1
                ORDER BY updated_at DESC LIMIT 1
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM company_contexts
                WHERE is_active = 1
                ORDER BY updated_at DESC LIMIT 1
            """)
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def list_company_contexts(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists all saved company profiles (multi-profile support)."""
    init_company_context_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT * FROM company_contexts
                WHERE user_id = ? OR user_id IS NULL
                ORDER BY updated_at DESC
            """, (user_id,))
        else:
            cursor.execute("SELECT * FROM company_contexts ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [row_to_dict(r) for r in rows]


def get_company_context_by_id(context_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a specific company context by its ID."""
    init_company_context_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_contexts WHERE id = ?", (context_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def delete_company_context(context_id: str) -> bool:
    """Deletes a company context profile by ID."""
    init_company_context_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM company_contexts WHERE id = ?", (context_id,))
        conn.commit()
        return cursor.rowcount > 0
