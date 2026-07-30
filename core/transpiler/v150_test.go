package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV150NumericEnum verifies numeric enum values work.
func TestV150NumericEnum(t *testing.T) {
	src := `
enum Status:
  active=1
  inactive=2
  pending=3
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

	// Verify enum has correct values
	if len(prog.Enums) != 1 {
		t.Fatalf("expected 1 enum, got %d", len(prog.Enums))
	}
	status := prog.Enums[0]
	if status.Name != "Status" {
		t.Fatalf("enum name: got %s", status.Name)
	}
	if len(status.Values) != 3 {
		t.Fatalf("expected 3 values, got %d", len(status.Values))
	}

	// Verify values
	if status.Values[0].Name != "active" || status.Values[0].Value != "1" {
		t.Fatalf("first value: got %+v", status.Values[0])
	}
	if status.Values[1].Name != "inactive" || status.Values[1].Value != "2" {
		t.Fatalf("second value: got %+v", status.Values[1])
	}
	if status.Values[2].Name != "pending" || status.Values[2].Value != "3" {
		t.Fatalf("third value: got %+v", status.Values[2])
	}

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: numeric enum -> type Status int
	if !strings.Contains(goOut, "type Status int") {
		t.Fatalf("go missing numeric enum:\n%s", goOut)
	}
	if !strings.Contains(goOut, "StatusActive Status = 1") {
		t.Fatalf("go missing enum constant:\n%s", goOut)
	}

	// Python: numeric enum -> class Status(int, enum.Enum)
	if !strings.Contains(pyOut, "class Status(int, enum.Enum):") {
		t.Fatalf("py missing numeric enum:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "ACTIVE = 1") {
		t.Fatalf("py missing enum constant:\n%s", pyOut)
	}

	t.Logf("v0.15.0 Numeric enum OK")
}

// TestV150StringEnum verifies string enum values still work.
func TestV150StringEnum(t *testing.T) {
	src := `
enum Status:
  active
  inactive
  pending
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

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: string enum -> type Status string
	if !strings.Contains(goOut, "type Status string") {
		t.Fatalf("go missing string enum:\n%s", goOut)
	}

	// Python: string enum -> class Status(str, enum.Enum)
	if !strings.Contains(pyOut, "class Status(str, enum.Enum):") {
		t.Fatalf("py missing string enum:\n%s", pyOut)
	}

	t.Logf("v0.15.0 String enum OK")
}