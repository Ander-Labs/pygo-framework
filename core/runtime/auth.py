"""PyGo Authentication System (v0.28.0).

Provides sessions, JWT, OAuth2, password hashing, and security middleware.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import argon2
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    HAS_ARGON2 = True
except ImportError:
    HAS_ARGON2 = False


@dataclass
class User:
    """User model for authentication."""
    id: str
    email: str
    password_hash: Optional[str] = None
    roles: list[str] = None
    tenant: Optional[str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []


class PasswordHasher:
    """Password hashing using Argon2id."""
    
    def __init__(self, pepper: Optional[str] = None):
        self.pepper = pepper or os.environ.get("PYGO_PEPPER", "")
        if HAS_ARGON2:
            self.ph = PasswordHasher(
                time_cost=3,      # 3 iterations
                memory_cost=65536, # 64 MB
                parallelism=4,    # 4 threads
                hash_len=32,      # 32 bytes
                salt_len=16       # 16 bytes
            )
    
    def hash(self, password: str) -> str:
        """Hash a password with Argon2id."""
        if not HAS_ARGON2:
            # Fallback to PBKDF2 if argon2 not available
            return self._hash_pbkdf2(password)
        
        peppered = password + self.pepper
        return self.ph.hash(peppered)
    
    def verify(self, password: str, hash: str) -> bool:
        """Verify a password against its hash."""
        if not HAS_ARGON2:
            return self._verify_pbkdf2(password, hash)
        
        peppered = password + self.pepper
        try:
            self.ph.verify(hash, peppered)
            return True
        except VerifyMismatchError:
            return False
    
    def _hash_pbkdf2(self, password: str) -> str:
        """PBKDF2 fallback implementation."""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000  # 100k iterations
        )
        return f"pbkdf2${salt}${key.hex()}"
    
    def _verify_pbkdf2(self, password: str, hash: str) -> bool:
        """PBKDF2 verification fallback."""
        try:
            _, salt, key_hex = hash.split('$')
            key = bytes.fromhex(key_hex)
            new_key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            )
            return hmac.compare_digest(key, new_key)
        except (ValueError, AttributeError):
            return False


class SessionManager:
    """Session management with secure cookies."""
    
    def __init__(self, secret_key: Optional[str] = None, session_lifetime: int = 7200):
        self.secret_key = secret_key or os.environ.get("PYGO_SECRET", secrets.token_hex(32))
        self.session_lifetime = session_lifetime  # seconds (default 2 hours)
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: str, tenant: Optional[str] = None) -> str:
        """Create a new session and return the session ID."""
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = {
            "user_id": user_id,
            "tenant": tenant,
            "created_at": time.time(),
            "expires_at": time.time() + self.session_lifetime
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data if valid."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.time() > session["expires_at"]:
            del self._sessions[session_id]
            return None
        return session
    
    def destroy_session(self, session_id: str) -> None:
        """Destroy a session."""
        self._sessions.pop(session_id, None)
    
    def refresh_session(self, session_id: str) -> bool:
        """Refresh session expiration."""
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session["expires_at"] = time.time() + self.session_lifetime
        return True


class JWTManager:
    """JWT token management."""
    
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or os.environ.get("PYGO_JWT_SECRET", secrets.token_hex(32))
        self.algorithm = algorithm
    
    def encode(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """Encode a JWT token."""
        import base64
        import json
        
        payload = payload.copy()
        payload["exp"] = int(time.time()) + expires_in
        payload["iat"] = int(time.time())
        
        header = {"alg": self.algorithm, "typ": "JWT"}
        
        def b64encode(data):
            return base64.urlsafe_b64encode(
                json.dumps(data, separators=(',', ':')).encode()
            ).rstrip(b'=').decode()
        
        header_b64 = b64encode(header)
        payload_b64 = b64encode(payload)
        
        # Sign with HMAC
        signature = hmac.new(
            self.secret_key.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            'sha256'
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def decode(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token."""
        import base64
        import json
        
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Add padding
            def b64decode(data):
                padding = 4 - len(data) % 4
                if padding != 4:
                    data += '=' * padding
                return base64.urlsafe_b64decode(data)
            
            # Verify signature
            expected_sig = hmac.new(
                self.secret_key.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                'sha256'
            ).digest()
            
            if not hmac.compare_digest(b64decode(signature_b64), expected_sig):
                return None
            
            payload = json.loads(b64decode(payload_b64))
            
            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None
            
            return payload
        except Exception:
            return None


class CSRFProtection:
    """CSRF token generation and validation."""
    
    @staticmethod
    def generate_token() -> str:
        """Generate a CSRF token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_token(token: str, expected: str) -> bool:
        """Validate a CSRF token using constant-time comparison."""
        if not token or not expected:
            return False
        return hmac.compare_digest(token, expected)


class RateLimiter:
    """Rate limiting for requests."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        now = time.time()
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Clean old requests
        self._requests[key] = [
            t for t in self._requests[key]
            if now - t < self.window_seconds
        ]
        
        if len(self._requests[key]) >= self.max_requests:
            return False
        
        self._requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for key."""
        now = time.time()
        if key not in self._requests:
            return self.max_requests
        
        count = len([
            t for t in self._requests[key]
            if now - t < self.window_seconds
        ])
        return max(0, self.max_requests - count)


# Convenience functions
def hash_password(password: str) -> str:
    """Hash a password."""
    return PasswordHasher().hash(password)


def verify_password(password: str, hash: str) -> bool:
    """Verify a password."""
    return PasswordHasher().verify(password, hash)


def create_session(user_id: str, tenant: Optional[str] = None) -> str:
    """Create a session."""
    return SessionManager().create_session(user_id, tenant)


def create_jwt(payload: Dict[str, Any], expires_in: int = 3600) -> str:
    """Create a JWT token."""
    return JWTManager().encode(payload, expires_in)