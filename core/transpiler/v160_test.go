package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV160ArrayEnum verifies Array[Enum] type mapping.
func TestV160ArrayEnum(t *testing.T) {
	src := `
enum Status:
  active
  inactive

model Order:
  id: UUID
  status: Array[Status]
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

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: Array[Status] -> []Status
	if !strings.Contains(goOut, "Status []Status") {
		t.Fatalf("go missing Array[Enum]:\n%s", goOut)
	}

	// Python: Array[Status] -> list[Status]
	if !strings.Contains(pyOut, "status: list[Status]") {
		t.Fatalf("py missing Array[Enum]:\n%s", pyOut)
	}

	t.Logf("v0.16.0 Array[Enum] OK")
}

// TestV160MapEnum verifies Map[String]Enum type mapping.
func TestV160MapEnum(t *testing.T) {
	src := `
enum Status:
  active
  inactive

model Order:
  id: UUID
  metadata: Map[String]Status
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

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: Map[String]Status -> map[string]Status
	if !strings.Contains(goOut, "Metadata map[string]Status") {
		t.Fatalf("go missing Map[Enum]:\n%s", goOut)
	}

	// Python: Map[String]Status -> dict[str, Status]
	if !strings.Contains(pyOut, "metadata: dict[str, Status]") {
		t.Fatalf("py missing Map[Enum]:\n%s", pyOut)
	}

	t.Logf("v0.16.0 Map[String]Enum OK")
}