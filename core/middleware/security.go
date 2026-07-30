package middleware

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"sync"
	"time"
)

// CSRFProtection provides CSRF token generation and validation
type CSRFProtection struct {
	tokens map[string]float64
	mu     sync.RWMutex
	expiry int64 // seconds
}

// NewCSRFProtection creates a new CSRF protection instance
func NewCSRFProtection() *CSRFProtection {
	return &CSRFProtection{
		tokens: make(map[string]float64),
		expiry: 3600, // 1 hour default
	}
}

// GenerateToken creates a CSRF token for a session
func (c *CSRFProtection) GenerateToken(sessionID string) string {
	token := make([]byte, 32)
	rand.Read(token)
	rawToken := hex.EncodeToString(token)
	
	hashInput := fmt.Sprintf("%s:%s", sessionID, rawToken)
	hash := sha256.Sum256([]byte(hashInput))
	tokenHash := hex.EncodeToString(hash[:])[:32]
	
	c.mu.Lock()
	c.tokens[tokenHash] = float64(time.Now().Unix())
	c.mu.Unlock()
	
	return fmt.Sprintf("%s:%s", rawToken, tokenHash)
}

// ValidateToken validates a CSRF token
func (c *CSRFProtection) ValidateToken(token, sessionID string) bool {
	parts := splitToken(token)
	if len(parts) != 2 {
		return false
	}
	
	rawToken, tokenHash := parts[0], parts[1]
	expectedHash := sha256.Sum256([]byte(fmt.Sprintf("%s:%s", sessionID, rawToken)))
	expected := hex.EncodeToString(expectedHash[:])[:32]
	
	if tokenHash != expected {
		return false
	}
	
	c.mu.RLock()
	created, exists := c.tokens[tokenHash]
	c.mu.RUnlock()
	
	if !exists {
		return false
	}
	
	// Check expiry
	if time.Now().Unix()-int64(created) > c.expiry {
		c.mu.Lock()
		delete(c.tokens, tokenHash)
		c.mu.Unlock()
		return false
	}
	
	return true
}

// Cleanup removes expired tokens
func (c *CSRFProtection) Cleanup() {
	c.mu.Lock()
	defer c.mu.Unlock()
	
	now := float64(time.Now().Unix())
	for hash, created := range c.tokens {
		if now-created > float64(c.expiry) {
			delete(c.tokens, hash)
		}
	}
}

// CSRFMiddleware protects endpoints with CSRF validation
func CSRFMiddleware(csrf *CSRFProtection) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Skip GET/HEAD/OPTIONS
			if r.Method == "GET" || r.Method == "HEAD" || r.Method == "OPTIONS" {
				next.ServeHTTP(w, r)
				return
			}
			
			// Validate CSRF token from header or form
			token := r.Header.Get("X-CSRF-Token")
			if token == "" {
				token = r.FormValue("_csrf")
			}
			
			sessionID := getSessionID(r)
			if !csrf.ValidateToken(token, sessionID) {
				http.Error(w, "CSRF token invalid", http.StatusForbidden)
				return
			}
			
			next.ServeHTTP(w, r)
		})
	}
}

// RateLimiter provides rate limiting functionality
type RateLimiter struct {
	clients map[string][]float64
	mu      sync.RWMutex
	limit   int
	window  int64 // seconds
}

// NewRateLimiter creates a new rate limiter
func NewRateLimiter(limit int, window int64) *RateLimiter {
	return &RateLimiter{
		clients: make(map[string][]float64),
		limit:   limit,
		window:  window,
	}
}

// Check validates if request is allowed. Returns (allowed, remaining_after_this_request)
func (r *RateLimiter) Check(key string) (bool, int) {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	now := float64(time.Now().Unix())
	windowStart := now - float64(r.window)
	
	// Clean old requests
	if requests, exists := r.clients[key]; exists {
		clean := make([]float64, 0)
		for _, t := range requests {
			if t > windowStart {
				clean = append(clean, t)
			}
		}
		r.clients[key] = clean
	} else {
		r.clients[key] = make([]float64, 0)
	}
	
	current := len(r.clients[key])
	
	// Check if over limit BEFORE adding this request
	if current >= r.limit {
		return false, 0
	}
	
	// Add this request
	r.clients[key] = append(r.clients[key], now)
	
	// Return remaining after this request
	remaining := r.limit - current - 1
	return true, remaining
}

// Reset clears rate limit for a key
func (r *RateLimiter) Reset(key string) {
	r.mu.Lock()
	delete(r.clients, key)
	r.mu.Unlock()
}

// RateLimitMiddleware applies rate limiting to requests
func RateLimitMiddleware(limiter *RateLimiter, getKey func(*http.Request) string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			key := getKey(r)
			allowed, remaining := limiter.Check(key)
			
			w.Header().Set("X-RateLimit-Remaining", fmt.Sprintf("%d", remaining))
			
			if !allowed {
				http.Error(w, "Rate limit exceeded", http.StatusTooManyRequests)
				return
			}
			
			next.ServeHTTP(w, r)
		})
	}
}

// SecurityHeadersMiddleware adds security headers to responses
func SecurityHeadersMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-XSS-Protection", "1; mode=block")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
		w.Header().Set("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
		w.Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
		
		next.ServeHTTP(w, r)
	})
}

// Helper functions

func splitToken(token string) []string {
	parts := make([]string, 0, 2)
	start := 0
	for i := 0; i < len(token); i++ {
		if token[i] == ':' && i+1 < len(token) && token[i+1] != ':' {
			parts = append(parts, token[start:i])
			start = i + 1
		}
	}
	parts = append(parts, token[start:])
	return parts
}

func getSessionID(r *http.Request) string {
	// Get from cookie, header, or context
	if cookie, err := r.Cookie("session_id"); err == nil {
		return cookie.Value
	}
	return r.Header.Get("X-Session-ID")
}
