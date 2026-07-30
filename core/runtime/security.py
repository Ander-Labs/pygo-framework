"""PyGo Security Utilities (v0.35.0).

Provides security helpers for input validation and headers.
"""

from __future__ import annotations

import re
import html
from typing import Dict, Any, Optional


def validate_input(value: str, max_length: int = 1000) -> str:
    """Validate and sanitize input to prevent injection attacks."""
    if not value:
        return value
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Remove dangerous characters for SQL injection
    value = re.sub(r"[';\"\\--]", "", value)
    
    # HTML escape for XSS prevention
    value = html.escape(value)
    
    return value


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    def __init__(self):
        self._headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
    
    def get_headers(self) -> Dict[str, str]:
        """Get security headers."""
        return dict(self._headers)
    
    def add_header(self, name: str, value: str) -> None:
        """Add a custom security header."""
        self._headers[name] = value
    
    def remove_header(self, name: str) -> None:
        """Remove a security header."""
        if name in self._headers:
            del self._headers[name]