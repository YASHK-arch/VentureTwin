import os
import sqlite3
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "venturetwin_auth.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db() -> None:
    """Initialize authentication tables and seed default executive user if none exists."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Executive',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                remember_me INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # Seed default executive account if users table is empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            seed_user_id = "usr_executive_nimbusdesk"
            seed_email = "ceo@nimbusdesk.io"
            seed_pw = "VentureTwin2026!"
            seed_name = "Elena Rostova (CEO)"
            pw_hash = hash_password(seed_pw)
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (seed_user_id, seed_email, pw_hash, seed_name, "Executive CEO", now))
            conn.commit()

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte random salt."""
    salt = secrets.token_bytes(16)
    iterations = 600_000
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored hash using constant-time comparison."""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False

def create_user(email: str, password: str, full_name: str, role: str = "Executive") -> Dict[str, Any]:
    """Create a new user account."""
    email_clean = email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise ValueError("Invalid email address format.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if not full_name.strip():
        raise ValueError("Full name is required.")

    user_id = f"usr_{secrets.token_hex(8)}"
    pw_hash = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO users (id, email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, email_clean, pw_hash, full_name.strip(), role, now))
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("An account with this email address already exists.")

    return {
        "id": user_id,
        "email": email_clean,
        "full_name": full_name.strip(),
        "role": role,
        "created_at": now
    }

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with email and password."""
    email_clean = email.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
        row = cursor.fetchone()
        if not row:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "created_at": row["created_at"]
        }

def create_session(user_id: str, remember_me: bool = False) -> Dict[str, Any]:
    """Create a cryptographically secure session token."""
    token = secrets.token_urlsafe(32)
    now_dt = datetime.now(timezone.utc)
    if remember_me:
        expires_dt = now_dt + timedelta(days=30)
    else:
        expires_dt = now_dt + timedelta(hours=24)

    now = now_dt.isoformat()
    expires_at = expires_dt.isoformat()

    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO sessions (token, user_id, remember_me, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (token, user_id, 1 if remember_me else 0, now, expires_at))
        conn.commit()

    max_age_seconds = 30 * 24 * 3600 if remember_me else 24 * 3600
    return {
        "token": token,
        "expires_at": expires_at,
        "max_age_seconds": max_age_seconds,
        "remember_me": remember_me
    }

def get_session_user(token: str) -> Optional[Dict[str, Any]]:
    """Validate session token and return user profile if not expired."""
    if not token:
        return None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.token, s.expires_at, u.id, u.email, u.full_name, u.role, u.created_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        row = cursor.fetchone()
        if not row:
            return None

        # Check expiration
        expires_dt = datetime.fromisoformat(row["expires_at"])
        if datetime.now(timezone.utc) > expires_dt:
            # Delete expired session
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "created_at": row["created_at"]
        }

def delete_session(token: str) -> None:
    """Invalidate and remove session token."""
    if not token:
        return
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

def create_password_reset(email: str) -> Optional[str]:
    """Generate simulated password reset token for user if account exists."""
    email_clean = email.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if not cursor.fetchone():
            return None
        token = secrets.token_urlsafe(24)
        reset_id = f"rst_{secrets.token_hex(6)}"
        now = datetime.now(timezone.utc).isoformat()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        conn.execute("""
            INSERT INTO password_resets (id, email, token, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (reset_id, email_clean, token, now, expires_at))
        conn.commit()
        return token

# Initialize auth db on module load
init_auth_db()
