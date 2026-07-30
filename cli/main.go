// Command pygo is the PyGo framework CLI (Fase 0 / PoC).
//
// Subcommands:
//
//	pygo new <name>       scaffold a new PyGo project
//	pygo dev              transpile the first .pgo and start the dev server
//	pygo build            build for production (--embed-python is a TODO)
//
// Only the Go standard library is used (flag). No third-party CLI framework
// is added so go.mod stays untouched.
package main

import (
	"fmt"
	"os"
)

const usage = `pygo — PyGo framework CLI (Fase 0 / PoC)

Usage:
  pygo <command> [arguments]

Commands:
  new <name>    Create a new PyGo project in ./<name>/
  dev           Transpile the first .pgo file and start the dev server (:8080)
  build         Build for production (use --embed-python for a single binary)
  gen [file]    Transpile .pgo files to Go/Python
  test          Run tests for the project

Run "pygo <command> -h" for command-specific flags.
`

func main() {
	if len(os.Args) < 2 {
		fmt.Fprint(os.Stderr, usage)
		os.Exit(2)
	}

	cmd := os.Args[1]
	args := os.Args[2:]

	var err error
	switch cmd {
	case "new":
		err = runNew(args)
	case "dev":
		err = runDev(args)
	case "build":
		err = runBuild(args)
	case "gen":
		err = runGen(args)
	case "test":
		err = runTest(args)
	case "-h", "--help", "help":
		fmt.Print(usage)
		return
	default:
		fmt.Fprintf(os.Stderr, "pygo: unknown command %q\n\n%s", cmd, usage)
		os.Exit(2)
	}

	if err != nil {
		fmt.Fprintf(os.Stderr, "pygo %s: %v\n", cmd, err)
		os.Exit(1)
	}
}
