package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestV050Build verifies `pygo build --embed-python` writes a PyOxidizer spec
// without pulling the heavy Rust/PyOxidizer toolchain here. If pyoxidizer is on
// PATH it would build; otherwise the spec is emitted and the user runs it where
// the toolchain exists.
func TestV050Build(t *testing.T) {
	tmp := t.TempDir()
	// Seed a minimal project: a .pgo and an app_poc.py + core/ so the spec
	// generation has something to reference.
	if err := os.WriteFile(filepath.Join(tmp, "app.pgo"), []byte("model X:\n    id: UUID?\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(tmp, "core", "runtime"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(tmp, "app_poc.py"), []byte("print('app')\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// runBuild uses findFirstPgo("."), so run from the seeded project dir.
	oldWd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(tmp); err != nil {
		t.Fatal(err)
	}
	defer os.Chdir(oldWd)
	oldArgs := os.Args
	os.Args = []string{"pygo", "build", "--embed-python", "--o", filepath.Join(tmp, "dist", "app")}
	defer func() { os.Args = oldArgs }()

	if err := runBuild(os.Args[2:]); err != nil {
		t.Fatalf("runBuild: %v", err)
	}

	spec := filepath.Join(tmp, "pyoxidizer.bzl")
	data, err := os.ReadFile(spec)
	if err != nil {
		t.Fatalf("spec not written: %v", err)
	}
	content := string(data)
	if strings.Contains(content, "%q") || strings.Contains(content, "%s") {
		t.Fatalf("spec not formatted, leftover verb: %s", content)
	}
	if !strings.Contains(content, "default_python_distribution") {
		t.Fatalf("spec missing PyOxidizer entrypoint: %s", content)
	}
	t.Logf("v0.5.0 OK: pyoxidizer.bzl generated (%d bytes)", len(content))
}
