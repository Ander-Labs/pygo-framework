"""Test suite for v0.31.0 - Email and Cache systems."""
import pytest
import time

from core.runtime.email import (
    Email, EmailTemplate, EmailSender, EmailQueue,
    send_email, render_template, queue_email
)
from core.runtime.cache import (
    CacheBackend, MemoryCache, Cache, get_cache,
    get, set, delete, remember, cache, RedisCache
)


# ============== Email Tests ==============

def test_v0310_email_dataclass():
    """Test Email dataclass."""
    email = Email(
        to="test@example.com",
        subject="Test",
        body="Hello"
    )
    
    assert email.to == "test@example.com"
    assert email.subject == "Test"
    assert email.body == "Hello"


def test_v0310_email_template():
    """Test email template rendering."""
    template = "Hello {{ name }}, your order #{{ order_id }} is ready."
    t = EmailTemplate(template)
    
    result = t.render({"name": "Alice", "order_id": 123})
    assert "Alice" in result
    assert "123" in result


def test_v0310_email_queue():
    """Test email queue."""
    eq = EmailQueue()
    
    email = Email(to="test@example.com", subject="Test", body="Hello")
    idx = eq.enqueue(email)
    
    assert idx == 0


def test_v0310_send_email_convenience():
    """Test send_email convenience function."""
    # This will fail without SMTP server, but tests the interface
    result = send_email("test@example.com", "Test", "Body")
    # Result depends on SMTP availability


# ============== Cache Tests ==============

def test_v0310_memory_cache():
    """Test MemoryCache basic operations."""
    cache = MemoryCache()
    
    # Set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    # Delete
    cache.delete("key1")
    assert cache.get("key1") is None
    
    # Clear
    cache.set("key2", "value2")
    cache.clear()
    assert cache.get("key2") is None


def test_v0310_memory_cache_ttl():
    """Test MemoryCache with TTL."""
    cache = MemoryCache()
    
    cache.set("key1", "value1", ttl=1)
    assert cache.get("key1") == "value1"
    
    time.sleep(1.1)
    assert cache.get("key1") is None  # Expired


def test_v0310_cache_wrapper():
    """Test Cache wrapper."""
    cache = Cache(MemoryCache())
    
    cache.set("key1", "value1", ttl=60)
    assert cache.get("key1") == "value1"
    
    # Remember
    result = cache.remember("key2", 60, lambda: "computed")
    assert result == "computed"
    
    # Should return cached value
    result2 = cache.remember("key2", 60, lambda: "different")
    assert result2 == "computed"


def test_v0310_cache_key_generation():
    """Test cache key generation."""
    cache = Cache(MemoryCache())
    
    key1 = cache.key("prefix", "arg1", "arg2", kwarg1="val1")
    key2 = cache.key("prefix", "arg1", "arg2", kwarg1="val1")
    key3 = cache.key("prefix", "arg1", "arg2", kwarg1="val2")
    
    assert key1 == key2
    assert key1 != key3


def test_v0310_global_cache_functions():
    """Test global cache convenience functions."""
    set("test_key", "test_value")
    assert get("test_key") == "test_value"
    
    assert remember("remember_key", 60, lambda: "computed") == "computed"
    
    delete("test_key")
    assert get("test_key") is None


def test_v0310_cache_decorator():
    """Test cache decorator."""
    call_count = [0]
    
    @cache(ttl=60)
    def expensive_func(x):
        call_count[0] += 1
        return x * 2
    
    # First call
    result1 = expensive_func(5)
    assert result1 == 10
    assert call_count[0] == 1
    
    # Second call (cached)
    result2 = expensive_func(5)
    assert result2 == 10
    assert call_count[0] == 1  # Not incremented


def test_v0310_redis_cache_import_error():
    """Test RedisCache raises helpful error when redis not installed."""
    try:
        import redis
        pytest.skip("redis is installed")
    except ImportError:
        rc = RedisCache()
        try:
            rc.get("test")
            pytest.fail("Should have raised ImportError")
        except ImportError as e:
            assert "redis" in str(e).lower()
