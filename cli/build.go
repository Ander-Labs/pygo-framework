package main

import (
	"flag"
	"fmt"
	"os"
)

// runBuild builds the project for production.
//
// Fase 0: this only describes the intended steps. PyOxidizer integration
// (embedding the Python interpreter into a single binary) is a TODO tracked in
// ARCHITECTURE.md §4.
func runBuild(args []string) error {
	fs := flag.NewFlagSet("build", flag.ContinueOnError)
	embedPython := fs.Bool("embed-python", false, "embed the Python interpreter into a single binary via PyOxidizer (TODO)")
	out := fs.String("o", "dist/app", "output binary path")
	fs.Usage = func() {
		fmt.Fprintln(os.Stderr, "Usage: pygo build [flags]")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		return err
	}

	fmt.Println("build: planned steps (Fase 0 — not yet executed):")
	fmt.Println("  1. Transpile all .pgo -> gen_go.go + gen_py.py")
	fmt.Println("  2. Compile the Go supervisor + generated routing")
	fmt.Printf("  3. Produce the production binary at %s\n", *out)

	if *embedPython {
		// TODO(build): integrate PyOxidizer to embed CPython + the app's Python
		// modules (and C-extensions such as psycopg/SQLAlchemy) into a single
		// self-contained binary. See ARCHITECTURE.md §4. Must be tested early
		// (Fase 1) with real C-extensions.
		fmt.Println("  4. [TODO] --embed-python: bundle CPython via PyOxidizer into a single binary")
		fmt.Println("build: --embed-python is not implemented yet (PyOxidizer integration pending)")
	} else {
		fmt.Println("build: dev-style build (Python runs from venv/). Use --embed-python for a single binary.")
	}

	return nil
}
