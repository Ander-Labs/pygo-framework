package client

import (
	"context"
	"testing"
	"time"
)

// TestV0260ClientCommunication verifies the Go-Python client.
func TestV0260ClientCommunication(t *testing.T) {
	c := NewClient("/tmp/test.sock")

	// Test context extraction (multi-tenancy fix)
	ctx := context.WithValue(context.Background(), "tenant", "acme-corp")
	ctx = context.WithValue(ctx, "user", map[string]interface{}{"id": "123"})

	extracted := extractContext(ctx)
	if extracted["tenant"] != "acme-corp" {
		t.Fatal("tenant not propagated to context")
	}
	if extracted["user"].(map[string]interface{})["id"] != "123" {
		t.Fatal("user not propagated to context")
	}

	t.Logf("Multi-tenancy context propagation OK")

	// Test that client is ready (will fail to connect without Python server)
	ctx2, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	_, err := c.CallPython(ctx2, "test_handler", map[string]interface{}{})
	if err == nil {
		t.Fatal("expected connection error without Python server")
	}

	t.Logf("Client connection test OK: %v", err)
}
