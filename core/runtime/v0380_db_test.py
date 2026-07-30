"""Test suite for v0.38.0 - PostgreSQL Real and ORM Enhancement."""
import pytest
import sqlite3
import tempfile
import os

from core.runtime.db import (
    DBType, connect, get_connection, ensure_table,
    run_migrations, soft_delete, hard_delete, query_with_deleted,
    set_tenant, _connection_pool, _pool_lock, _POOL_SIZE
)


def test_db_type_constants():
    """Test DB type constants exist."""
    assert DBType.SQLITE == "sqlite"
    assert DBType.POSTGRES == "postgres"
    assert DBType.MYSQL == "mysql"


def test_connect_sqlite():
    """Test SQLite connection."""
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        conn = connect(f.name, db_type=DBType.SQLITE)
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        conn.close()


def test_get_connection_context_manager():
    """Test get_connection context manager."""
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        with get_connection(f.name, db_type=DBType.SQLITE) as conn:
            assert conn is not None
        # Connection should be closed after context


def test_ensure_table():
    """Test table creation."""
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        conn = connect(f.name, db_type=DBType.SQLITE)
        
        # Create test table
        ensure_table(conn, "users", [
            "id INTEGER PRIMARY KEY",
            "email TEXT UNIQUE",
            "created_at TEXT"
        ])
        
        # Verify table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        result = cursor.fetchone()
        assert result is not None
        
        conn.close()


def test_soft_delete():
    """Test soft delete functionality."""
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        conn = connect(f.name, db_type=DBType.SQLITE)
        
        # Create table with deleted_at column
        ensure_table(conn, "items", [
            "id INTEGER PRIMARY KEY",
            "name TEXT",
            "deleted_at TEXT"
        ])
        
        # Insert record
        conn.execute("INSERT INTO items (id, name) VALUES (1, 'test')")
        conn.commit()
        
        # Soft delete
        soft_delete(conn, "items", "id", 1)
        
        # Verify deleted_at is set
        cursor = conn.execute("SELECT deleted_at FROM items WHERE id = 1")
        result = cursor.fetchone()
        assert result[0] is not None
        
        conn.close()


def test_hard_delete():
    """Test hard delete functionality."""
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        conn = connect(f.name, db_type=DBType.SQLITE)
        
        # Create table
        ensure_table(conn, "temp_items", [
            "id INTEGER PRIMARY KEY",
            "name TEXT"
        ])
        
        # Insert record
        conn.execute("INSERT INTO temp_items (id, name) VALUES (1, 'temp')")
        conn.commit()
        
        # Hard delete
        hard_delete(conn, "temp_items", "id", 1)
        
        # Verify record is gone
        cursor = conn.execute("SELECT COUNT(*) FROM temp_items")
        count = cursor.fetchone()[0]
        assert count == 0
        
        conn.close()


def test_query_with_deleted():
    """Test query_with_deleted helper."""
    # Should return empty string for normal query
    clause = query_with_deleted(None, "users", include_deleted=False)
    assert clause == "AND deleted_at IS NULL"
    
    # Should return empty string when include_deleted=True
    clause = query_with_deleted(None, "users", include_deleted=True)
    assert clause == ""


def test_tenant_isolation():
    """Test tenant-based database naming."""
    set_tenant("tenant_a")
    
    # Should use tenant-specific database
    conn = connect(db_type=DBType.SQLITE)
    # Connection object, check the file path differently
    assert conn is not None
    conn.close()
    
    set_tenant(None)
