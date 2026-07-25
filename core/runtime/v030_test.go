package runtime

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"
)

// TestV030ORM starts the native server, creates a Customer via the create
// handler (query params) and reads it back via get_customer, asserting the
// SQLite row persisted end-to-end through the Python ORM.
func TestV030ORM(t *testing.T) {
	repoRoot, err := repoRoot()
	if err != nil {
		t.Fatalf("repo root: %v", err)
	}
	appDir := filepath.Join(repoRoot, "examples", "hello-world")
	appPath := filepath.Join(appDir, "app_poc.py")
	if _, err := os.Stat(appPath); err != nil {
		t.Fatalf("app_poc.py missing: %v", err)
	}

	if err := os.Setenv("PYTHONPATH", repoRoot); err != nil {
		t.Fatal(err)
	}
	if err := os.Setenv("PYGO_SOCKET", filepath.Join(t.TempDir(), "pygo.sock")); err != nil {
		t.Fatal(err)
	}
	// Use an isolated DB for the test.
	dbPath := filepath.Join(t.TempDir(), "pygo_test.db")
	if err := os.Setenv("PYGO_DB", dbPath); err != nil {
		t.Fatal(err)
	}

	const addr = "127.0.0.1:18081"
	server := NewServer(addr, appPath)
	server.Router().Handle("POST", "/customers", func(args map[string]any) (any, error) {
		return CallPython("create_customer", args)
	}, false)
	server.Router().Handle("GET", "/customers/:id", func(args map[string]any) (any, error) {
		id, _ := args["id"].(string)
		return CallPython("get_customer", map[string]any{"id": id})
	}, false)

	go func() { _ = server.Start() }()
	defer server.Stop()

	base := "http://" + addr
	client := &http.Client{Timeout: 5 * time.Second}
	waitFor(t, base+"/customers/1", client)

	// Create.
	createURL := base + "/customers?name=Maria&email=maria@example.com"
	resp, err := client.Post(createURL, "application/x-www-form-urlencoded", nil)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	b, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	var created map[string]any
	if err := json.Unmarshal(b, &created); err != nil {
		t.Fatalf("create body not json: %s", b)
	}
	t.Logf("v0.3.0 raw body: %s", b)
	if created["name"] != "Maria" {
		t.Fatalf("expected name=Maria, got %v", created["name"])
	}
	idVal, ok := created["id"]
	if !ok || idVal == nil {
		t.Fatalf("expected an id, got %v", created)
	}
	id := toString(idVal)

	// Read back by id.
	getURL := base + "/customers/" + id
	resp2, err := client.Get(getURL)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	b2, _ := io.ReadAll(resp2.Body)
	resp2.Body.Close()
	var got map[string]any
	if err := json.Unmarshal(b2, &got); err != nil {
		t.Fatalf("get body not json: %s", b2)
	}
	if got["email"] != "maria@example.com" {
		t.Fatalf("expected email persisted, got %v", got["email"])
	}
	t.Logf("v0.3.0 OK: created=%v got=%v", created, got)
}

func waitFor(t *testing.T, url string, client *http.Client) {
	for i := 0; i < 50; i++ {
		if resp, err := client.Get(url); err == nil {
			resp.Body.Close()
			return
		}
		time.Sleep(100 * time.Millisecond)
	}
}

func toString(v any) string {
	switch x := v.(type) {
	case string:
		return x
	case float64:
		// SQLite rowid comes back as float64; render as integer string.
		if x == float64(int64(x)) {
			return strconv.FormatInt(int64(x), 10)
		}
		return strconv.FormatFloat(x, 'f', -1, 64)
	default:
		return ""
	}
}
