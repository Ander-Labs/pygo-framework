"""Test suite for v0.27.0 - PostgreSQL support and ORM enhancements."""
import pytest
import sqlite3
import tempfile
import os

from core.runtime.db import connect, DBType, set_tenant


def test_v0270_sqlite_connection():
    """Test SQLite connection still works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = connect(db_path=db_path)
        try:
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1
        finally:
            conn.close()


def test_v0270_tenant_db_selection():
    """Test tenant-based database selection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        set_tenant("tenant1")
        conn1 = connect()
        conn1.execute("CREATE TABLE test (id INTEGER)")
        conn1.close()
        
        set_tenant("tenant2")
        conn2 = connect()
        # Should have separate DB files
        assert os.path.exists("pygo_tenant1.db")
        assert os.path.exists("pygo_tenant2.db")
        conn2.close()


def test_v0270_db_type_enum():
    """Test DBType enum values."""
    assert DBType.SQLITE == "sqlite"
    assert DBType.POSTGRES == "postgres"
    assert DBType.MYSQL == "mysql"


def test_v0270_postgres_import_error():
    """Test PostgreSQL raises helpful error when psycopg not installed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        try:
            conn = connect(db_path=db_path, db_type=DBType.POSTGRES)
            pytest.fail("Should have raised ImportError")
        except ImportError as e:
            assert "psycopg" in str(e)


def test_v0270_mysql_url_parsing():
    """Test MySQL connection URL parsing."""
    from core.runtime.db import _parse_mysql_url
    
    result = _parse_mysql_url("mysql://user:pass@localhost:3306/mydb")
    assert result["user"] == "user"
    assert result["password"] == "pass"
    assert result["host"] == "localhost"
    assert result["port"] == 3306
    assert result["database"] == "mydb"
