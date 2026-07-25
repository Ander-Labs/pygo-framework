"""PyGo native DB helper (Fase 0/0.3.0).

Thin, dependency-free SQLite access used by generated model code. For
production, swap the connection for psycopg (a minimal driver, not a heavy
ORM) — the generated model methods only need `connect()` and `execute()`.

Kept intentionally small: PyGo's principle is native/stdlib only.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Optional

DEFAULT_DB_PATH = "pygo.db"


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a SQLite connection. db_path comes from PYGO_DB env or default.

    The connection returns rows as dict-like via Row for easy serialization.
    """
    path = db_path or os.environ.get("PYGO_DB") or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table(conn: sqlite3.Connection, table: str, columns: list[str]) -> None:
    """Create table if it does not exist. columns: list of 'name TYPE' DDL."""
    ddl = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})"
    conn.execute(ddl)
    conn.commit()
