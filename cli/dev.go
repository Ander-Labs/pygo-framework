package main

import (
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/ander-labs/pygo/core/runtime"
)

// runDev is the real v0.2.0 flow: transpile, then start the native net/http
// Server (which launches Python via the supervisor) and serve HTMX fragments.
func runDev(args []string) error {
	fs := flag.NewFlagSet("dev", flag.ContinueOnError)
	addr := fs.String("addr", ":8080", "HTTP listen address")
	frameworkRoot := fs.String("framework-root", "", "path to the PyGo framework repo; defaults to $PYGO_HOME or the current module")
	fs.Usage = func() {
		fmt.Fprintln(os.Stderr, "Usage: pygo dev [flags]")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		return err
	}

	root := frameworkRootOrCwd(*frameworkRoot)
	pgo, err := findFirstPgo(".")
	if err != nil {
		return err
	}
	fmt.Printf("dev: found DSL source %s\n", pgo)

	projectDir := filepath.Dir(pgo)
	outDir := filepath.Join(projectDir, ".pygo-gen")
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return fmt.Errorf("creating gen dir: %w", err)
	}
	if err := transpile(root, pgo, outDir); err != nil {
		return fmt.Errorf("transpile failed: %w", err)
	}
	fmt.Printf("dev: transpiled -> %s/gen_go.go, %s/gen_py.py\n", outDir, outDir)

	// PYTHONPATH so `core.runtime.pyclient` (and the generated gen_py) resolve.
	if err := os.Setenv("PYTHONPATH", root); err != nil {
		return err
	}

	server := runtime.NewServer(*addr, "app_poc.py")
	// Register the HTMX fragment for the /hello/:name route.
	if frag, err := os.ReadFile(filepath.Join(projectDir, "hello.html")); err == nil {
		server.Router().RegisterView("GET", "/hello/:name", string(frag))
	} else {
		fmt.Println("dev: no hello.html found; serving JSON")
	}

	// gen_go.go registers routes onto the router via RegisterRoutes. To keep the
	// PoC dependency-free we register the one known route here; full wiring
	// (compiling gen_go.go into the project) lands with the generated main.
	if err := registerHelloRoute(server.Router()); err != nil {
		return err
	}
	// Example of a protected route: requires a valid Bearer JWT.
	server.Router().Handle("GET", "/me", func(args map[string]any) (any, error) {
		user, _ := args["_user"].(string)
		return map[string]any{"user": user}, nil
	}, true)

	fmt.Printf("dev server ready on http://127.0.0.1%s\n", normalizeAddr(*addr))
	fmt.Println("dev: try  curl http://127.0.0.1:8080/hello/Anders")
	return server.Start()
}

// registerHelloRoute wires the /hello/:name route to Python in the PoC. The
// generated gen_go.go will do this generically once compiled into the project.
func registerHelloRoute(r *runtime.Router) error {
	r.Handle("GET", "/hello/:name", func(args map[string]any) (any, error) {
		name, _ := args["name"].(string)
		return runtime.CallPython("hello", map[string]any{"name": name})
	}, false)
	return nil
}

func transpile(frameworkRoot, input, outDir string) error {
	absInput, err := filepath.Abs(input)
	if err != nil {
		return err
	}
	absOut, err := filepath.Abs(outDir)
	if err != nil {
		return err
	}
	cmd := exec.Command("go", "run", "./core/transpiler", absInput, "--out", absOut)
	cmd.Dir = frameworkRoot
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
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
