"""Integration tests for PostgreSQL (requires running PostgreSQL).

Run with: pytest core/runtime/db_postgres_test.py -v --postgres-host=localhost --postgres-port=5432
"""
import pytest
import os

from core.runtime.db import DBType, connect, get_connection, ensure_table


# PostgreSQL connection settings
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "pygo_test")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")


@pytest.fixture
def postgres_url():
    """Build PostgreSQL connection URL."""
    return f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


@pytest.fixture
def pg_conn(postgres_url):
    """Get PostgreSQL connection."""
    try:
        import psycopg
        conn = psycopg.connect(postgres_url)
        yield conn
        conn.close()
    except ImportError:
        pytest.skip("psycopg not installed")
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL integration tests"
)
class TestPostgreSQLIntegration:
    """Integration tests against real PostgreSQL database."""
    
    def test_postgres_connection(self, pg_conn):
        """Test PostgreSQL connection."""
        assert pg_conn is not None
    
    def test_postgres_ensure_table(self, pg_conn):
        """Test table creation in PostgreSQL."""
        ensure_table(pg_conn, "test_products", [
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
            "name TEXT NOT NULL",
            "price DECIMAL(10,2)",
            "created_at TIMESTAMP DEFAULT NOW()"
        ], db_type=DBType.POSTGRES)
        
        # Verify table exists
        cursor = pg_conn.execute(
            "SELECT to_regclass('test_products')"
        )
        result = cursor.fetchone()
        assert result[0] is not None
    
    def test_postgres_insert_select(self, pg_conn):
        """Test insert and select in PostgreSQL."""
        # Create table
        ensure_table(pg_conn, "test_items", [
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
            "name TEXT NOT NULL",
            "created_at TIMESTAMP DEFAULT NOW()"
        ], db_type=DBType.POSTGRES)
        
        # Insert
        cursor = pg_conn.execute(
            "INSERT INTO test_items (name) VALUES (%s) RETURNING id, name, created_at",
            ("Test Item",)
        )
        result = cursor.fetchone()
        assert result is not None
        assert result[1] == "Test Item"
        assert result[2] is not None  # created_at
    
    def test_postgres_transaction(self, pg_conn):
        """Test transaction support in PostgreSQL."""
        ensure_table(pg_conn, "test_transactions", [
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
            "value INTEGER"
        ], db_type=DBType.POSTGRES)
        
        # Start transaction
        pg_conn.execute("BEGIN")
        
        try:
            # Insert
            pg_conn.execute(
                "INSERT INTO test_transactions (value) VALUES (%s)",
                (100,)
            )
            
            # Check
            cursor = pg_conn.execute("SELECT COUNT(*) FROM test_transactions")
            count = cursor.fetchone()[0]
            assert count == 1
            
            # Commit
            pg_conn.commit()
        except Exception as e:
            pg_conn.rollback()
            raise e
    
    def test_postgres_connection_pooling(self, postgres_url):
        """Test connection pooling with PostgreSQL."""
        try:
            import psycopg
        except ImportError:
            pytest.skip("psycopg not installed")
        
        # Get multiple connections
        connections = []
        for i in range(5):
            conn = connect(postgres_url, db_type=DBType.POSTGRES)
            connections.append(conn)
        
        # All should be valid
        for conn in connections:
            assert conn is not None
        
        # Close all
        for conn in connections:
            conn.close()


@pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL integration tests"
)
class TestPostgreSQLTypes:
    """Test PostgreSQL-specific types."""
    
    def test_uuid_type(self, pg_conn):
        """Test UUID type support."""
        ensure_table(pg_conn, "test_uuids", [
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
            "data TEXT"
        ], db_type=DBType.POSTGRES)
        
        cursor = pg_conn.execute(
            "INSERT INTO test_uuids (data) VALUES (%s) RETURNING id, data",
            ("test",)
        )
        result = cursor.fetchone()
        
        # UUID should be returned
        assert result[0] is not None
        assert isinstance(result[0], str)
    
    def test_decimal_type(self, pg_conn):
        """Test DECIMAL type support."""
        ensure_table(pg_conn, "test_decimals", [
            "id SERIAL PRIMARY KEY",
            "amount DECIMAL(10,2)"
        ], db_type=DBType.POSTGRES)
        
        cursor = pg_conn.execute(
            "INSERT INTO test_decimals (amount) VALUES (%s) RETURNING amount",
            (123.45,)
        )
        result = cursor.fetchone()
        assert result[0] == 123.45
    
    def test_jsonb_type(self, pg_conn):
        """Test JSONB type support."""
        ensure_table(pg_conn, "test_jsonb", [
            "id SERIAL PRIMARY KEY",
            "data JSONB"
        ], db_type=DBType.POSTGRES)
        
        import json
        test_data = {"key": "value", "nested": {"a": 1, "b": 2}}
        
        cursor = pg_conn.execute(
            "INSERT INTO test_jsonb (data) VALUES (%s) RETURNING data",
            (test_data,)
        )
        result = cursor.fetchone()
        
        # Should be able to query JSONB
        cursor = pg_conn.execute(
            "SELECT data->>'key' FROM test_jsonb WHERE id = 1"
        )
        key_value = cursor.fetchone()[0]
        assert key_value == "value"


@pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL integration tests"
)
class TestPostgreSQLMigrations:
    """Test migration handling for PostgreSQL."""
    
    def test_migration_with_rollback(self, pg_conn):
        """Test migration with rollback comment."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            migrations_dir = os.path.join(tmpdir, "migrations")
            os.makedirs(migrations_dir)
            
            migration_file = os.path.join(migrations_dir, "003_with_rollback.sql")
            with open(migration_file, 'w') as f:
                f.write("""-- Test migration
CREATE TABLE IF NOT EXISTS test_rollback (
    id SERIAL PRIMARY KEY,
    name TEXT
);

-- @rollback: DROP TABLE IF EXISTS test_rollback;
""")
            
            from core.runtime.db import run_migrations
            applied = run_migrations(pg_conn, migrations_dir, DBType.POSTGRES)
            
            assert "003_with_rollback" in applied