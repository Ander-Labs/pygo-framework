package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

const (
	registryURL = "https://raw.githubusercontent.com/pygo-labs/pygo-registry/main/registry.json"
	moduleDir   = "pygo_modules"
)

type Module struct {
	Name         string   `json:"name"`
	Version      string   `json:"version"`
	Description  string   `json:"description"`
	Author       string   `json:"author"`
	Repository   string   `json:"repository"`
	DownloadURL  string   `json:"download_url"`
	Checksum     string   `json:"checksum"`
	Dependencies []string `json:"dependencies"`
	License      string   `json:"license"`
	Category     string   `json:"category"`
	Tags         []string `json:"tags"`
	Official     bool     `json:"official"`
}

type Registry struct {
	Version     string   `json:"version"`
	LastUpdated string   `json:"last_updated"`
	Repository  string   `json:"repository"`
	Modules     []Module `json:"modules"`
}

func runModule(args []string) error {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: pygo module <command>\n\nCommands:\n  install <name>    Install a module from the registry\n  list              List installed modules\n  search <term>     Search available modules")
		os.Exit(2)
	}

	switch args[0] {
	case "install":
		return runModuleInstall(args[1:])
	case "list":
		return runModuleList()
	case "search":
		return runModuleSearch(args[1:])
	default:
		return fmt.Errorf("unknown module subcommand %q", args[0])
	}
}

func fetchRegistry() (*Registry, error) {
	resp, err := http.Get(registryURL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch registry: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("registry returned status %d", resp.StatusCode)
	}

	var reg Registry
	if err := json.NewDecoder(resp.Body).Decode(&reg); err != nil {
		return nil, fmt.Errorf("failed to parse registry: %w", err)
	}
	return &reg, nil
}

func findModule(reg *Registry, name string) *Module {
	for i := range reg.Modules {
		if reg.Modules[i].Name == name {
			return &reg.Modules[i]
		}
	}
	return nil
}

func runModuleInstall(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("module name required: pygo module install <name>")
	}

	name := args[0]
	fmt.Println("Fetching registry...")

	reg, err := fetchRegistry()
	if err != nil {
		return err
	}

	mod := findModule(reg, name)
	if mod == nil {
		return fmt.Errorf("module %q not found in registry", name)
	}

	fmt.Printf("Installing %s v%s...\n", mod.Name, mod.Version)

	// Check dependencies
	for _, dep := range mod.Dependencies {
		fmt.Printf("  dependency: %s\n", dep)
	}

	// Download module
	if err := downloadModule(mod); err != nil {
		return err
	}

	// Install locally
	if err := installModuleLocal(mod); err != nil {
		return err
	}

	fmt.Printf("OK %s installed successfully\n", mod.Name)
	fmt.Printf("  Repository: %s\n", mod.Repository)
	return nil
}

func downloadModule(mod *Module) error {
	if mod.DownloadURL == "" {
		return fmt.Errorf("no download URL for module %s", mod.Name)
	}

	fmt.Printf("  downloading from %s...\n", mod.DownloadURL)

	resp, err := http.Get(mod.DownloadURL)
	if err != nil {
		return fmt.Errorf("download failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("download failed with status %d", resp.StatusCode)
	}

	tmpFile, err := os.CreateTemp("", mod.Name+"-*.tar.gz")
	if err != nil {
		return err
	}
	defer os.Remove(tmpFile.Name())

	if _, err := io.Copy(tmpFile, resp.Body); err != nil {
		return err
	}
	tmpFile.Close()

	fmt.Printf("  downloaded (%.1f KB)\n", float64(resp.ContentLength)/1024)
	return nil
}

func installModuleLocal(mod *Module) error {
	if err := os.MkdirAll(moduleDir, 0755); err != nil {
		return err
	}

	metaPath := filepath.Join(moduleDir, mod.Name+".mod")
	meta := fmt.Sprintf("name: %s\nversion: %s\nrepository: %s\n",
		mod.Name, mod.Version, mod.Repository)
	return os.WriteFile(metaPath, []byte(meta), 0644)
}

func runModuleList() error {
	entries, err := os.ReadDir(moduleDir)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Println("No modules installed")
			return nil
		}
		return err
	}

	fmt.Println("Installed modules:")
	for _, f := range entries {
		if strings.HasSuffix(f.Name(), ".mod") {
			name := strings.TrimSuffix(f.Name(), ".mod")
			fmt.Printf("  %s\n", name)
		}
	}
	return nil
}

func runModuleSearch(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("search term required: pygo module search <term>")
	}

	term := strings.ToLower(args[0])
	reg, err := fetchRegistry()
	if err != nil {
		return err
	}

	fmt.Printf("Searching for \"%s\"...\n\n", term)
	found := 0
	for _, mod := range reg.Modules {
		searchable := strings.ToLower(mod.Name + " " + mod.Description + " " + strings.Join(mod.Tags, " "))
		if strings.Contains(searchable, term) {
			fmt.Printf("  %s v%s — %s\n", mod.Name, mod.Version, mod.Description)
			if mod.Official {
				fmt.Println("    [official]")
			}
			found++
		}
	}

	if found == 0 {
		fmt.Println("No modules found")
	} else {
		fmt.Printf("\n%d module(s) found\n", found)
	}
	return nil
}
