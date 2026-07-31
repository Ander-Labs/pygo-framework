"""Integration tests for PostgreSQL (requires running PostgreSQL).

Run with: pytest core/runtime/db_postgres_test.py -v --postgres-host=localhost --postgres-port=5432
"""
import pytest
import os
import sys

# Skip if PostgreSQL not available
pytest.importorskip("psycopg2", reason="PostgreSQL not available")

from core.runtime.db import Database, DBConfig


@pytest.fixture
def postgres_config():
    """Get PostgreSQL config from environment."""
    return DBConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        name=os.getenv("POSTGRES_DB", "pygo_test"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres")
    )


@pytest.fixture
def db(postgres_config):
    """Create database connection."""
    database = Database(postgres_config)
    database.connect()
    yield database
    database.close()


class TestPostgreSQLIntegration:
    """Integration tests for PostgreSQL."""
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )
    def test_connection(self, db):
        """Test database connection."""
        assert db.is_connected()
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )
    def test_create_tables(self, db):
        """Test table creation."""
        # Create test table
        db.execute("""
            CREATE TABLE IF NOT EXISTS test_users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                metadata JSONB
            )
        """)
        
        # Verify table exists
        result = db.query("SELECT to_regclass('test_users')")
        assert result[0][0] == 'test_users'
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS test_users")
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )
    def test_uuid_type(self, db):
        """Test UUID type support."""
        import uuid
        
        test_uuid = uuid.uuid4()
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS uuid_test (
                id UUID PRIMARY KEY,
                name TEXT
            )
        """)
        
        db.execute(
            "INSERT INTO uuid_test (id, name) VALUES (%s, %s)",
            (test_uuid, "test")
        )
        
        result = db.query(
            "SELECT id, name FROM uuid_test WHERE id = %s",
            (test_uuid,)
        )
        
        assert len(result) == 1
        assert str(result[0][0]) == str(test_uuid)
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS uuid_test")
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )
    def test_jsonb_type(self, db):
        """Test JSONB type support."""
        db.execute("""
            CREATE TABLE IF NOT EXISTS jsonb_test (
                id SERIAL PRIMARY KEY,
                data JSONB
            )
        """)
        
        test_data = {"key": "value", "nested": {"a": 1, "b": 2}}
        
        db.execute(
            "INSERT INTO jsonb_test (data) VALUES (%s)",
            (test_data,)
        )
        
        result = db.query("SELECT data FROM jsonb_test LIMIT 1")
        
        assert result[0][0] == test_data
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS jsonb_test")
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )
    def test_decimal_type(self, db):
        """Test DECIMAL type support."""
        db.execute("""
            CREATE TABLE IF NOT EXISTS decimal_test (
                id SERIAL PRIMARY KEY,
                amount DECIMAL(10, 2)
            )
        """)
        
        db.execute(
            "INSERT INTO decimal_test (amount) VALUES (%s)",
            (12345.67,)
        )
        
        result = db.query("SELECT amount FROM decimal_test LIMIT 1")
        
        assert float(result[0][0]) == 12345.67
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS decimal_test")
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )

    def test_connection_pooling(self, postgres_config):
        """Test connection pooling."""
        from core.runtime.db import create_pool
        
        pool = create_pool(
            host=postgres_config.host,
            port=postgres_config.port,
            database=postgres_config.name,
            user=postgres_config.user,
            password=postgres_config.password,
            min_size=2,
            max_size=5
        )
        
        # Get multiple connections
        conns = [pool.get_connection() for _ in range(3)]
        
        # Verify pool size
        assert pool.size() >= 2
        
        # Return connections
        for conn in conns:
            pool.return_connection(conn)
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )
    def test_migrations(self, db):
        """Test migration execution."""
        # Create migration table
        db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Apply migration
        db.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)",
            ("001_initial",)
        )
        
        result = db.query(
            "SELECT version FROM schema_migrations WHERE version = %s",
            ("001_initial",)
        )
        
        assert len(result) == 1
        assert result[0][0] == "001_initial"
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS schema_migrations")


class TestPostgreSQLTypes:
    """Test PostgreSQL-specific types."""
    
    @pytest.mark.skipif(
        not os.getenv("RUN_POSTGRES_TESTS"),
        reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL tests"
    )
    def test_timestamptz(self, db):
        """Test TIMESTAMP WITH TIME ZONE support."""
        from datetime import datetime, timezone
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS ts_test (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        db.execute("INSERT INTO ts_test DEFAULT VALUES")
        
        result = db.query("SELECT created_at FROM ts_test LIMIT 1")
        
        assert result[0][0] is not None
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS ts_test")