package transpiler

import (
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/ast"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV3500CrudParsing tests that crud ModelName syntax generates routes
func TestV3500CrudParsing(t *testing.T) {
	src := `
model User:
  id: UUID
  email: Email
  name: String

crud User
`
	l := lexer.New(src)
	tokens, err := l.Tokenize()
	if err != nil {
		t.Fatalf("Tokenize failed: %v", err)
	}
	p := parser.New(tokens, src)
	prog, err := p.Parse()
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	// Should have one CrudNode
	if len(prog.Cruds) != 1 {
		t.Fatalf("Expected 1 CrudNode, got %d", len(prog.Cruds))
	}

	crud := prog.Cruds[0]
	if crud.Name != "User" {
		t.Errorf("Expected CrudNode name 'User', got %q", crud.Name)
	}

	// Should have 5 generated routes
	if len(crud.Routes) != 5 {
		t.Errorf("Expected 5 CRUD routes, got %d", len(crud.Routes))
	}

	// Verify route methods
	expectedMethods := []string{"GET", "GET", "POST", "PUT", "DELETE"}
	for i, r := range crud.Routes {
		if r.Method != expectedMethods[i] {
			t.Errorf("Route %d: expected method %s, got %s", i, expectedMethods[i], r.Method)
		}
	}

	// Verify route paths
	expectedPaths := []string{"/user", "/user/:id", "/user", "/user/:id", "/user/:id"}
	for i, r := range crud.Routes {
		if r.Path != expectedPaths[i] {
			t.Errorf("Route %d: expected path %s, got %s", i, expectedPaths[i], r.Path)
		}
	}

	// Verify handler names
	expectedHandlers := []string{"ListUser", "GetUser", "CreateUser", "UpdateUser", "DeleteUser"}
	for i, r := range crud.Routes {
		if r.Handler != expectedHandlers[i] {
			t.Errorf("Route %d: expected handler %s, got %s", i, expectedHandlers[i], r.Handler)
		}
	}
}

// TestV3500CrudMultipleModels tests CRUD with multiple models
func TestV3500CrudMultipleModels(t *testing.T) {
	src := `
model User:
  id: UUID
  name: String

model Product:
  id: UUID
  name: String

crud User
crud Product
`
	l := lexer.New(src)
	tokens, err := l.Tokenize()
	if err != nil {
		t.Fatalf("Tokenize failed: %v", err)
	}
	p := parser.New(tokens, src)
	prog, err := p.Parse()
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if len(prog.Cruds) != 2 {
		t.Fatalf("Expected 2 CrudNodes, got %d", len(prog.Cruds))
	}

	// Check User CRUD
	if prog.Cruds[0].Name != "User" {
		t.Errorf("Expected first CrudNode 'User', got %q", prog.Cruds[0].Name)
	}

	// Check Product CRUD
	if prog.Cruds[1].Name != "Product" {
		t.Errorf("Expected second CrudNode 'Product', got %q", prog.Cruds[1].Name)
	}
}

// TestV3500CrudNodeStructure tests the CrudNode structure
func TestV3500CrudNodeStructure(t *testing.T) {
	node := &ast.CrudNode{
		Name:            "TestModel",
		Line:            10,
		HandlerPrefix:   "CrudTestModel",
		Routes:          []ast.CrudRoute{},
	}

	if node.Name != "TestModel" {
		t.Errorf("Expected name 'TestModel', got %q", node.Name)
	}
	if node.Line != 10 {
		t.Errorf("Expected line 10, got %d", node.Line)
	}
	if node.HandlerPrefix != "CrudTestModel" {
		t.Errorf("Expected handler prefix 'CrudTestModel', got %q", node.HandlerPrefix)
	}
}
