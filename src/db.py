import os
import sqlite3
from datetime import datetime
from typing import List, Dict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "reglens.db")

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
    os.makedirs(DATA_DIR, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()


def log_request(profile: Dict[str, str], status: str, result_text: str, source_documents: str | None = None) -> int:
    conn = get_connection()
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
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def fetch_recent_requests(limit: int = 50) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM compliance_requests ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
