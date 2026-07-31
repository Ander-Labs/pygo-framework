"""PyGo Connection Pool for Unix Domain Sockets (v1.0.0).

Provides connection pooling for UDS communication between Go and Python.
"""

from __future__ import annotations

import socket
import struct
import time
import threading
from typing import Optional, Any, Dict
from contextlib import contextmanager

import msgpack


class ConnectionPool:
    """Connection pool for Unix Domain Sockets."""
    
    def __init__(
        self,
        socket_path: str,
        min_size: int = 2,
        max_size: int = 4,
        timeout: float = 5.0,
        retry_delay: float = 0.1
    ):
        self.socket_path = socket_path
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.retry_delay = retry_delay
        
        self._pool: list[socket.socket] = []
        self._pool_lock = threading.Lock()
        self._initialized = False
        self._shutdown = False
    
    def _create_connection(self) -> socket.socket:
        """Create a new socket connection."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        return sock
    
    def initialize(self) -> None:
        """Initialize the pool with minimum connections."""
        with self._pool_lock:
            if self._initialized:
                return
            
            for _ in range(self.min_size):
                try:
                    conn = self._create_connection()
                    self._pool.append(conn)
                except Exception:
                    pass
            
            self._initialized = True
    
    def get_connection(self) -> socket.socket:
        """Get a connection from the pool."""
        with self._pool_lock:
            if self._pool:
                return self._pool.pop()
        
        # Pool empty, create new if under max
        if len(self._pool) < self.max_size:
            try:
                return self._create_connection()
            except Exception:
                pass
        
        # Wait for a connection to become available
        start = time.time()
        while time.time() - start < self.timeout:
            time.sleep(0.01)
            with self._pool_lock:
                if self._pool:
                    return self._pool.pop()
        
        raise ConnectionError("Timeout waiting for connection from pool")
    
    def return_connection(self, conn: socket.socket) -> None:
        """Return a connection to the pool."""
        with self._pool_lock:
            if self._shutdown or len(self._pool) >= self.max_size:
                try:
                    conn.close()
                except Exception:
                    pass
            else:
                self._pool.append(conn)
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        self._shutdown = True
        with self._pool_lock:
            for conn in self._pool:
                try:
                    conn.close()
                except Exception:
                    pass
            self._pool.clear()
    
    @contextmanager
    def connection(self):
        """Context manager for getting/returning a connection."""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn is not None:
                self.return_connection(conn)


class FramedConnection:
    """Length-prefixed msgpack framing over a socket."""
    
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
    
    def recv(self) -> Any:
        """Receive a framed message."""
        header = self._sock.recv(4)
        if not header or len(header) < 4:
            raise ConnectionError("Socket closed while reading")
        
        (length,) = struct.unpack(">I", header)
        body = self._sock.recv(length)
        
        if not body or len(body) < length:
            raise ConnectionError("Incomplete message received")
        
        return msgpack.unpackb(body, raw=False)
    
    def send(self, obj: Any) -> None:
        """Send a framed message."""
        body = msgpack.packb(obj, use_bin_type=True) or b""
        self._sock.sendall(struct.pack(">I", len(body)) + body)
    
    def close(self) -> None:
        """Close the underlying socket."""
        try:
            self._sock.close()
        except OSError:
            pass


# Global pool instance
_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_pool(socket_path: Optional[str] = None) -> ConnectionPool:
    """Get the global connection pool."""
    global _pool
    
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                path = socket_path or "/tmp/pygo.sock"
                _pool = ConnectionPool(path)
                _pool.initialize()
    
    return _pool


def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    
    with _pool_lock:
        if _pool is not None:
            _pool.close_all()
            _pool = None


# Circuit breaker state
_circuit_state = {
    "failures": 0,
    "last_failure": 0,
    "timeout": 60.0,  # Reset after 60 seconds of success
    "failure_threshold": 5,
    "open": False
}
_circuit_lock = threading.Lock()


def circuit_breaker_call(
    func,
    fallback=None,
    timeout: float = 5.0
) -> Any:
    """Execute a function with circuit breaker protection."""
    global _circuit_state
    
    with _circuit_lock:
        if _circuit_state["open"]:
            if time.time() - _circuit_state["last_failure"] > _circuit_state["timeout"]:
                _circuit_state["open"] = False
                _circuit_state["failures"] = 0
            else:
                if fallback:
                    return fallback()
                raise TimeoutError("Circuit breaker is open")
    
    try:
        result = func()
        
        # Reset on success
        with _circuit_lock:
            _circuit_state["failures"] = 0
            _circuit_state["open"] = False
        
        return result
    except Exception as e:
        with _circuit_lock:
            _circuit_state["failures"] += 1
            _circuit_state["last_failure"] = time.time()
            
            if _circuit_state["failures"] >= _circuit_state["failure_threshold"]:
                _circuit_state["open"] = True
        
        if fallback:
            return fallback()
        raise


if __name__ == "__main__":
    # Test the pool
    import os
    
    socket_path = os.getenv("PYGO_SOCKET", "/tmp/pygo.sock")
    
    try:
        pool = get_pool(socket_path)
        print(f"✅ Pool initialized with min_size={pool.min_size}, max_size={pool.max_size}")
        
        # Test getting/returning connections
        conn = pool.get_connection()
        print(f"✅ Got connection: {conn}")
        pool.return_connection(conn)
        print("✅ Returned connection")
        
        pool.close_all()
        print("✅ Pool closed")
    except Exception as e:
        print(f"❌ Error: {e}")