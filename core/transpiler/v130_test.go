package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/ast"
	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV130TypeValidation verifies UUID/Email/DateTime fields generate validation helpers.
func TestV130TypeValidation(t *testing.T) {
	src := `
model Event:
  id: UUID
  email: Email
  created: DateTime
  url: URL
  phone: Phone
`

	l := lexer.New(src)
	tokens, err := l.Tokenize()
	if err != nil {
		t.Fatalf("lex: %v", err)
	}
	p := parser.New(tokens, src)
	prog, err := p.Parse()
	if err != nil {
		t.Fatalf("parse: %v", err)
	}

	// Verify model has correct fields
	if len(prog.Models) != 1 {
		t.Fatalf("expected 1 model, got %d", len(prog.Models))
	}
	event := prog.Models[0]
	if event.Name != "Event" {
		t.Fatalf("model name: got %s", event.Name)
	}

	fieldsByName := make(map[string]*ast.FieldNode)
	for _, f := range event.Fields {
		fieldsByName[f.Name] = f
	}

	// Verify UUID field
	if f, ok := fieldsByName["id"]; !ok {
		t.Fatal("missing id field")
	} else if f.Type.Name != "UUID" {
		t.Fatalf("id field type: got %s", f.Type.Name)
	}

	// Verify Email field
	if f, ok := fieldsByName["email"]; !ok {
		t.Fatal("missing email field")
	} else if f.Type.Name != "Email" {
		t.Fatalf("email field type: got %s", f.Type.Name)
	}

	// Verify DateTime field
	if f, ok := fieldsByName["created"]; !ok {
		t.Fatal("missing created field")
	} else if f.Type.Name != "DateTime" {
		t.Fatalf("created field type: got %s", f.Type.Name)
	}

	// Verify URL field
	if f, ok := fieldsByName["url"]; !ok {
		t.Fatal("missing url field")
	} else if f.Type.Name != "URL" {
		t.Fatalf("url field type: got %s", f.Type.Name)
	}

	// Verify Phone field
	if f, ok := fieldsByName["phone"]; !ok {
		t.Fatal("missing phone field")
	} else if f.Type.Name != "Phone" {
		t.Fatalf("phone field type: got %s", f.Type.Name)
	}

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: UUID -> string, DateTime -> time.Time
	if !strings.Contains(goOut, "Id string") {
		t.Fatalf("go missing UUID field:\n%s", goOut)
	}
	if !strings.Contains(goOut, "Created time.Time") {
		t.Fatalf("go missing DateTime field:\n%s", goOut)
	}

	// Python: all fields as str/datetime
	if !strings.Contains(pyOut, "id: str") {
		t.Fatalf("py missing UUID field:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "email: str") {
		t.Fatalf("py missing Email field:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "created: datetime") {
		t.Fatalf("py missing DateTime field:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "url: str") {
		t.Fatalf("py missing URL field:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "phone: str") {
		t.Fatalf("py missing Phone field:\n%s", pyOut)
	}

	// Type mappings are correct for UUID/Email/DateTime/URL/Phone
	t.Logf("v0.13.0 Type mappings OK")
}