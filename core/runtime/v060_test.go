package runtime

import (
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// TestV060HotReload verifies that editing a .html fragment hot-swaps into the
// running server without restarting it. The Go process (and the test) stays up;
// only the in-memory view changes.
func TestV060HotReload(t *testing.T) {
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

	const addr = "127.0.0.1:18083"
	server := NewServerWithSocket(addr, sock, appPath)
	baseHTML := "<div id=\"greeting\"><h2>Hello, {{ .name }}!</h2></div>"
	server.Router().RegisterView("GET", "/hello/:name", baseHTML)
	server.Router().Handle("GET", "/hello/:name", func(args map[string]any) (any, error) {
		name, _ := args["name"].(string)
		return map[string]any{"name": name}, nil
	}, false)

	go func() { _ = server.Start() }()
	defer server.Stop()

	base := "http://" + addr
	client := &http.Client{Timeout: 5 * time.Second}
	waitFor(t, base+"/hello/Anders", client)

	// Initial render.
	body := getBody(t, client, base+"/hello/Anders")
	if !strings.Contains(body, "Hello, Anders!") {
		t.Fatalf("initial render wrong: %s", body)
	}

	// Simulate an editor writing a NEW fragment to hello.html on disk.
	newFrag := "<div id=\"greeting\"><h1>HOT-RELOADED {{ .name }}</h1></div>"
	server.Router().SetView("GET", "/hello/:name", newFrag)

	// Request again: should reflect the hot-swapped fragment, server still up.
	body2 := getBody(t, client, base+"/hello/Anders")
	if !strings.Contains(body2, "HOT-RELOADED Anders") {
		t.Fatalf("hot-swap did not take effect: %s", body2)
	}
	t.Logf("v0.6.0 OK: before=%q after=%q", body, body2)
}

func getBody(t *testing.T, client *http.Client, url string) string {
	t.Helper()
	resp, err := client.Get(url)
	if err != nil {
		t.Fatalf("get %s: %v", url, err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	return string(b)
}
