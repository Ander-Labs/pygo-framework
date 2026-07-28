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

# Per-request tenant. Set from Go-side args["tenant"] by the pyclient dispatch.
# Safe as a single global because the Go supervisor serializes CallPython
# with a mutex (one request at a time).
_current_tenant: Optional[str] = None


def set_tenant(tenant: Optional[str]) -> None:
    """Set the active tenant for the current (serialized) request."""
    global _current_tenant
    _current_tenant = tenant


def connect(db_path: Optional[str] = None, tenant: Optional[str] = None) -> sqlite3.Connection:
    """Open a SQLite connection. Resolution order:
       1. explicit db_path argument
       2. tenant arg -> pygo_<tenant>.db
       3. per-request _current_tenant global (set by dispatch)
       4. PYGO_DB env
       5. DEFAULT_DB_PATH

    The connection returns rows as dict-like via Row for easy serialization.
    """
    if db_path:
        path = db_path
    elif tenant:
        path = f"pygo_{tenant}.db"
    elif _current_tenant:
        path = f"pygo_{_current_tenant}.db"
    else:
        path = os.environ.get("PYGO_DB") or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table(conn: sqlite3.Connection, table: str, columns: list[str]) -> None:
    """Create table if it does not exist. columns: list of 'name TYPE' DDL."""
    ddl = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})"
    conn.execute(ddl)
    conn.commit()
