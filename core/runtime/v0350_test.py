"""Test suite for v0.35.0 - Benchmarks and Security."""
import pytest
import time

from core.runtime.benchmark import BenchmarkRunner, BenchmarkResult, benchmark


def test_v0350_benchmark_result():
    """Test BenchmarkResult dataclass."""
    result = BenchmarkResult(
        name="test",
        duration=0.5,
        iterations=100,
        ops_per_second=200.0
    )
    
    assert result.name == "test"
    assert result.duration == 0.5


def test_v0350_benchmark_runner():
    """Test BenchmarkRunner."""
    runner = BenchmarkRunner()
    
    def test_func():
        return 1 + 1
    
    result = runner.run("test_func", test_func, iterations=10)
    
    assert result.name == "test_func"
    assert result.iterations == 10
    assert len(runner.results) == 1


def test_v0350_benchmark_runner_report():
    """Test BenchmarkRunner report."""
    runner = BenchmarkRunner()
    
    runner.run("test", lambda: 1, iterations=5)
    report = runner.report()
    
    assert "Benchmark Results:" in report
    assert "test" in report


def test_v0350_benchmark_convenience():
    """Test benchmark convenience function."""
    result = benchmark("test", lambda: 1, iterations=5)
    
    assert result.name == "test"
    assert result.iterations == 5


def test_v0350_benchmark_ops_per_second():
    """Test ops_per_second calculation."""
    runner = BenchmarkRunner()
    
    # Simple function that takes negligible time
    result = runner.run("fast", lambda: None, iterations=1000)
    
    # Should have positive ops/sec
    assert result.ops_per_second > 0


# ============== Security Tests ==============

def test_v0350_password_hashing():
    """Test password hashing uses Argon2id or PBKDF2."""
    from core.runtime.auth import PasswordHasher
    
    ph = PasswordHasher()
    
    # Hash a password
    hashed = ph.hash("test_password")
    
    assert hashed is not None
    assert hashed != "test_password"
    
    # Verify
    assert ph.verify("test_password", hashed) is True
    assert ph.verify("wrong_password", hashed) is False


def test_v0350_jwt_token():
    """Test JWT token generation."""
    from core.runtime.auth import JWTManager
    
    jm = JWTManager(secret_key="test-secret")
    
    token = jm.encode({"user_id": "123"}, expires_in=3600)
    
    assert token is not None
    
    # Decode
    payload = jm.decode(token)
    assert payload is not None
    assert payload.get("user_id") == "123"


def test_v0350_csrf_token():
    """Test CSRF token generation."""
    from core.runtime.auth import CSRFProtection
    
    token = CSRFProtection.generate_token()
    
    assert token is not None
    assert CSRFProtection.validate_token(token, token) is True
    assert CSRFProtection.validate_token("invalid", token) is False


def test_v0350_rate_limiter():
    """Test rate limiting."""
    from core.runtime.auth import RateLimiter
    
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    
    # All should be allowed initially
    for i in range(5):
        assert limiter.is_allowed("client-1") is True
    
    # Should be blocked
    assert limiter.is_allowed("client-1") is False
    
    # Different client should be allowed
    assert limiter.is_allowed("client-2") is True


def test_v0350_session_security():
    """Test session security."""
    from core.runtime.auth import SessionManager
    
    sm = SessionManager()
    
    session_id = sm.create_session("user-1", tenant="tenant-1")
    
    assert session_id is not None
    
    # Verify session
    session = sm.get_session(session_id)
    assert session is not None
    assert session["user_id"] == "user-1"
    assert session["tenant"] == "tenant-1"


def test_v0350_secure_headers():
    """Test security headers."""
    from core.runtime.security import SecurityHeaders
    
    headers = SecurityHeaders()
    
    response_headers = headers.get_headers()
    
    assert "X-Content-Type-Options" in response_headers
    assert "X-Frame-Options" in response_headers
    assert "Content-Security-Policy" in response_headers
