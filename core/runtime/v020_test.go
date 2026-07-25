package runtime

import (
	"io"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestV020HTMX starts the native net/http Server (which launches Python via the
// supervisor), serves the /hello/:name route with an HTMX fragment, and asserts
// the rendered HTML contains the name. The server is torn down at the end.
func TestV020HTMX(t *testing.T) {
	repoRoot, err := repoRoot()
	if err != nil {
		t.Fatalf("repo root: %v", err)
	}
	appDir := filepath.Join(repoRoot, "examples", "hello-world")
	if _, err := os.Stat(filepath.Join(appDir, "app_poc.py")); err != nil {
		t.Fatalf("app_poc.py missing (run transpiler first): %v", err)
	}
	if _, err := os.Stat(filepath.Join(appDir, "hello.html")); err != nil {
		t.Fatalf("hello.html missing: %v", err)
	}

	if err := os.Setenv("PYTHONPATH", repoRoot); err != nil {
		t.Fatal(err)
	}
	if err := os.Setenv("PYGO_SOCKET", filepath.Join(t.TempDir(), "pygo.sock")); err != nil {
		t.Fatal(err)
	}

	const addr = "127.0.0.1:18080"
	server := NewServer(addr, filepath.Join(appDir, "app_poc.py"))
	frag, err := os.ReadFile(filepath.Join(appDir, "hello.html"))
	if err != nil {
		t.Fatal(err)
	}
	server.Router().RegisterView("GET", "/hello/:name", string(frag))
	server.Router().Handle("GET", "/hello/:name", func(args map[string]any) (any, error) {
		name, _ := args["name"].(string)
		return CallPython("hello", map[string]any{"name": name})
	}, false)

	go func() {
		_ = server.Start()
	}()

	// Wait for the server to come up.
	url := "http://" + addr + "/hello/Anders"
	client := &http.Client{Timeout: 5 * time.Second}
	var body string
	for i := 0; i < 50; i++ {
		resp, err := client.Get(url)
		if err == nil {
			b, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			body = string(b)
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
	defer server.Stop()

	if body == "" {
		t.Fatal("server did not respond")
	}
	if !contains(body, "Anders") {
		t.Fatalf("expected HTML fragment to contain 'Anders', got: %s", body)
	}
	t.Logf("v0.2.0 OK: %s", body)
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (s == sub || indexOf(s, sub) >= 0)
}

func indexOf(s, sub string) int {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}
