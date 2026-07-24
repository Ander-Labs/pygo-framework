package runtime

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestPoCHelloWorld is the end-to-end PoC: Go supervisor launches Python
// (app_poc.py), which imports the transpiled gen_py.py and serves HANDLERS
// over the UDS. We call runtime.CallPython("hello", {name}) and expect the
// Greeting back.
func TestPoCHelloWorld(t *testing.T) {
	repoRoot, err := repoRoot()
	if err != nil {
		t.Fatalf("repo root: %v", err)
	}
	appDir := filepath.Join(repoRoot, "examples", "hello-world")
	appPath := filepath.Join(appDir, "app_poc.py")
	if _, err := os.Stat(appPath); err != nil {
		t.Fatalf("app_poc.py missing (run `go run ./core/transpiler` first): %v", err)
	}

	// PYTHONPATH must include the repo root so `core.runtime.pyclient` resolves.
	if err := os.Setenv("PYTHONPATH", repoRoot); err != nil {
		t.Fatal(err)
	}

	sup := New(Config{
		Interpreter: "python3",
		Module:      appPath,
		AcceptTimeout: 15 * time.Second,
	})
	SetDefault(sup)
	if err := sup.Start(); err != nil {
		t.Fatalf("supervisor start: %v", err)
	}
	defer sup.Stop()

	result, err := CallPython("hello", map[string]any{"name": "Anders"})
	if err != nil {
		t.Fatalf("CallPython: %v", err)
	}

	greeting, ok := result.(map[string]any)
	if !ok {
		t.Fatalf("unexpected result type %T: %v", result, result)
	}
	if greeting["name"] != "Anders" {
		t.Fatalf("expected name=Anders, got %v", greeting["name"])
	}
	t.Logf("PoC OK: %v", greeting)
}

// repoRoot walks up to the directory containing go.mod.
func repoRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for i := 0; i < 8; i++ {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir, nil
		}
		dir = filepath.Dir(dir)
	}
	return "", fmt.Errorf("go.mod not found")
}
