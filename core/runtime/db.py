"""PyGo native DB helper (Fase 0/0.3.0).

Thin, dependency-free SQLite access used by generated model code. For
production, swap the connection for psycopg (a minimal driver, not a heavy
ORM) — the generated model methods only need `connect()` and `execute()`.

Kept intentionally small: PyGo's principle is native/stdlib only.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Optional, Union

DEFAULT_DB_PATH = "pygo.db"

# Database type support
class DBType:
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MYSQL = "mysql"

# Per-request tenant. Set from Go-side args["tenant"] by the pyclient dispatch.
# Safe as a single global because the Go supervisor serializes CallPython
# with a mutex (one request at a time).
_current_tenant: Optional[str] = None


def set_tenant(tenant: Optional[str]) -> None:
    """Set the active tenant for the current (serialized) request."""
    global _current_tenant
    _current_tenant = tenant


def connect(db_path: Optional[str] = None, tenant: Optional[str] = None, db_type: str = DBType.SQLITE) -> Union[sqlite3.Connection, Any]:
    """Open a database connection. Resolution order:
       1. explicit db_path argument
       2. tenant arg -> pygo_<tenant>.db
       3. per-request _current_tenant global (set by dispatch)
       4. PYGO_DB env
       5. DEFAULT_DB_PATH

    The connection returns rows as dict-like via Row for easy serialization.
    
    For PostgreSQL, install psycopg (minimal driver).
    For MySQL, install mysql-connector-python.
    """
    if db_path:
        path = db_path
    elif tenant:
        path = f"pygo_{tenant}.db"
    elif _current_tenant:
        path = f"pygo_{_current_tenant}.db"
    else:
        path = os.environ.get("PYGO_DB") or DEFAULT_DB_PATH
    
    if db_type == DBType.POSTGRES:
        # Lazy import to avoid dependency if not used
        try:
            import psycopg
        except ImportError:
            raise ImportError("PostgreSQL support requires: pip install psycopg")
        # Parse connection string: postgres://user:pass@host:port/dbname
        conn = psycopg.connect(path)
        return conn
    elif db_type == DBType.MYSQL:
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("MySQL support requires: pip install mysql-connector-python")
        # Parse connection string: mysql://user:pass@host:port/dbname
        conn = mysql.connector.connect(**_parse_mysql_url(path))
        return conn
    else:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn


def _parse_mysql_url(url: str) -> dict:
    """Parse MySQL connection URL to connector kwargs."""
    import re
    match = re.match(r"mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", url)
    if match:
        return {
            "user": match.group(1),
            "password": match.group(2),
            "host": match.group(3),
            "port": int(match.group(4)),
            "database": match.group(5),
        }
    raise ValueError(f"Invalid MySQL URL: {url}")


def ensure_table(conn, table: str, columns: list[str], db_type: str = DBType.SQLITE) -> None:
    """Create table if it does not exist. columns: list of 'name TYPE' DDL."""
    ddl = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})"
    conn.execute(ddl)
    conn.commit()
