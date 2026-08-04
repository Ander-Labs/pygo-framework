package cache

import (
	"context"
	"testing"
	"time"
)

func TestMemoryCache(t *testing.T) {
	c := NewMemoryCache()
	ctx := context.Background()

	// Test Set
	if err := c.Set(ctx, "key1", "value1", time.Minute); err != nil {
		t.Fatalf("Set failed: %v", err)
	}

	// Test Get
	val, err := c.Get(ctx, "key1")
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	if val != "value1" {
		t.Errorf("Get = %q, want %q", val, "value1")
	}

	// Test Has
	has, _ := c.Has(ctx, "key1")
	if !has {
		t.Error("Has should return true")
	}

	// Test Get miss
	_, err = c.Get(ctx, "nonexistent")
	if err == nil {
		t.Error("Get on missing key should return error")
	}

	// Test Delete
	c.Delete(ctx, "key1")
	_, err = c.Get(ctx, "key1")
	if err == nil {
		t.Error("Get after Delete should fail")
	}

	// Test Clear
	c.Set(ctx, "key2", "value2", time.Minute)
	c.Clear(ctx)

	// Verify all keys gone
	_, err = c.Get(ctx, "key2")
	if err == nil {
		t.Error("Should not retrieve key after Clear")
	}
}

func TestMemoryCacheExpiry(t *testing.T) {
	c := NewMemoryCache()
	ctx := context.Background()

	// Set with very short TTL
	c.Set(ctx, "temp", "value", 10*time.Millisecond)
	time.Sleep(20 * time.Millisecond)

	_, err := c.Get(ctx, "temp")
	if err == nil {
		t.Error("Expired key should not be retrievable")
	}
}
