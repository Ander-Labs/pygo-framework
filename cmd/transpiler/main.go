// Command transpiler is the PyGo CLI transpiler: given a `.pgo` file it emits
// gen_go.go and gen_py.py into the output directory.
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"pygo-framework/core/transpiler/generators"
	"pygo-framework/core/transpiler/lexer"
	"pygo-framework/core/transpiler/parser"
)

func main() {
	outDir := flag.String("out", "", "output directory (default: same dir as input)")
	pkg := flag.String("pkg", "generated", "Go package name for gen_go.go")
	flag.Parse()

	if flag.NArg() < 1 {
		fmt.Fprintln(os.Stderr, "usage: transpiler <file.pgo> [--out dir] [--pkg name]")
		os.Exit(2)
	}
	inPath := flag.Arg(0)

	if err := run(inPath, *outDir, *pkg); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}

func run(inPath, outDir, pkg string) error {
	src, err := os.ReadFile(inPath)
	if err != nil {
		return fmt.Errorf("read input: %w", err)
	}

	tokens, err := lexer.New(string(src)).Tokenize()
	if err != nil {
		return fmt.Errorf("lex: %w", err)
	}

	prog, err := parser.New(tokens, string(src)).Parse()
	if err != nil {
		return fmt.Errorf("parse: %w", err)
	}

	goSrc, err := generators.GenerateGo(prog, pkg)
	if err != nil {
		return fmt.Errorf("gen_go: %w", err)
	}

	pySrc, err := generators.GeneratePy(prog)
	if err != nil {
		return fmt.Errorf("gen_py: %w", err)
	}

	if outDir == "" {
		outDir = filepath.Dir(inPath)
	}
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return fmt.Errorf("mkdir out: %w", err)
	}

	goPath := filepath.Join(outDir, "gen_go.go")
	pyPath := filepath.Join(outDir, "gen_py.py")

	if err := os.WriteFile(goPath, []byte(goSrc), 0o644); err != nil {
		return fmt.Errorf("write gen_go.go: %w", err)
	}
	if err := os.WriteFile(pyPath, []byte(pySrc), 0o644); err != nil {
		return fmt.Errorf("write gen_py.py: %w", err)
	}

	fmt.Printf("wrote %s\n", goPath)
	fmt.Printf("wrote %s\n", pyPath)
	return nil
}
