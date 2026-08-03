// Package multitenancy provides multi-tenant support for PyGo framework.
package multitenancy

import (
	"context"
	"net/http"
	"sync"
	"time"
)

// Tenant represents an isolated customer in the system.
type Tenant struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Slug      string    `json:"slug"`
	Plan      string    `json:"plan"`       // free, pro, enterprise
	DBSchema  string    `json:"db_schema"`   // PostgreSQL schema name
	Settings  Settings  `json:"settings"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Settings holds tenant-specific configuration.
type Settings map[string]interface{}

// ContextKey is used for context values.
type ContextKey string

const TenantKey ContextKey = "tenant"

// Store holds tenant registry in-memory (for development).
type Store struct {
	mu       sync.RWMutex
	tenants  map[string]*Tenant
	bySlug   map[string]*Tenant
}

// NewStore creates a new tenant store.
func NewStore() *Store {
	return &Store{
		tenants: make(map[string]*Tenant),
		bySlug:  make(map[string]*Tenant),
	}
}

// Register registers a new tenant.
func (s *Store) Register(t *Tenant) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.tenants[t.ID]; exists {
		return ErrTenantExists
	}
	if _, exists := s.bySlug[t.Slug]; exists {
		return ErrTenantExists
	}
	t.CreatedAt = time.Now()
	t.UpdatedAt = time.Now()
	s.tenants[t.ID] = t
	s.bySlug[t.Slug] = t
	return nil
}

// Get retrieves a tenant by ID.
func (s *Store) Get(id string) (*Tenant, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	t, ok := s.tenants[id]
	if !ok {
		return nil, ErrTenantNotFound
	}
	return t, nil
}

// GetBySlug retrieves a tenant by slug.
func (s *Store) GetBySlug(slug string) (*Tenant, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	t, ok := s.bySlug[slug]
	if !ok {
		return nil, ErrTenantNotFound
	}
	return t, nil
}

// List returns all tenants.
func (s *Store) List() []*Tenant {
	s.mu.RLock()
	defer s.mu.RUnlock()
	tenants := make([]*Tenant, 0, len(s.tenants))
	for _, t := range s.tenants {
		tenants = append(tenants, t)
	}
	return tenants
}

// Delete removes a tenant.
func (s *Store) Delete(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	t, ok := s.tenants[id]
	if !ok {
		return ErrTenantNotFound
	}
	delete(s.tenants, id)
	delete(s.bySlug, t.Slug)
	return nil
}

// DefaultStore is the default tenant store instance.
var DefaultStore = NewStore()

// FromContext extracts tenant from context.
func FromContext(ctx context.Context) (*Tenant, error) {
	t, ok := ctx.Value(TenantKey).(*Tenant)
	if !ok || t == nil {
		return nil, ErrNoTenantInContext
	}
	return t, nil
}

// WithTenant puts tenant into context.
func WithTenant(ctx context.Context, t *Tenant) context.Context {
	return context.WithValue(ctx, TenantKey, t)
}

// Middleware detects and injects tenant into request context.
// Detects tenant via subdomain (e.g., acme.myapp.com) or API key.
func Middleware(store *Store) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			tenant := detectTenant(store, r)
			if tenant != nil {
				ctx := WithTenant(r.Context(), tenant)
				r = r.WithContext(ctx)
			}
			next.ServeHTTP(w, r)
		})
	}
}

// detectTenant identifies tenant from request.
func detectTenant(store *Store, r *http.Request) *Tenant {
	// 1. Check subdomaint
	host := r.Host
	if host != "" {
		parts := splitHost(host)
		if len(parts) > 0 {
			if tenant, err := store.GetBySlug(parts[0]); err == nil {
				return tenant
			}
		}
	}

	// 2. Check API key header
	apiKey := r.Header.Get("X-API-Key")
	if apiKey != "" {
		// In production, look up tenant by API key
		return nil
	}

	// 3. Check custom header
	tenantID := r.Header.Get("X-Tenant-ID")
	if tenantID != "" {
		if tenant, err := store.Get(tenantID); err == nil {
			return tenant
		}
	}

	// 4. Check path prefix (e.g., /acme/dashboard)
	pathParts := splitPath(r.URL.Path)
	if len(pathParts) > 0 {
		if tenant, err := store.GetBySlug(pathParts[0]); err == nil {
			return tenant
		}
	}

	return nil
}

func splitHost(host string) []string {
	// Remove port if present
	if idx := indexOf(host, ":"); idx > 0 {
		host = host[:idx]
	}
	return splitString(host, ".")
}

func splitPath(path string) []string {
	path = trimString(path, "/")
	return splitString(path, "/")
}

// Provision creates a new tenant with isolated settings.
func Provision(store *Store, name, slug, plan string) (*Tenant, error) {
	t := &Tenant{
		ID:       slug,
		Name:     name,
		Slug:     slug,
		Plan:     plan,
		DBSchema: "tenant_" + slug,
		Settings: Settings{},
	}
	return t, store.Register(t)
}

// QueryScope returns tenant-specific query modifications.
// In production, add WHERE clause for tenant_id or use schema.
func QueryScope(tenant *Tenant) (string, string) {
	return "tenant_id", tenant.ID
}

// Errors
var (
	ErrTenantExists       = ErrTenant("tenant already exists")
	ErrTenantNotFound     = ErrTenant("tenant not found")
	ErrNoTenantInContext  = ErrTenant("no tenant in context")
)

type ErrTenant string

func (e ErrTenant) Error() string { return string(e) }

func indexOf(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

func splitString(s, sep string) []string {
	var result []string
	start := 0
	for i := 0; i <= len(s)-len(sep); i++ {
		if s[i:i+len(sep)] == sep {
			result = append(result, s[start:i])
			start = i + len(sep)
		}
	}
	result = append(result, s[start:])
	return result
}

func trimString(s, cut string) string {
	for hasPrefix(s, cut) {
		s = s[len(cut):]
	}
	for hasSuffix(s, cut) {
		s = s[:len(s)-len(cut)]
	}
	return s
}

func hasPrefix(s, prefix string) bool {
	return len(s) >= len(prefix) && s[:len(prefix)] == prefix
}

func hasSuffix(s, suffix string) bool {
	return len(s) >= len(suffix) && s[len(s)-len(suffix):] == suffix
}
