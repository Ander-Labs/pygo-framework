// Package main is the entry point for a PyGo application.
// It initializes the web server and Python bridge, then serves.
package main

import (
	"fmt"
	"log"
	"os"

	"pygo-framework/bridge"
	"pygo-framework/web"
)

func main() {
	// Get framework root from env (set by pygo CLI)
	frameworkRoot := os.Getenv("PYGO_HOME")
	if frameworkRoot == "" {
		frameworkRoot = os.Getenv("PWD") // fallback to current directory
	}

	// Ensure Python path includes framework root
	os.Setenv("PYTHONPATH", frameworkRoot)

	// Create app with UDS bridge
	app := web.NewApp("") // default socket: storage/.pygo.sock

	// Initialize — starts Python subprocess + UDS pool
	if err := app.Init(); err != nil {
		log.Fatalf("PyGo init error: %v", err)
	}

	// Example: register module routes
	// Each module can register routes like:
	// app.Get("/productos", handleProductosList)
	registerRoutes(app)

	// Run the server
	if err := app.Run(":8080"); err != nil {
		log.Fatalf("PyGo server error: %v", err)
	}
}

func registerRoutes(app *web.App) {
	// Placeholder for module route registration
	// Real apps would iterate modules/ and load their routes.pgo
	fmt.Println("PyGo ERP — routes registered (blank module)")
}
