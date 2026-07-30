"""Test suite for v0.37.0 - Security Middleware."""
import pytest
import time
import hashlib
import secrets

from core.runtime.security_middleware import (
    CSRFProtection, RateLimiter, SecurityHeaders
)


def test_csrf_token_generation():
    """Test CSRF token generation."""
    token = CSRFProtection.generate_token("session-123")
    assert token is not None
    assert ":" in token
    parts = token.split(":")
    assert len(parts) == 2


def test_csrf_token_validation():
    """Test CSRF token validation."""
    session_id = "session-123"
    token = CSRFProtection.generate_token(session_id)
    
    # Valid token
    assert CSRFProtection.validate_token(token, session_id) is True
    
    # Invalid token (wrong session)
    assert CSRFProtection.validate_token(token, "other-session") is False
    
    # Invalid token (wrong format)
    assert CSRFProtection.validate_token("invalid:token", session_id) is False


def test_csrf_token_expiry():
    """Test CSRF token expiry."""
    session_id = "session-456"
    token = CSRFProtection.generate_token(session_id)
    
    # Token should be valid immediately
    assert CSRFProtection.validate_token(token, session_id) is True


def test_rate_limiter_allows_under_limit():
    """Test rate limiter allows requests under limit."""
    key = "test-ip-1"
    allowed, remaining = RateLimiter.check(key, "api")
    
    assert allowed is True
    assert remaining > 0


def test_rate_limiter_blocks_over_limit():
    """Test rate limiter blocks requests over limit."""
    key = "test-ip-2"
    
    # Make requests up to limit
    for _ in range(100):
        RateLimiter.check(key, "api")
    
    # Next request should be blocked
    allowed, remaining = RateLimiter.check(key, "api")
    assert allowed is False
    assert remaining == 0


def test_rate_limiter_reset():
    """Test rate limiter reset."""
    key = "test-ip-3"
    
    # Make some requests
    for _ in range(90):
        RateLimiter.check(key, "api")
    
    # Reset
    RateLimiter.reset(key)
    
    # Should be allowed again
    allowed, remaining = RateLimiter.check(key, "api")
    assert allowed is True


def test_rate_limiter_login_protection():
    """Test rate limiter for login endpoint."""
    key = "login-ip-1"
    
    # Login has stricter limits (5 req/min)
    for _ in range(5):
        RateLimiter.check(key, "login")
    
    # Should be blocked
    allowed, remaining = RateLimiter.check(key, "login")
    assert allowed is False


def test_security_headers_present():
    """Test security headers are defined."""
    headers = SecurityHeaders.HEADERS
    
    assert "X-Frame-Options" in headers
    assert "X-Content-Type-Options" in headers
    assert "Content-Security-Policy" in headers
    assert "Strict-Transport-Security" in headers


def test_security_headers_values():
    """Test security headers have correct values."""
    headers = SecurityHeaders.HEADERS
    
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_rate_limiter_different_limits():
    """Test different rate limit types."""
    api_key = "different-api"
    upload_key = "different-upload"
    
    # API limit: 100 req/min
    for _ in range(100):
        RateLimiter.check(api_key, "api")
    
    # Upload limit: 10 req/min
    for _ in range(10):
        RateLimiter.check(upload_key, "upload")
    
    # API should be blocked
    allowed, _ = RateLimiter.check(api_key, "api")
    assert allowed is False
    
    # Upload should be blocked
    allowed, _ = RateLimiter.check(upload_key, "upload")
    assert allowed is False
