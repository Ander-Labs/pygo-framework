package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

// runNew scaffolds a new PyGo project at ./<name>/ with the minimal Fase 0
// structure: pygo.toml, a web/hello.pgo example, and a README.
func runNew(args []string) error {
	fs := flag.NewFlagSet("new", flag.ContinueOnError)
	fs.Usage = func() {
		fmt.Fprintln(os.Stderr, "Usage: pygo new <name>")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		return err
	}
	if fs.NArg() < 1 {
		fs.Usage()
		return fmt.Errorf("missing project name")
	}
	name := fs.Arg(0)

	root := filepath.Clean(name)
	if _, err := os.Stat(root); err == nil {
		return fmt.Errorf("directory %q already exists", root)
	}

	webDir := filepath.Join(root, "web")
	if err := os.MkdirAll(webDir, 0o755); err != nil {
		return fmt.Errorf("creating project dirs: %w", err)
	}

	files := map[string]string{
		filepath.Join(root, "pygo.toml"):    renderPygoToml(name),
		filepath.Join(webDir, "hello.pgo"):  helloPgo,
		filepath.Join(root, "README.md"):    renderReadme(name),
	}
	for path, content := range files {
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			return fmt.Errorf("writing %s: %w", path, err)
		}
	}

	fmt.Printf("Created PyGo project %q:\n", name)
	fmt.Printf("  %s/pygo.toml\n", root)
	fmt.Printf("  %s/web/hello.pgo\n", root)
	fmt.Printf("  %s/README.md\n", root)
	fmt.Printf("\nNext:\n  cd %s\n  pygo dev\n", name)
	return nil
}

func renderPygoToml(name string) string {
	return fmt.Sprintf(`# PyGo project config
dsl_version = "0.0.1"
name = %q

[server]
host = "127.0.0.1"
port = 8080

[python]
interpreter = "python3"
module = "app.py"
`, name)
}

// helloPgo is the end-to-end PoC example from DSL-SPEC.md §4.
const helloPgo = `model Greeting:
    id: UUID?
    name: String

route GET /hello/:name -> hello

handler hello(name: String) -> Greeting:
    return Greeting(name=name)
`

func renderReadme(name string) string {
	return fmt.Sprintf("# %s\n\nA PyGo project (Fase 0 / PoC).\n\n"+
		"## Structure\n\n"+
		"- `pygo.toml` — project config.\n"+
		"- `web/hello.pgo` — DSL: model + route + handler.\n\n"+
		"## Develop\n\n"+
		"```sh\npygo dev\n```\n\n"+
		"Transpiles the first `.pgo` file, starts the Go supervisor which\n"+
		"launches Python, and serves on http://127.0.0.1:8080.\n\n"+
		"Try: `curl http://127.0.0.1:8080/hello/Anders`\n\n"+
		"## Build\n\n"+
		"```sh\npygo build --embed-python\n```\n", name)
}
