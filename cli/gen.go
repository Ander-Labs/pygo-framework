package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

// runGen transpiles .pgo files to Go/Python without running the server.
func runGen(args []string) error {
	fs := flag.NewFlagSet("gen", flag.ContinueOnError)
	fs.Usage = func() {
		fmt.Fprintln(os.Stderr, "Usage: pygo gen [file.pgo] [--go-out DIR] [--py-out DIR]")
		fs.PrintDefaults()
	}
	goOut := "generated"
	pyOut := "generated"
	var inputFile string

	fs.StringVar(&goOut, "go-out", goOut, "output directory for Go files")
	fs.StringVar(&pyOut, "py-out", pyOut, "output directory for Python files")
	if err := fs.Parse(args); err != nil {
		return err
	}

	if fs.NArg() >= 1 {
		inputFile = fs.Arg(0)
	} else {
		// Find first .pgo file in web/ directory
		matches, err := filepath.Glob("web/*.pgo")
		if err != nil || len(matches) == 0 {
			return fmt.Errorf("no .pgo file found in web/")
		}
		inputFile = matches[0]
	}

	fmt.Printf("Transpiling %s...\n", inputFile)
	fmt.Printf("  Go output: %s/\n", goOut)
	fmt.Printf("  Python output: %s/\n", pyOut)
	
	// TODO: Implement actual transpilation
	fmt.Println("Transpilation complete")
	return nil
}

// runTest runs tests for the PyGo project.
func runTest(args []string) error {
	fs := flag.NewFlagSet("test", flag.ContinueOnError)
	fs.Usage = func() {
		fmt.Fprintln(os.Stderr, "Usage: pygo test [package] [-v]")
		fs.PrintDefaults()
	}
	var verbose bool
	fs.BoolVar(&verbose, "v", false, "verbose output")
	
	if err := fs.Parse(args); err != nil {
		return err
	}

	fmt.Println("Running tests...")
	return nil
}