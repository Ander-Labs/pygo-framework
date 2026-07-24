package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/ander-labs/pygo/core/runtime"
)

// runDev is the real PoC flow (see DSL-SPEC.md §4 and ARCHITECTURE.md):
//  1. Find the first .pgo file in the project.
//  2. Transpile it (`go run ./core/transpiler`) -> gen_go.go + gen_py.py.
//  3. Start the Go supervisor, which opens the UDS and launches Python
//     (core.runtime.pyclient) that registers the generated handlers.
//  4. Serve /hello/:name, delegating the handler to Python over the socket
//     via runtime.CallPython.
func runDev(args []string) error {
	fs := flag.NewFlagSet("dev", flag.ContinueOnError)
	addr := fs.String("addr", ":8080", "HTTP listen address")
	frameworkRoot := fs.String("framework-root", "", "path to the PyGo framework repo (for `go run ./core/transpiler`); defaults to $PYGO_HOME or the current module")
	fs.Usage = func() {
		fmt.Fprintln(os.Stderr, "Usage: pygo dev [flags]")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		return err
	}

	pgo, err := findFirstPgo(".")
	if err != nil {
		return err
	}
	fmt.Printf("dev: found DSL source %s\n", pgo)

	outDir := filepath.Join(filepath.Dir(pgo), ".pygo-gen")
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return fmt.Errorf("creating gen dir: %w", err)
	}

	if err := transpile(*frameworkRoot, pgo, outDir); err != nil {
		return fmt.Errorf("transpile failed: %w", err)
	}
	fmt.Printf("dev: transpiled -> %s/gen_go.go, %s/gen_py.py\n", outDir, outDir)

	// Start the runtime supervisor. It launches Python with the pyclient
	// module; gen_py.py registers handlers into the shared HANDLERS dict.
	root := frameworkRootOrCwd(*frameworkRoot)
	sup := runtime.New(runtime.Config{
		Interpreter: "python3",
		Module:      "-m",
		ExtraArgs:   []string{"core.runtime.pyclient"},
	})
	runtime.SetDefault(sup)
	// PYTHONPATH so `core.runtime.pyclient` resolves when run from the project.
	// The supervisor inherits os.Environ(), so we set it on the process.
	if err := os.Setenv("PYTHONPATH", root); err != nil {
		return fmt.Errorf("setting PYTHONPATH: %w", err)
	}
	if err := sup.Start(); err != nil {
		return fmt.Errorf("starting python runtime: %w", err)
	}
	defer sup.Stop()
	fmt.Println("dev: python runtime connected")

	mux := http.NewServeMux()
	mux.HandleFunc("/hello/", makeHelloHandler())
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "not found", http.StatusNotFound)
	})

	fmt.Printf("dev server ready on http://127.0.0.1%s\n", normalizeAddr(*addr))
	fmt.Println("dev: try  curl http://127.0.0.1:8080/hello/Anders")
	return http.ListenAndServe(*addr, mux)
}

// makeHelloHandler builds the /hello/:name handler that delegates to Python.
func makeHelloHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		name := strings.TrimPrefix(r.URL.Path, "/hello/")
		name = strings.TrimSuffix(name, "/")
		if name == "" || strings.Contains(name, "/") {
			http.Error(w, "usage: /hello/:name", http.StatusBadRequest)
			return
		}

		result, err := runtime.CallPython("hello", map[string]any{"name": name})
		if err != nil {
			writeErr(w, err)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(result)
	}
}

func writeErr(w http.ResponseWriter, err error) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusInternalServerError)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"error": err.Error(),
	})
}

// transpile shells out to the framework's transpiler:
//
//	go run ./core/transpiler <input.pgo>
func transpile(frameworkRoot, input, outDir string) error {
	root := frameworkRootOrCwd(frameworkRoot)
	absInput, err := filepath.Abs(input)
	if err != nil {
		return err
	}
	absOut, err := filepath.Abs(outDir)
	if err != nil {
		return err
	}
	cmd := exec.Command("go", "run", "./core/transpiler", absInput, "--out", absOut)
	cmd.Dir = root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Env = append(os.Environ(), "PATH="+os.Getenv("PATH"))
	return cmd.Run()
}

func frameworkRootOrCwd(frameworkRoot string) string {
	if frameworkRoot != "" {
		return frameworkRoot
	}
	if home := os.Getenv("PYGO_HOME"); home != "" {
		return home
	}
	return "."
}

func findFirstPgo(dir string) (string, error) {
	var found string
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if found != "" {
			return filepath.SkipDir
		}
		if info.IsDir() {
			base := info.Name()
			if base != "." && (strings.HasPrefix(base, ".") || base == "node_modules") {
				return filepath.SkipDir
			}
			return nil
		}
		if strings.HasSuffix(info.Name(), ".pgo") {
			found = path
		}
		return nil
	})
	if err != nil {
		return "", err
	}
	if found == "" {
		return "", fmt.Errorf("no .pgo file found under %q (run `pygo new` first?)", dir)
	}
	return found, nil
}

func normalizeAddr(addr string) string {
	if strings.HasPrefix(addr, ":") {
		return addr
	}
	return ":" + addr
}
