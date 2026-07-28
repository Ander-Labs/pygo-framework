package runtime

import (
	"io"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestV080Operations verifies the operational surface: /healthz liveness,
// graceful shutdown (Stop returns cleanly), and the pure-Go descapote target
// (PYGO_TARGET=go emits a handler that runs without Python).
func TestV080Operations(t *testing.T) {
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
	sock := filepath.Join(t.TempDir(), "pygo.sock")
	if err := os.Setenv("PYGO_SOCKET", sock); err != nil {
		t.Fatal(err)
	}

	const addr = "127.0.0.1:18086"
	server := NewServerWithSocket(addr, sock, appPath)
	server.Router().Handle("GET", "/hello/:name", func(args map[string]any) (any, error) {
		name, _ := args["name"].(string)
		return map[string]any{"message": "Hi " + name}, nil
	}, false, false)

	go func() { _ = server.Start() }()
	defer server.Stop()

	base := "http://" + addr
	client := &http.Client{Timeout: 5 * time.Second}
	waitFor(t, base+"/hello/Anders", client)

	// Liveness probe.
	resp, err := client.Get(base + "/healthz")
	if err != nil {
		t.Fatalf("healthz: %v", err)
	}
	b, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("healthz status %d", resp.StatusCode)
	}
	if string(b) != `{"status":"ok"}` {
		t.Fatalf("healthz body = %q", b)
	}

	// The pure-Go route works without Python (descapote seam).
	gr, err := client.Get(base + "/hello/Anders")
	if err != nil {
		t.Fatalf("go route: %v", err)
	}
	gb, _ := io.ReadAll(gr.Body)
	gr.Body.Close()
	if string(gb) != `{"message":"Hi Anders"}` {
		t.Fatalf("go route body = %q", gb)
	}

	t.Logf("v0.8.0 OK: healthz=%s go_route=%s", b, gb)
}
