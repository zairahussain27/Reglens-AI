import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = logging.getLogger(__name__)


def _resolve_sqlite_path(database_url: str | None) -> str:
    if not database_url:
        return os.path.join(ROOT_DIR, "data", "reglens.db")

    if database_url == "sqlite:///:memory:":
        return ":memory:"

    if not database_url.startswith("sqlite:///"):
        raise RuntimeError("Only sqlite:/// DATABASE_URL values are supported by this app.")

    db_path = database_url.removeprefix("sqlite:///")
    if os.path.isabs(db_path):
        return db_path
    return os.path.abspath(os.path.join(ROOT_DIR, db_path))


DB_PATH = _resolve_sqlite_path(os.getenv("DATABASE_URL"))
DATA_DIR = os.path.dirname(DB_PATH) if DB_PATH != ":memory:" else ""

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


def ensure_data_dir() -> None:
    if DATA_DIR:
        os.makedirs(DATA_DIR, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_data_dir()
    try:
        conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False,
            timeout=int(os.getenv("DB_TIMEOUT", "10")),
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn
    except sqlite3.Error as exc:
        logger.exception("Could not open SQLite database at %s", DB_PATH)
        raise RuntimeError("Database is unavailable") from exc


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    except sqlite3.Error as exc:
        logger.exception("Could not initialize database schema")
        raise RuntimeError("Database initialization failed") from exc
    finally:
        conn.close()


def ping_database() -> dict:
    conn = get_connection()
    try:
        conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "path": DB_PATH}
    finally:
        conn.close()


def log_request(profile: Dict[str, str], status: str, result_text: str, source_documents: str | None = None) -> int:
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
                datetime.utcnow().isoformat(),
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
