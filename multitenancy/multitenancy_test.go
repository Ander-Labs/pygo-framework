package multitenancy

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestStore(t *testing.T) {
	store := NewStore()

	tenant := &Tenant{
		ID:   "acme",
		Name: "Acme Corp",
		Slug: "acme",
		Plan: "pro",
	}

	// Test Register
	if err := store.Register(tenant); err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	// Test duplicate
	err := store.Register(tenant)
	if err == nil {
		t.Error("Should fail on duplicate")
	}

	// Test Get
	got, err := store.Get("acme")
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	if got.Name != "Acme Corp" {
		t.Errorf("Name = %q", got.Name)
	}

	// Test GetBySlug
	got2, err := store.GetBySlug("acme")
	if err != nil {
		t.Fatalf("GetBySlug failed: %v", err)
	}
	if got2 != tenant {
		t.Error("GetBySlug should return same tenant")
	}

	// Test Get not found
	_, err = store.Get("nonexistent")
	if err == nil {
		t.Error("Should fail on missing tenant")
	}

	// Test List
	tenants := store.List()
	if len(tenants) != 1 {
		t.Errorf("List count = %d, want 1", len(tenants))
	}

	// Test Delete
	if err := store.Delete("acme"); err != nil {
		t.Errorf("Delete failed: %v", err)
	}
	_, err = store.Get("acme")
	if err == nil {
		t.Error("Should not find deleted tenant")
	}
}

func TestContext(t *testing.T) {
	tenant := &Tenant{ID: "t1", Slug: "test"}
	ctx := WithTenant(context.Background(), tenant)

	got, err := FromContext(ctx)
	if err != nil {
		t.Fatalf("FromContext failed: %v", err)
	}
	if got.ID != "t1" {
		t.Errorf("ID = %q, want t1", got.ID)
	}

	_, err = FromContext(context.Background())
	if err == nil {
		t.Error("Should fail with no tenant in context")
	}
}

func TestMiddleware(t *testing.T) {
	store := NewStore()
	tenant := &Tenant{ID: "acme", Slug: "acme", Name: "Acme"}
	store.Register(tenant)

	mw := Middleware(store)

	handler := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		t, err := FromContext(ctx)
		if err != nil {
			http.Error(w, "no tenant", http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(t.ID))
	}))

	req := httptest.NewRequest("GET", "/", nil)
	req.Header.Set("X-Tenant-ID", "acme")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("Status = %d, want 200", rr.Code)
	}
	if rr.Body.String() != "acme" {
		t.Errorf("Body = %q, want acme", rr.Body.String())
	}
}

func TestProvision(t *testing.T) {
	store := NewStore()
	_, err := Provision(store, "Acme Corp", "acme", "pro")
	if err != nil {
		t.Fatalf("Provision failed: %v", err)
	}

	got, err := store.GetBySlug("acme")
	if err != nil {
		t.Fatal(err)
	}

	if got.Name != "Acme Corp" {
		t.Errorf("Name = %q", got.Name)
	}
	if got.Plan != "pro" {
		t.Errorf("Plan = %q", got.Plan)
	}
	if got.DBSchema != "tenant_acme" {
		t.Errorf("DBSchema = %q", got.DBSchema)
	}
}
