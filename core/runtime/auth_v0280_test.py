"""Test suite for v0.28.0 - Authentication and Security."""
import pytest
import time
import os

from core.runtime.auth import (
    PasswordHasher, SessionManager, JWTManager,
    CSRFProtection, RateLimiter,
    hash_password, verify_password, create_session, create_jwt
)


def test_v0280_password_hasher_pbkdf2():
    """Test PBKDF2 password hashing (fallback)."""
    ph = PasswordHasher(pepper="test-pepper")
    
    password = "my-secret-password"
    hashed = ph.hash(password)
    
    assert hashed.startswith("pbkdf2$")
    assert ph.verify(password, hashed)
    assert not ph.verify("wrong-password", hashed)


def test_v0280_session_manager():
    """Test session management."""
    sm = SessionManager(secret_key="test-secret", session_lifetime=3600)
    
    # Create session
    session_id = sm.create_session("user-123", tenant="acme")
    assert session_id is not None
    assert len(session_id) > 20
    
    # Get session
    session = sm.get_session(session_id)
    assert session is not None
    assert session["user_id"] == "user-123"
    assert session["tenant"] == "acme"
    
    # Destroy session
    sm.destroy_session(session_id)
    assert sm.get_session(session_id) is None


def test_v0280_session_expiry():
    """Test session expiry."""
    sm = SessionManager(secret_key="test-secret", session_lifetime=1)  # 1 second
    
    session_id = sm.create_session("user-123")
    time.sleep(2)
    
    session = sm.get_session(session_id)
    assert session is None  # Expired


def test_v0280_jwt_manager():
    """Test JWT token creation and verification."""
    jm = JWTManager(secret_key="test-secret")
    
    payload = {"user_id": "user-123", "tenant": "acme"}
    token = jm.encode(payload, expires_in=3600)
    
    assert token is not None
    assert "." in token
    
    decoded = jm.decode(token)
    assert decoded is not None
    assert decoded["user_id"] == "user-123"
    assert decoded["tenant"] == "acme"


def test_v0280_jwt_expiry():
    """Test JWT token expiry."""
    jm = JWTManager(secret_key="test-secret")
    
    payload = {"user_id": "user-123"}
    token = jm.encode(payload, expires_in=1)
    
    time.sleep(2)
    decoded = jm.decode(token)
    assert decoded is None  # Expired


def test_v0280_jwt_tampering():
    """Test JWT tampering detection."""
    jm = JWTManager(secret_key="test-secret")
    
    payload = {"user_id": "user-123"}
    token = jm.encode(payload)
    
    # Tamper with signature (change last character)
    parts = token.split('.')
    tampered_sig = parts[2][:-1] + ('a' if parts[2][-1] != 'a' else 'b')
    tampered = f"{parts[0]}.{parts[1]}.{tampered_sig}"
    
    decoded = jm.decode(tampered)
    assert decoded is None  # Tampering detected


def test_v0280_csrf_protection():
    """Test CSRF token generation and validation."""
    token = CSRFProtection.generate_token()
    
    assert token is not None
    assert len(token) > 20
    assert CSRFProtection.validate_token(token, token)
    assert not CSRFProtection.validate_token(token, "wrong")


def test_v0280_rate_limiter():
    """Test rate limiting."""
    rl = RateLimiter(max_requests=3, window_seconds=10)
    
    # First 3 requests allowed
    assert rl.is_allowed("client-1")
    assert rl.is_allowed("client-1")
    assert rl.is_allowed("client-1")
    
    # 4th request blocked
    assert not rl.is_allowed("client-1")
    
    # Different client allowed
    assert rl.is_allowed("client-2")


def test_v0280_convenience_functions():
    """Test convenience functions."""
    # hash_password
    hashed = hash_password("test-password")
    assert hashed is not None
    
    # verify_password
    assert verify_password("test-password", hashed)
    assert not verify_password("wrong", hashed)
    
    # create_session
    session_id = create_session("user-1", tenant="test")
    assert session_id is not None
    
    # create_jwt
    token = create_jwt({"user_id": "user-1"})
    assert token is not None
