"""PyGo Security Middleware (v0.37.0).

Provides CSRF protection, rate limiting, and security headers.
"""

from __future__ import annotations

import secrets
import time
import hashlib
from typing import Optional, Dict, Any, Callable
from functools import wraps

# CSRF token storage (in production, use Redis)
_csrf_tokens: Dict[str, float] = {}

# Rate limit storage (in production, use Redis)
_rate_limits: Dict[str, list] = {}


class CSRFProtection:
    """CSRF token generation and validation."""
    
    TOKEN_EXPIRY = 3600  # 1 hour
    
    @classmethod
    def generate_token(cls, session_id: str) -> str:
        """Generate a CSRF token for a session."""
        token = secrets.token_urlsafe(32)
        hash_input = f"{session_id}:{token}"
        token_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:32]
        _csrf_tokens[token_hash] = time.time()
        return f"{token}:{token_hash}"
    
    @classmethod
    def validate_token(cls, token: str, session_id: str) -> bool:
        """Validate a CSRF token."""
        try:
            parts = token.split(":")
            if len(parts) != 2:
                return False
            
            raw_token, token_hash = parts
            expected_hash = hashlib.sha256(
                f"{session_id}:{raw_token}".encode()
            ).hexdigest()[:32]
            
            if not secrets.compare_digest(token_hash, expected_hash):
                return False
            
            # Check expiry
            created = _csrf_tokens.get(token_hash, 0)
            if time.time() - created > cls.TOKEN_EXPIRY:
                del _csrf_tokens[token_hash]
                return False
            
            return True
        except Exception:
            return False
    
    @classmethod
    def cleanup_expired(cls) -> None:
        """Remove expired tokens."""
        now = time.time()
        expired = [k for k, v in _csrf_tokens.items() 
                   if now - v > cls.TOKEN_EXPIRY]
        for k in expired:
            del _csrf_tokens[k]


class RateLimiter:
    """Rate limiting with configurable limits."""
    
    DEFAULT_LIMITS = {
        "api": {"requests": 100, "window": 60},      # 100 req/min
        "login": {"requests": 5, "window": 60},       # 5 attempts/min
        "upload": {"requests": 10, "window": 60},     # 10 uploads/min
    }
    
    @classmethod
    def check(cls, key: str, limit_type: str = "api") -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, remaining)."""
        limits = cls.DEFAULT_LIMITS.get(limit_type, cls.DEFAULT_LIMITS["api"])
        max_requests = limits["requests"]
        window = limits["window"]
        
        now = time.time()
        window_start = now - window
        
        # Get or create request history
        if key not in _rate_limits:
            _rate_limits[key] = []
        
        # Remove old requests outside window
        _rate_limits[key] = [t for t in _rate_limits[key] if t > window_start]
        
        # Check limit
        current = len(_rate_limits[key])
        remaining = max(0, max_requests - current)
        
        if current >= max_requests:
            return False, 0
        
        _rate_limits[key].append(now)
        return True, remaining
    
    @classmethod
    def reset(cls, key: str) -> None:
        """Reset rate limit for a key."""
        _rate_limits.pop(key, None)


class SecurityHeaders:
    """Security headers middleware."""
    
    HEADERS = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }
    
    @classmethod
    def apply_headers(cls, response) -> None:
        """Apply security headers to response."""
        for header, value in cls.HEADERS.items():
            response.headers[header] = value