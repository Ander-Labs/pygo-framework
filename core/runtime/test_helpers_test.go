// Package runtime — test helpers for PyGo dual-language integration tests.
// Provides repoRoot() and contains() used by v-series integration tests.
package runtime

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// repoRoot walks up from the calling test file to find the git repo root.
func repoRoot() (string, error) {
	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		return "", nil
	}
	dir := filepath.Dir(filename)

	// Walk up until we find go.mod (marks repo root)
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			// Reached filesystem root
			return dir, nil
		}
		dir = parent
	}
}

// contains checks if a string contains a substring (test helper).
func contains(s, substr string) bool {
	return strings.Contains(s, substr)
}
