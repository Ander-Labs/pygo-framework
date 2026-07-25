package runtime

import (
	"io"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestV040Auth verifies the native JWT middleware: a protected route returns
// 401 without a token and 200 with a valid Bearer JWT, injecting the subject.
func TestV040Auth(t *testing.T) {
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
	// Fixed secret for the test.
	if err := os.Setenv("PYGO_JWT_SECRET", "test-secret-v040"); err != nil {
		t.Fatal(err)
	}

	const addr = "127.0.0.1:18082"
	server := NewServer(addr, appPath)
	server.Router().Handle("GET", "/me", func(args map[string]any) (any, error) {
		user, _ := args["_user"].(string)
		return map[string]any{"user": user}, nil
	}, true)

	go func() { _ = server.Start() }()
	defer server.Stop()

	base := "http://" + addr
	client := &http.Client{Timeout: 5 * time.Second}
	waitFor(t, base+"/me", client)

	// No token -> 401.
	resp, err := client.Get(base + "/me")
	if err != nil {
		t.Fatalf("get no-token: %v", err)
	}
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("expected 401 without token, got %d", resp.StatusCode)
	}
	resp.Body.Close()

	// Valid token -> 200 with subject.
	tok, err := SignHS256(Claims{Sub: "user-42"}, "test-secret-v040")
	if err != nil {
		t.Fatal(err)
	}
	req, _ := http.NewRequest("GET", base+"/me", nil)
	req.Header.Set("Authorization", "Bearer "+tok)
	resp2, err := client.Do(req)
	if err != nil {
		t.Fatalf("get with-token: %v", err)
	}
	defer resp2.Body.Close()
	body, _ := io.ReadAll(resp2.Body)
	if resp2.StatusCode != http.StatusOK {
		t.Fatalf("expected 200 with token, got %d: %s", resp2.StatusCode, body)
	}
	if !contains(string(body), "user-42") {
		t.Fatalf("expected subject user-42 in response, got %s", body)
	}
	t.Logf("v0.4.0 OK: %s", body)
}
