package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV240Integration verifies complete end-to-end transpilation.
func TestV240Integration(t *testing.T) {
	// Full DSL example
	src := `
model User:
  id: UUID
  email: Email
  name: String
  created_at: DateTime

model Post:
  id: UUID
  title: String
  content: String
  user_id: UUID

enum Status:
  draft
  published
  archived

enum Role:
  admin=1
  author=2
  reader=3

handler hello:
  get() -> String:
    return "Hello, World!"

route GET /hello -> hello
`

	l := lexer.New(src)
	toks, err := l.Tokenize()
	if err != nil {
		t.Fatalf("lex: %v", err)
	}
	p := parser.New(toks, src)
	prog, err := p.Parse()
	if err != nil {
		t.Fatalf("parse: %v", err)
	}

	// Verify all components parsed
	if len(prog.Models) != 2 {
		t.Fatalf("expected 2 models, got %d", len(prog.Models))
	}
	if len(prog.Enums) != 2 {
		t.Fatalf("expected 2 enums, got %d", len(prog.Enums))
	}
	if len(prog.Handlers) != 1 {
		t.Fatalf("expected 1 handler, got %d", len(prog.Handlers))
	}
	if len(prog.Routes) != 1 {
		t.Fatalf("expected 1 route, got %d", len(prog.Routes))
	}

	// Generate Go code
	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}

	// Verify Go output
	if !strings.Contains(goOut, "type User struct") {
		t.Fatal("Go missing User struct")
	}
	if !strings.Contains(goOut, "type Post struct") {
		t.Fatal("Go missing Post struct")
	}
	if !strings.Contains(goOut, "type Status") {
		t.Fatal("Go missing Status enum")
	}
	if !strings.Contains(goOut, "type Role int") {
		t.Fatal("Go missing Role enum with numeric values")
	}
	if !strings.Contains(goOut, "func Handler_hello") {
		t.Fatal("Go missing hello handler")
	}

	// Generate Python code
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Verify Python output
	if !strings.Contains(pyOut, "class User:") {
		t.Fatal("Python missing User class")
	}
	if !strings.Contains(pyOut, "class Status") {
		t.Fatal("Python missing Status enum")
	}
	if !strings.Contains(pyOut, "class Role(int, enum.Enum)") {
		t.Fatal("Python missing Role enum with int")
	}
	if !strings.Contains(pyOut, "def hello():") {
		t.Fatal("Python missing hello handler")
	}

	t.Logf("v0.24.0 integration test passed")
}
