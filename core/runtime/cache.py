"""PyGo Cache System (v0.31.0).

Provides in-memory and Redis cache implementations.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import time
import hashlib
import pickle


class CacheBackend:
    """Base cache backend interface."""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    def clear(self) -> None:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """In-memory cache implementation."""
    
    def __init__(self):
        self._store: Dict[str, tuple] = {}  # key -> (value, expires_at)
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        
        value, expires_at = self._store[key]
        if expires_at and time.time() > expires_at:
            del self._store[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        expires_at = None
        if ttl:
            expires_at = time.time() + ttl
        
        self._store[key] = (value, expires_at)
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    def clear(self) -> None:
        self._store.clear()


class RedisCache(CacheBackend):
    """Redis cache implementation (optional dependency)."""
    
    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client = None
    
    def _get_client(self):
        """Lazy-load Redis client."""
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password
                )
            except ImportError:
                raise ImportError("Redis support requires: pip install redis")
        return self._client
    
    def get(self, key: str) -> Optional[Any]:
        client = self._get_client()
        value = client.get(key)
        if value is None:
            return None
        return pickle.loads(value)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        client = self._get_client()
        data = pickle.dumps(value)
        if ttl:
            client.setex(key, ttl, data)
        else:
            client.set(key, data)
        return True
    
    def delete(self, key: str) -> bool:
        client = self._get_client()
        return client.delete(key) > 0
    
    def clear(self) -> None:
        client = self._get_client()
        client.flushdb()


class Cache:
    """Cache wrapper with key generation and decorators."""
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or MemoryCache()
    
    def get(self, key: str) -> Optional[Any]:
        return self.backend.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return self.backend.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        return self.backend.delete(key)
    
    def clear(self) -> None:
        self.backend.clear()
    
    def remember(self, key: str, ttl: Optional[int], callback: Callable) -> Any:
        """Get from cache or compute and store."""
        value = self.get(key)
        if value is not None:
            return value
        
        value = callback()
        self.set(key, value, ttl)
        return value
    
    def key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key."""
        data = f"{prefix}:{args}:{kwargs}"
        return hashlib.md5(data.encode()).hexdigest()


# Global cache instance
_default_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get the default cache instance."""
    global _default_cache
    if _default_cache is None:
        _default_cache = Cache(MemoryCache())
    return _default_cache


def cache(key: str = None, ttl: int = 300):
    """Decorator for caching function results."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate key
            if key:
                cache_key = key
            else:
                cache_key = cache.key(func.__name__, args, kwargs)
            
            return cache.remember(cache_key, ttl, lambda: func(*args, **kwargs))
        return wrapper
    return decorator


# Convenience functions
def get(key: str) -> Optional[Any]:
    """Get value from cache."""
    return get_cache().get(key)


def set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache."""
    return get_cache().set(key, value, ttl)


def delete(key: str) -> bool:
    """Delete value from cache."""
    return get_cache().delete(key)


def remember(key: str, ttl: int, callback: Callable) -> Any:
    """Get from cache or compute."""
    return get_cache().remember(key, ttl, callback)