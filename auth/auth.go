// Package auth provides authentication and authorization for PyGo framework.
package auth

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// Session represents a user session.
type Session struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	TenantID  string    `json:"tenant_id,omitempty"`
	Email     string    `json:"email"`
	Role      string    `json:"role"`
	ExpiresAt time.Time `json:"expires_at"`
	CreatedAt time.Time `json:"created_at"`
}

// User represents an authenticated user.
type User struct {
	ID          string    `json:"id"`
	Email       string    `json:"email"`
	Name        string    `json:"name"`
	Role        string    `json:"role"`         // user, admin, superadmin
	TenantID    string    `json:"tenant_id,omitempty"`
	AvatarURL   string    `json:"avatar_url,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
}

// Claims for JWT tokens.
type Claims struct {
	UserID   string `json:"uid"`
	Email    string `json:"email"`
	Role     string `json:"role"`
	TenantID string `json:"tid,omitempty"`
	jwt.RegisteredClaims
}

// Config holds auth configuration.
type Config struct {
	JWTSecret   string
	JWTIssuer   string
	JWTDuration time.Duration
	CookieName  string
	Secure      bool
}

// DefaultConfig returns sensible defaults.
func DefaultConfig() *Config {
	return &Config{
		JWTSecret:   "change-this-in-production",
		JWTIssuer:   "pygo-framework",
		JWTDuration: 24 * time.Hour,
		CookieName:  "pygo_session",
		Secure:      true,
	}
}

// Manager handles authentication and sessions.
type Manager struct {
	cfg    *Config
	store  SessionStore
}

// SessionStore defines session persistence.
type SessionStore interface {
	Save(s *Session) error
	Load(id string) (*Session, error)
	Delete(id string) error
	ClearExpired() error
}

// MemorySessionStore implements SessionStore in-memory.
type MemorySessionStore struct {
	sessions map[string]*Session
}

// NewMemoryStore creates an in-memory session store.
func NewMemoryStore() *MemorySessionStore {
	return &MemorySessionStore{
		sessions: make(map[string]*Session),
	}
}

func (s *MemorySessionStore) Save(sess *Session) error {
	s.sessions[sess.ID] = sess
	return nil
}

func (s *MemorySessionStore) Load(id string) (*Session, error) {
	sess, ok := s.sessions[id]
	if !ok {
		return nil, ErrSessionNotFound
	}
	if time.Now().After(sess.ExpiresAt) {
		delete(s.sessions, id)
		return nil, ErrSessionExpired
	}
	return sess, nil
}

func (s *MemorySessionStore) Delete(id string) error {
	delete(s.sessions, id)
	return nil
}

func (s *MemorySessionStore) ClearExpired() error {
	now := time.Now()
	for id, sess := range s.sessions {
		if now.After(sess.ExpiresAt) {
			delete(s.sessions, id)
		}
	}
	return nil
}

// New creates an auth manager.
func New(cfg *Config) *Manager {
	if cfg == nil {
		cfg = DefaultConfig()
	}
	return &Manager{
		cfg:   cfg,
		store: NewMemoryStore(),
	}
}

// GenerateSessionID creates a cryptographically secure session ID.
func GenerateSessionID() string {
	b := make([]byte, 32)
	rand.Read(b)
	h := sha256.Sum256(b)
	return base64.URLEncoding.EncodeToString(h[:])[:32]
}

// GenerateToken creates a JWT token for a user.
func (m *Manager) GenerateToken(user *User) (string, error) {
	claims := Claims{
		UserID:   user.ID,
		Email:    user.Email,
		Role:     user.Role,
		TenantID: user.TenantID,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(m.cfg.JWTDuration)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    m.cfg.JWTIssuer,
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(m.cfg.JWTSecret))
}

// VerifyToken validates a JWT token.
func (m *Manager) VerifyToken(tokenStr string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenStr, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return []byte(m.cfg.JWTSecret), nil
	})

	if err != nil {
		return nil, err
	}

	if claims, ok := token.Claims.(*Claims); ok && token.Valid {
		return claims, nil
	}
	return nil, ErrInvalidToken
}

// CreateSession creates a new session and sets cookie.
func (m *Manager) CreateSession(w http.ResponseWriter, user *User) (*Session, error) {
	sess := &Session{
		ID:        GenerateSessionID(),
		UserID:    user.ID,
		TenantID:  user.TenantID,
		Email:     user.Email,
		Role:      user.Role,
		ExpiresAt: time.Now().Add(m.cfg.JWTDuration),
		CreatedAt: time.Now(),
	}

	if err := m.store.Save(sess); err != nil {
		return nil, err
	}

	http.SetCookie(w, &http.Cookie{
		Name:     m.cfg.CookieName,
		Value:    sess.ID,
		HttpOnly: true,
		Secure:   m.cfg.Secure,
		SameSite: http.SameSiteLaxMode,
		Expires:  sess.ExpiresAt,
		Path:     "/",
	})

	return sess, nil
}

// GetSessionFromRequest extracts session from request cookie.
func (m *Manager) GetSession(r *http.Request) (*Session, error) {
	cookie, err := r.Cookie(m.cfg.CookieName)
	if err != nil {
		return nil, ErrSessionNotFound
	}
	return m.store.Load(cookie.Value)
}

// DestroySession invalidates a session.
func (m *Manager) DestroySession(w http.ResponseWriter, r *http.Request) error {
	sess, err := m.GetSession(r)
	if err != nil {
		return err
	}
	http.SetCookie(w, &http.Cookie{
		Name:     m.cfg.CookieName,
		Value:    "",
		HttpOnly: true,
		Secure:   m.cfg.Secure,
		Expires:  time.Unix(0, 0),
		Path:     "/",
	})
	return m.store.Delete(sess.ID)
}

// RequireAuth middleware ensures user is authenticated.
func (m *Manager) RequireAuth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, err := m.GetSession(r)
		if err != nil {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// RequireRole middleware ensures user has required role.
func (m *Manager) RequireRole(role string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			sess, err := m.GetSession(r)
			if err != nil {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}
			if sess.Role != role && sess.Role != "superadmin" {
				http.Error(w, "Forbidden", http.StatusForbidden)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// FromContext extracts user from context.
func FromContext(ctx context.Context) (*User, error) {
	u, ok := ctx.Value(UserContextKey).(*User)
	if !ok {
		return nil, ErrSessionNotFound
	}
	return u, nil
}

// UserContextKey for context storage.
type contextKey string

const UserContextKey contextKey = "user"

// Errors
var (
	ErrSessionNotFound = errors.New("session not found")
	ErrSessionExpired  = errors.New("session expired")
	ErrInvalidToken    = errors.New("invalid token")
)

// OAuthURL generates OAuth provider auth URL.
func OAuthURL(provider, clientID, redirectURI string) string {
	base := map[string]string{
		"github":  "https://github.com/login/oauth/authorize",
		"google":  "https://accounts.google.com/o/oauth2/v2/auth",
		"microsoft": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
	}
	url, ok := base[provider]
	if !ok {
		return ""
	}
	return fmt.Sprintf("%s?client_id=%s&redirect_uri=%s&scope=read:user", url, clientID, redirectURI)
}
