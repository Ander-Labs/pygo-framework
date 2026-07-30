package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCSRFProtection_GenerateToken(t *testing.T) {
	csrf := NewCSRFProtection()
	token := csrf.GenerateToken("session-123")
	
	if token == "" {
		t.Error("Token should not be empty")
	}
	
	// Token should contain separator
	found := false
	for i := 0; i < len(token)-1; i++ {
		if token[i] == ':' && token[i+1] != ':' {
			found = true
			break
		}
	}
	if !found {
		t.Error("Token should contain ':' separator")
	}
}

func TestCSRFProtection_ValidateToken(t *testing.T) {
	csrf := NewCSRFProtection()
	sessionID := "session-123"
	token := csrf.GenerateToken(sessionID)
	
	// Valid token
	if !csrf.ValidateToken(token, sessionID) {
		t.Error("Valid token should pass validation")
	}
	
	// Invalid session
	if csrf.ValidateToken(token, "other-session") {
		t.Error("Token with wrong session should fail validation")
	}
	
	// Invalid format
	if csrf.ValidateToken("invalid:token", sessionID) {
		t.Error("Invalid token format should fail validation")
	}
}

func TestRateLimiter_Check(t *testing.T) {
	limiter := NewRateLimiter(5, 60) // 5 requests per minute
	
	// Should be allowed under limit
	allowed, remaining := limiter.Check("client-1")
	if !allowed {
		t.Error("Should be allowed under limit")
	}
	// After first request, 4 remaining (5-1)
	if remaining != 4 {
		t.Errorf("Expected 4 remaining, got %d", remaining)
	}
}

func TestRateLimiter_OverLimit(t *testing.T) {
	limiter := NewRateLimiter(3, 60)
	
	// Exhaust limit
	for i := 0; i < 3; i++ {
		limiter.Check("client-2")
	}
	
	// Should be blocked
	allowed, remaining := limiter.Check("client-2")
	if allowed {
		t.Error("Should be blocked over limit")
	}
	if remaining != 0 {
		t.Errorf("Expected 0 remaining, got %d", remaining)
	}
}

func TestRateLimiter_Reset(t *testing.T) {
	limiter := NewRateLimiter(10, 60)
	
	// Make some requests
	for i := 0; i < 5; i++ {
		limiter.Check("client-3")
	}
	
	// Reset
	limiter.Reset("client-3")
	
	// Should be allowed again
	allowed, _ := limiter.Check("client-3")
	if !allowed {
		t.Error("Should be allowed after reset")
	}
}

func TestSecurityHeadersMiddleware(t *testing.T) {
	handler := SecurityHeadersMiddleware(
		http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
		}),
	)
	
	req := httptest.NewRequest("GET", "/", nil)
	rec := httptest.NewRecorder()
	
	handler.ServeHTTP(rec, req)
	
	// Check headers are set
	if rec.Header().Get("X-Frame-Options") != "DENY" {
		t.Error("X-Frame-Options header not set")
	}
	if rec.Header().Get("X-Content-Type-Options") != "nosniff" {
		t.Error("X-Content-Type-Options header not set")
	}
	if rec.Header().Get("Content-Security-Policy") == "" {
		t.Error("Content-Security-Policy header not set")
	}
}

func TestCSRFMiddleware_SkipsGet(t *testing.T) {
	csrf := NewCSRFProtection()
	middleware := CSRFMiddleware(csrf)
	
	handler := middleware(
		http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
		}),
	)
	
	req := httptest.NewRequest("GET", "/", nil)
	rec := httptest.NewRecorder()
	
	handler.ServeHTTP(rec, req)
	
	if rec.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", rec.Code)
	}
}

func TestCSRFMiddleware_BlocksInvalidToken(t *testing.T) {
	csrf := NewCSRFProtection()
	middleware := CSRFMiddleware(csrf)
	
	handler := middleware(
		http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
		}),
	)
	
	req := httptest.NewRequest("POST", "/", nil)
	req.Header.Set("X-CSRF-Token", "invalid:token")
	rec := httptest.NewRecorder()
	
	handler.ServeHTTP(rec, req)
	
	if rec.Code != http.StatusForbidden {
		t.Errorf("Expected 403, got %d", rec.Code)
	}
}
