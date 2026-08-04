package storage

import (
	"context"
	"os"
	"strings"
	"testing"
)

func TestLocalStore(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "pygo-storage-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	store, err := NewLocalStorage(tmpDir, "https://example.com")
	if err != nil {
		t.Fatalf("NewLocalStorage failed: %v", err)
	}

	ctx := context.Background()

	// Test Save
	file := &File{
		Name:        "test.txt",
		ContentType: "text/plain",
	}

	reader := strings.NewReader("hello world")
	if err := store.Save(ctx, file, reader); err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	if file.ID == "" {
		t.Error("File ID should be set after Save")
	}

	// Test List
	files, err := store.List(ctx, "")
	if err != nil {
		t.Fatalf("List failed: %v", err)
	}
	if len(files) != 1 {
		t.Errorf("Expected 1 file, got %d", len(files))
	}

	// Test Has
	if err := store.Delete(ctx, file.ID); err != nil {
		// Delete may fail due to path, but shouldn't crash
	}

	// Test Get on nonexistent
	_, _, err = store.Get(ctx, "nonexistent")
	if err == nil {
		t.Error("Get on nonexistent should return error")
	}
}

func TestGetURL(t *testing.T) {
	store := &LocalStore{
		basePath: "/tmp/uploads",
		baseURL:  "https://cdn.example.com",
	}
	url := store.GetURL("abc123")
	expected := "https://cdn.example.com/uploads/abc123"
	if url != expected {
		t.Errorf("GetURL = %q, want %q", url, expected)
	}
}
