import os
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS compliance_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    business_type TEXT NOT NULL,
    industry TEXT NOT NULL,
    services TEXT NOT NULL,
    customer_type TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    revenue TEXT NOT NULL,
    status TEXT NOT NULL,
    result_text TEXT NOT NULL,
    source_documents TEXT
)
"""


def _get_db_path() -> str:
    path = settings.DATABASE_PATH
    if path == ":memory:":
        return ":memory:"
    if path.startswith("sqlite:///"):
        path = path.removeprefix("sqlite:///")
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return path


def ensure_db_dir() -> None:
    db_path = _get_db_path()
    if db_path != ":memory:":
        dir_name = os.path.dirname(db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_db_dir()
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=settings.DB_TIMEOUT,
        )
        conn.row_factory = sqlite3.Row
        if db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        # Ensure table exists (especially vital for :memory: connections)
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
        return conn
    except sqlite3.Error as exc:
        logger.exception("Could not open SQLite database at %s", db_path)
        raise RuntimeError(f"Database is unavailable at {db_path}") from exc


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
        logger.info("SQLite database schema initialized at %s", _get_db_path())
    except sqlite3.Error as exc:
        logger.exception("Could not initialize database schema")
        raise RuntimeError("Database initialization failed") from exc
    finally:
        conn.close()


def ping_database() -> dict:
    conn = get_connection()
    try:
        conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "path": _get_db_path()}
    finally:
        conn.close()


def log_request(
    profile: Dict[str, str],
    status: str,
    result_text: str,
    source_documents: Optional[str] = None,
) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO compliance_requests (
                timestamp, business_type, industry, services,
                customer_type, transaction_type, revenue,
                status, result_text, source_documents
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                profile.get("business_type", ""),
                profile.get("industry", ""),
                profile.get("services", ""),
                profile.get("customer_type", ""),
                profile.get("transaction_type", ""),
                profile.get("revenue", ""),
                status,
                result_text,
                source_documents,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.exception("Could not write compliance request audit log")
        raise RuntimeError("Audit logging failed") from exc
    finally:
        conn.close()


def fetch_recent_requests(limit: int = 50) -> List[Dict]:
    conn = get_connection()
    try:
        safe_limit = max(1, min(int(limit), 200))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM compliance_requests ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except (sqlite3.Error, TypeError, ValueError) as exc:
        logger.exception("Could not fetch recent compliance requests")
        raise RuntimeError("Audit history is unavailable") from exc
    finally:
        conn.close()
