"""PyGo native DB helper (Fase 0/0.3.0).

Thin, dependency-free SQLite access used by generated model code. For
production, swap the connection for psycopg (a minimal driver, not a heavy
ORM) — the generated model methods only need `connect()` and `execute()`.

Kept intentionally small: PyGo's principle is native/stdlib only.
"""

from __future__ import annotations

import os
import sqlite3
import time
import threading
from typing import Any, Optional, Union
from contextlib import contextmanager

DEFAULT_DB_PATH = "pygo.db"

# Connection pool for PostgreSQL/MySQL
_connection_pool: dict[str, Any] = {}
_pool_lock = threading.Lock()
_POOL_SIZE = 10


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


@contextmanager
def get_connection(db_path: Optional[str] = None, tenant: Optional[str] = None, db_type: str = DBType.SQLITE):
    """Context manager for database connections with pooling."""
    conn = None
    try:
        conn = _get_connection(db_path, tenant, db_type)
        yield conn
    finally:
        if conn:
            _return_connection(conn, db_type)


def _get_connection(db_path: Optional[str] = None, tenant: Optional[str] = None, db_type: str = DBType.SQLITE):
    """Get a connection from pool or create new one."""
    if db_type == DBType.SQLITE:
        return _get_sqlite_connection(db_path, tenant)
    
    # PostgreSQL/MySQL - use connection pool
    key = f"{db_type}:{db_path or 'default'}"
    
    with _pool_lock:
        if key not in _connection_pool:
            _connection_pool[key] = []
        
        pool = _connection_pool[key]
        
        if pool:
            return pool.pop()
    
    # Create new connection
    return _create_external_connection(db_path, db_type)


def _return_connection(conn: Any, db_type: str) -> None:
    """Return connection to pool."""
    if db_type == DBType.SQLITE:
        conn.close()
        return
    
    key = f"{db_type}:{conn.info.get('dbname', 'default') if hasattr(conn, 'info') else 'default'}"
    
    with _pool_lock:
        if key in _connection_pool:
            pool = _connection_pool[key]
            if len(pool) < _POOL_SIZE:
                pool.append(conn)
            else:
                conn.close()  # Pool full, close connection
        else:
            try:
                conn.close()
            except:
                pass


def _get_sqlite_connection(db_path: Optional[str] = None, tenant: Optional[str] = None):
    """Get SQLite connection."""
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


def _create_external_connection(db_path: str, db_type: str):
    """Create PostgreSQL or MySQL connection."""
    if db_type == DBType.POSTGRES:
        try:
            import psycopg
        except ImportError:
            raise ImportError("PostgreSQL support requires: pip install psycopg")
        conn = psycopg.connect(db_path)
        return conn
    elif db_type == DBType.MYSQL:
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("MySQL support requires: pip install mysql-connector-python")
        conn = mysql.connector.connect(**_parse_mysql_url(db_path))
        return conn
    raise ValueError(f"Unsupported DB type: {db_type}")


def _parse_mysql_url(url: str) -> dict:
    """Parse MySQL connection URL to connector kwargs."""
    import re
    match = re.match(r"mysql://([^:***@]+)@([^:]+):(\d+)/(.+)", url)
    if match:
        return {
            "user": match.group(1),
            "password": match.group(2),
            "host": match.group(3),
            "port": int(match.group(4)),
            "database": match.group(5),
        }
    raise ValueError(f"Invalid MySQL URL: {url}")


def connect(db_path: Optional[str] = None, tenant: Optional[str] = None, db_type: str = DBType.SQLITE) -> Union[sqlite3.Connection, Any]:
    """Open a database connection. 
    
    For production use, prefer get_connection() with context manager.
    """
    return _get_connection(db_path, tenant, db_type)


def ensure_table(conn, table: str, columns: list[str], db_type: str = DBType.SQLITE) -> None:
    """Create table if it does not exist. columns: list of 'name TYPE' DDL."""
    ddl = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})"
    conn.execute(ddl)
    conn.commit()


def run_migrations(conn, migrations_dir: str = "db/migrations", db_type: str = DBType.SQLITE) -> list[str]:
    """Run all migrations in order. Returns list of applied migrations."""
    import re
    from pathlib import Path
    
    applied = []
    migration_files = sorted(Path(migrations_dir).glob("*.sql"))
    
    for migration_file in migration_files:
        with open(migration_file) as f:
            sql = f.read()
        
        # Handle rollback comments: -- @rollback: DROP TABLE...
        rollback_match = re.search(r'-- @rollback:\s*(.+)', sql, re.MULTILINE | re.DOTALL)
        
        if rollback_match:
            # Store rollback SQL
            rollback_sql = rollback_match.group(1).strip()
        else:
            rollback_sql = None
        
        # Execute migration (remove rollback comment from SQL)
        migration_sql = re.sub(r'-- @rollback:.*', '', sql, flags=re.MULTILINE | re.DOTALL).strip()
        
        try:
            conn.executescript(migration_sql) if db_type == DBType.SQLITE else conn.execute(migration_sql)
            conn.commit()
            applied.append(migration_file.stem)
        except Exception as e:
            if applied:
                # Rollback on error
                if rollback_sql:
                    conn.executescript(rollback_sql) if db_type == DBType.SQLITE else conn.execute(rollback_sql)
                    conn.commit()
            raise e
    
    return applied


def soft_delete(conn, table: str, id_field: str, id_value: Any, db_type: str = DBType.SQLITE) -> None:
    """Soft delete a record by setting deleted_at timestamp."""
    import datetime
    
    deleted_at = datetime.datetime.utcnow().isoformat()
    
    if db_type == DBType.SQLITE:
        sql = f"UPDATE {table} SET deleted_at = ? WHERE {id_field} = ? AND deleted_at IS NULL"
        conn.execute(sql, (deleted_at, id_value))
    else:
        sql = f"UPDATE {table} SET deleted_at = %s WHERE {id_field} = ? AND deleted_at IS NULL"
        conn.execute(sql, (deleted_at, id_value))
    
    conn.commit()


def hard_delete(conn, table: str, id_field: str, id_value: Any, db_type: str = DBType.SQLITE) -> None:
    """Hard delete a record permanently."""
    if db_type == DBType.SQLITE:
        sql = f"DELETE FROM {table} WHERE {id_field} = ?"
        conn.execute(sql, (id_value,))
    else:
        sql = f"DELETE FROM {table} WHERE {id_field} = ?"
        conn.execute(sql, (id_value,))
    
    conn.commit()


def query_with_deleted(conn, table: str, include_deleted: bool = False, db_type: str = DBType.SQLITE) -> str:
    """Return WHERE clause that excludes deleted records unless include_deleted=True."""
    if include_deleted:
        return ""
    return f"AND deleted_at IS NULL"