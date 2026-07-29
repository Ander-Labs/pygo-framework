package runtime

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// TestV100ReportsI18n verifies CSV report endpoint and i18n via Accept-Language.
func TestV100ReportsI18n(t *testing.T) {
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
	// Use an isolated DB for the test.
	dbPath := filepath.Join(t.TempDir(), "pygo_test.db")
	if err := os.Setenv("PYGO_DB", dbPath); err != nil {
		t.Fatal(err)
	}

	const addr = "127.0.0.1:18090"
	server := NewServerWithSocket(addr, sock, appPath)

	// Register hello + i18n endpoints
	server.Router().Handle("GET", "/hello/:name", func(args map[string]any) (any, error) {
		return CallPython("hello", args)
	}, false, false)
	server.Router().Handle("GET", "/greet_i18n/:name", func(args map[string]any) (any, error) {
		return CallPython("greet_i18n", args)
	}, false, false)
	server.Router().Handle("GET", "/report/customers.csv", func(args map[string]any) (any, error) {
		return CallPython("customer_report", args)
	}, false, false)

	go func() { _ = server.Start() }()
	defer server.Stop()

	base := "http://" + addr
	client := &http.Client{Timeout: 10 * time.Second}

	// Wait for server to be ready
	waitFor(t, base+"/hello/test", client)

	// 1) i18n: Spanish locale via Accept-Language header
	req, _ := http.NewRequest("GET", base+"/greet_i18n/Anders", nil)
	req.Header.Set("Accept-Language", "es-ES")
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("greet_i18n es: %v", err)
	}
	b, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	var out map[string]any
	if err := json.Unmarshal(b, &out); err != nil {
		t.Fatalf("greet_i18n es body not json: %s", b)
	}
	if msg, ok := out["message"].(string); !ok || msg != "¡Hola, Anders!" {
		t.Fatalf("expected Spanish greeting, got %v", out)
	}

	// 2) i18n: English locale (default)
	req, _ = http.NewRequest("GET", base+"/greet_i18n/Anders", nil)
	req.Header.Set("Accept-Language", "en-US")
	resp, err = client.Do(req)
	if err != nil {
		t.Fatalf("greet_i18n en: %v", err)
	}
	b, _ = io.ReadAll(resp.Body)
	resp.Body.Close()
	if err := json.Unmarshal(b, &out); err != nil {
		t.Fatalf("greet_i18n en body not json: %s", b)
	}
	if msg, ok := out["message"].(string); !ok || msg != "Hello, Anders!" {
		t.Fatalf("expected English greeting, got %v", out)
	}

	// 3) CSV report endpoint
	req, _ = http.NewRequest("GET", base+"/report/customers.csv", nil)
	resp, err = client.Do(req)
	if err != nil {
		t.Fatalf("report: %v", err)
	}
	b, _ = io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("report status %d: %s", resp.StatusCode, b)
	}
	csv := string(b)
	if csv == "" || !strings.Contains(csv, "name") || !strings.Contains(csv, "id") {
		t.Fatalf("CSV missing headers or empty: %s", csv)
	}
	// Should have at least one data row (the test inserted "test" and "Anders")
	if !strings.Contains(csv, "test") && !strings.Contains(csv, "Anders") {
		t.Fatalf("CSV missing expected data rows: %s", csv)
	}

	t.Logf("v0.10.0 OK: i18n=es/en + CSV report")
}